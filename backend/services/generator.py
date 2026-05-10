# generator.py
import json
import logging
import os
import uuid
from datetime import UTC, datetime

from groq import Groq
from models.checklist import ChecklistItem, DROPSSeverity, GeneratedChecklist

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
FALLBACK_MODEL = os.environ.get("GROQ_MODEL_FALLBACK", "llama-3.1-70b-versatile")

_groq_client = None

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
- chunk_id: the exact ID string from the <a id='...'></a> markers found in the markdown.
  You MUST pick the anchor tag that IMMEDIATELY PRECEDES the requirement text or the 
  table row you are extracting. Never reuse an ID from a different section. 
  This ID is the ONLY way the user can see the visual evidence—it MUST be accurate.

Return ONLY a valid JSON array. No preamble. No explanation.
No markdown code fences. Start with [ and end with ]."""


def _get_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    return _groq_client


def _call_groq(client, model: str, prose_text: str) -> str:
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
    """
    if not chunks:
        return items

    chunk_map = {c["id"]: c.get("markdown", "").lower() for c in chunks}
    
    validated_count = 0
    for item in items:
        cid = item.get("chunk_id")
        if not cid or cid not in chunk_map:
            item["chunk_id"] = None
            continue
            
        chunk_text = chunk_map[cid]
        action_text = item.get("action", "").lower()
        
        stop_words = {"inspect", "check", "verify", "ensure", "monitor", "with", "from", "each", "that", "this"}
        keywords = [w for w in action_text.replace(",", "").replace(".", "").split() 
                   if len(w) > 3 and w not in stop_words]
        
        if not keywords:
            match = action_text[:10] in chunk_text
        else:
            match = any(k in chunk_text for k in keywords)
        
        if not match:
            log.warning("Grounding MISMATCH: Chunk %s text doesn't match action. Clearing link.", cid)
            item["chunk_id"] = None
        else:
            validated_count += 1
            
    log.info("Grounding validation complete: %d/%d items verified.", validated_count, len(items))
    return items


def generate_from_prose(prose_text: str, document_name: str, document_hash: str, chunks: list[dict] = None) -> GeneratedChecklist:
    """Orchestrates the full generation pipeline with validation."""
    client = _get_client()
    
    # 1. LLM Extraction
    try:
        raw_output = _call_groq(client, MODEL, prose_text)
        items_data = _parse_llm_output(raw_output)
    except Exception as e:
        log.error("Failed to call LLM or parse output: %s. Falling back to Llama-3.1.", e)
        raw_output = _call_groq(client, FALLBACK_MODEL, prose_text)
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
