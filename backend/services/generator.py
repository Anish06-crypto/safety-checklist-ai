# generator.py
import json
import logging
import os
import re
import uuid
from datetime import UTC, datetime

from groq import Groq
from models.checklist import ChecklistItem, DROPSSeverity, GeneratedChecklist

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
FALLBACK_MODEL = os.environ.get("GROQ_MODEL_FALLBACK", "llama-3.1-70b-versatile")

# ---------------------------------------------------------------------------
# API Key Rotation — reads GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3
# On 429 rate-limit, automatically rotates to the next key.
# ---------------------------------------------------------------------------
_api_keys: list[str] = []
_key_index: int = 0
_clients: dict[str, Groq] = {}

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a safety inspection specialist for the offshore energy industry.
You extract structured inspection checklists from DROPS (Dropped Object
Prevention Scheme) safety procedure documents.

The document text is structured markdown extracted by an agentic document 
parser. Tables appear as markdown tables with headers and rows intact. 
Extract checklist items from BOTH prose paragraphs AND table rows — 
inspection tables often contain the most specific action and criteria data.

DROPS Severity Classification — based on DROPS Calculator 2021 thresholds.
Severity is determined by the mass of the component and the height from
which it could fall. Use the quick rules below to classify each item:

CRITICAL (red zone — potential fatality):
  Object ≥ 10 kg at any working height above 1.5 m
  Object ≥ 5 kg at any working height above 2.7 m
  Object ≥ 2 kg at any working height above 5.9 m
  Object ≥ 1 kg at any working height above 10.6 m
  Any unsecured component on a derrick, crown block, or monkey board (height > 20 m)

MAJOR (yellow zone — Lost Time Incident risk):
  Object ≥ 10 kg at height 0.9–1.5 m
  Object ≥ 5 kg at height 1.7–2.7 m
  Object ≥ 2 kg at height 3.7–5.9 m
  Object ≥ 1 kg at height 6.6–10.6 m
  Working-at-height equipment at intermediate elevations (drill floor, BOP deck)

MINOR (green zone — Medical Treatment / First Aid risk):
  Object ≥ 10 kg at height below 0.9 m
  Object ≥ 5 kg at height below 1.7 m
  Object ≥ 1 kg at height below 6.6 m
  Small hand tools (< 0.5 kg) at typical working heights
  Ground-level or low-elevation equipment
  Administrative and documentation checks (registers, logs, records)

When the document does not specify mass or height, infer from context:
  - Overhead lifting equipment, crane components, top drive: CRITICAL
  - Drill floor equipment, elevated platforms: MAJOR
  - Ground-level portable tools, low-height equipment: MINOR

For each inspectable item you identify, return a JSON object with these
exact fields:
- action: the specific inspection action to perform (clear imperative verb,
  reference specific component names from the document)
- acceptance_criteria: exactly what constitutes a pass condition
  (be specific — reference tolerances, visual standards, or document criteria)
- failure_criteria: exactly what constitutes a fail requiring immediate
  escalation — stop work, remove from service, notify supervisor.
  This MUST be substantively different from acceptance_criteria.
  Bad example: "Component does not meet acceptance criteria — report to supervisor."
  Good example: "Any keeper plate found cracked, missing, or with damaged retaining
  pin — remove crown block assembly from service immediately, do not resume hoisting
  operations, notify installation supervisor and OIM before any further use."
- severity: CRITICAL, MAJOR, or MINOR per DROPS thresholds above
- source_section: the exact section heading or annex title this item came from
- examination_frequency: extract from the document text —
  "Pre-use", "6-monthly", "12-monthly", or "As required".
  Do NOT default everything to Pre-use — vary based on document content.
  For event-triggered inspections (post-jarring, post-incident, post-modification),
  use "As required". Never invent a frequency not supported by the document.
- chunk_id: the most precise ID that locates your extracted text in the document.
  There are TWO types of IDs in the markdown — you MUST choose the most specific one:
  
  TYPE 1 — Table cell IDs (HIGHEST PRECISION — prefer these for table content):
  These appear as attributes on <td> tags inside tables: <td id="1-9">Link Block Bolt Assemblies Secured</td>
  The id format is like "1-9", "0-7", "1-c", "3-g" etc. (page-column notation).
  If the item you are extracting appears in a table row, use the <td id="..."> of the 
  FIRST cell in that row (the one containing the item name/description).
  
  TYPE 2 — Chunk anchor IDs (FALLBACK — use only for non-table content):
  These appear as <a id='uuid-here'></a> tags before paragraphs, headings, or figures.
  Use these ONLY when the content is NOT inside a table.
  
  RULE: For table items, ALWAYS use the cell ID (e.g. "1-9"), never the chunk UUID.
  This ID is the ONLY way the user can see the precise visual evidence—it MUST be accurate.

Return ONLY a valid JSON array. No preamble. No explanation.
No markdown code fences. Start with [ and end with ]."""


def _load_api_keys() -> list[str]:
    """Collect all configured Groq API keys from environment variables."""
    keys = []
    primary = os.environ.get("GROQ_API_KEY", "")
    if primary:
        keys.append(primary)
    for i in range(2, 10):  # supports GROQ_API_KEY_2 through GROQ_API_KEY_9
        k = os.environ.get(f"GROQ_API_KEY_{i}", "")
        if k:
            keys.append(k)
        else:
            break
    return keys


def _get_client_for_key(api_key: str) -> Groq:
    """Return a cached Groq client for the given API key."""
    if api_key not in _clients:
        _clients[api_key] = Groq(api_key=api_key)
    return _clients[api_key]


def _call_groq(model: str, prose_text: str) -> str:
    """Call Groq with automatic round-robin key rotation on 429 rate-limit errors."""
    global _api_keys, _key_index

    if not _api_keys:
        _api_keys = _load_api_keys()
        if not _api_keys:
            raise RuntimeError("No Groq API keys configured. Set GROQ_API_KEY in environment.")
        log.info("Loaded %d Groq API key(s) for rotation.", len(_api_keys))

    attempts = len(_api_keys)
    last_error = None

    for _ in range(attempts):
        key = _api_keys[_key_index]
        client = _get_client_for_key(key)
        key_label = f"key[{_key_index + 1}/{len(_api_keys)}]"
        try:
            log.debug("Calling Groq with %s model=%s", key_label, model)
            response = client.chat.completions.create(
                model=model,
                temperature=0.1,
                max_tokens=4000,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Extract 8-12 safety-critical inspection items with their precise chunk_ids from this DROPS procedure:\n\n{prose_text}"},
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str.lower() or "rate limit" in err_str.lower():
                log.warning("Rate limit hit on %s — rotating to next key.", key_label)
                _key_index = (_key_index + 1) % len(_api_keys)
                last_error = e
            else:
                raise  # Non-rate-limit errors propagate immediately

    raise RuntimeError(f"All {len(_api_keys)} Groq API key(s) are rate-limited.") from last_error


def _parse_llm_output(raw: str) -> list[dict]:
    # Strip markdown code fences if present
    if "```" in raw:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        raw = raw[start:end] if start != -1 else raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
        return []


def _validate_item(data: dict) -> ChecklistItem | None:
    try:
        if not data.get("action", "").strip():
            return None

        severity_raw = data.get("severity", "MINOR").upper()
        if severity_raw not in {"CRITICAL", "MAJOR", "MINOR"}:
            severity_raw = "MAJOR" if "MAJ" in severity_raw or "HIGH" in severity_raw else "MINOR"

        return ChecklistItem(
            id=str(uuid.uuid4()),
            action=data.get("action", ""),
            acceptance_criteria=data.get("acceptance_criteria", ""),
            failure_criteria=data.get("failure_criteria", ""),
            severity=DROPSSeverity(severity_raw),
            source_section=data.get("source_section", "General"),
            examination_frequency=data.get("examination_frequency", "Pre-use"),
            chunk_id=data.get("chunk_id"),
        )
    except Exception:
        return None


def validate_grounding(items: list[dict], chunks: list[dict]) -> list[dict]:
    """
    Verify that the chunk_id selected by LLM actually contains text related to the item.
    Handles both chunk-level UUIDs and table cell-level IDs (e.g. '1-9', '0-7').
    """
    if not chunks:
        return items

    # Build lookup from chunk markdown (UUID-keyed)
    chunk_map = {c["id"]: c.get("markdown", "").lower() for c in chunks}

    # Build lookup for table cell IDs embedded within chunk markdown
    # e.g. <td id="1-9">Link Block Bolt Assemblies Secured</td>
    cell_map: dict[str, str] = {}
    cell_pattern = re.compile(r'<td[^>]+id="([^"]+)"[^>]*>(.*?)</td>', re.IGNORECASE | re.DOTALL)
    for chunk in chunks:
        for cell_id, cell_text in cell_pattern.findall(chunk.get("markdown", "")):
            cell_map[cell_id] = cell_text.lower()

    validated_count = 0
    for item in items:
        cid = item.get("chunk_id")
        if not cid:
            continue

        # Resolve text: check cell map first, then chunk map
        if cid in cell_map:
            chunk_text = cell_map[cid]
        elif cid in chunk_map:
            chunk_text = chunk_map[cid]
        else:
            log.warning("Grounding ID '%s' not found in chunk or cell maps — clearing link.", cid)
            item["chunk_id"] = None
            continue

        action_text = item.get("action", "").lower()
        stop_words = {"inspect", "check", "verify", "ensure", "monitor", "with", "from", "each", "that", "this"}
        keywords = [w for w in action_text.replace(",", "").replace(".", "").split()
                   if len(w) > 3 and w not in stop_words]

        if not keywords:
            match = action_text[:10] in chunk_text
        else:
            match = any(k in chunk_text for k in keywords)

        if not match:
            log.warning("Grounding MISMATCH: ID '%s' text doesn't match action. Clearing link.", cid)
            item["chunk_id"] = None
        else:
            validated_count += 1

    log.info("Grounding validation complete: %d/%d items verified.", validated_count, len(items))
    return items


def generate_from_prose(prose_text: str, document_name: str, document_hash: str, chunks: list[dict] = None) -> GeneratedChecklist:
    """Orchestrates the full generation pipeline with validation."""

    # 1. LLM Extraction — with automatic key rotation on rate-limit
    try:
        raw_output = _call_groq(MODEL, prose_text)
        items_data = _parse_llm_output(raw_output)
    except Exception as e:
        log.error("Primary model failed: %s. Falling back to %s.", e, FALLBACK_MODEL)
        raw_output = _call_groq(FALLBACK_MODEL, prose_text)
        items_data = _parse_llm_output(raw_output)

    # 2. Grounding Validation
    if chunks:
        items_data = validate_grounding(items_data, chunks)

    # 3. Model instantiation
    # Use _validate_item to generate IDs and clean data
    items = [item for data in items_data if (item := _validate_item(data)) is not None]
    
    return GeneratedChecklist(
        id=f"cl-{uuid.uuid4().hex[:8]}",
        document_name=document_name,
        generated_at=datetime.now(UTC).isoformat(),
        source_document_hash=document_hash,
        status="current",
        items=items,
        item_count=len(items)
    )
