import logging
import os
import tempfile
import time
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database.mongo as db
import services.detector as detector_svc
import services.extractor as extractor_svc
import services.generator as generator_svc
import services.table_parser as table_parser_svc
import services.translator as translator_svc
from models.checklist import GeneratedChecklist

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("safety-checklist-ai")

# ---------------------------------------------------------------------------
# Response models (for Swagger docs)
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str


class TranslateResponse(BaseModel):
    checklist_id: str
    language: str
    cache_hit: bool
    items: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Safety Checklist AI",
    description=(
        "Automatically generates structured DROPS inspection checklists from "
        "safety procedure PDFs using LLM extraction, with real-time multilingual "
        "translation via DeepL.\n\n"
        "**Pipeline:** PDF upload → DROPS detection → text extraction → "
        "LLM generation (Groq) → MongoDB persistence → DeepL translation\n\n"
        "**Supported languages:** EN, NB, FR, AR, PL, ID, ES, PT-BR, NL, RO"
    ),
    version="1.0.0",
    contact={
        "name": "Anish Ravikiran",
        "email": "anishravikiran0610@gmail.com",
    },
    license_info={
        "name": "Private — University of Aberdeen KTP Associate Application",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
def health():
    """Returns `{"status": "ok"}` when the service is running."""
    log.info("GET /health — service alive")
    return {"status": "ok"}


@app.post(
    "/api/checklists/generate",
    response_model=GeneratedChecklist,
    summary="Generate inspection checklist from PDF",
    tags=["Checklists"],
    responses={
        200: {"description": "Checklist generated or returned from cache"},
        422: {"model": ErrorResponse, "description": "Non-PDF file or non-DROPS document"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def generate(
    file: UploadFile = File(..., description="DROPS procedure PDF"),
    force: bool = Query(default=False, description="Bypass document hash cache and force regeneration"),
):
    """
    Full generation pipeline:

    1. Validate PDF file type
    2. Extract prose text (pages 22–35) and annex blocks (pages 40–62) via PyMuPDF
    3. Detect DROPS keywords in sample text — reject non-DROPS documents
    4. Check MongoDB for existing checklist with same document hash (cache hit) — skipped if `force=true`
    5. Parse annex blocks directly into ChecklistItems (no LLM)
    6. Generate checklist items from prose via Groq LLM (llama-3.3-70b-versatile)
    7. Persist combined checklist to MongoDB
    8. Return GeneratedChecklist JSON
    """
    t_start = time.perf_counter()
    log.info("POST /api/checklists/generate — file=%s size=%s bytes force=%s",
             file.filename, file.size, force)

    if not file.filename.lower().endswith(".pdf"):
        log.warning("Rejected non-PDF upload: %s", file.filename)
        raise HTTPException(status_code=422, detail="Only PDF files are accepted.")

    # --- Write to temp file ---
    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    log.info("[1/6] Temp file written: %s (%d bytes)", tmp_path, len(contents))

    # --- Extract ---
    try:
        t0 = time.perf_counter()
        extracted = extractor_svc.extract_from_pdf(tmp_path)
        log.info("[2/6] Extraction complete — hash=%s prose_chars=%d annex_pages=%d (%.2fs)",
                 extracted["document_hash"],
                 len(extracted["prose_text"]),
                 len(extracted["annex_blocks"]),
                 time.perf_counter() - t0)
    finally:
        os.unlink(tmp_path)

    # --- Detect ---
    detection = detector_svc.detect_document_type(extracted["sample_text"])
    log.info("[3/6] Document detection — is_drops=%s keywords=%s",
             detection["is_drops"], detection["detected_keywords"])
    if not detection["is_drops"]:
        log.warning("Rejected non-DROPS document: %s", file.filename)
        raise HTTPException(
            status_code=422,
            detail="Document does not appear to be a DROPS procedure.",
        )

    # --- Cache check ---
    t0 = time.perf_counter()
    if force:
        log.info("[4/6] Cache BYPASS — force=true, skipping hash lookup")
    else:
        existing = await db.get_by_hash(extracted["document_hash"])
        if existing:
            log.info("[4/6] Cache HIT — returning existing checklist id=%s (%.2fs)",
                     existing.id, time.perf_counter() - t0)
            return existing
        log.info("[4/6] Cache MISS — hash=%s (%.2fs)",
                 extracted["document_hash"], time.perf_counter() - t0)

    # --- Parse annexes ---
    t0 = time.perf_counter()
    annex_items = table_parser_svc.parse_annex_blocks(extracted["annex_blocks"])
    log.info("[5/6] Annex parser — %d items extracted (%.2fs)",
             len(annex_items), time.perf_counter() - t0)

    # --- LLM generation ---
    t0 = time.perf_counter()
    log.info("[6/6] Calling Groq LLM for prose generation...")
    checklist = generator_svc.generate_from_prose(
        extracted["prose_text"],
        file.filename,
        extracted["document_hash"],
        annex_items,
    )
    log.info("[6/6] LLM generation complete — %d items total (%.2fs)",
             checklist.item_count, time.perf_counter() - t0)

    # --- Persist ---
    await db.save_checklist(checklist)
    log.info("Checklist saved to MongoDB — id=%s", checklist.id)

    log.info("POST /api/checklists/generate DONE — id=%s total_items=%d elapsed=%.2fs",
             checklist.id, checklist.item_count, time.perf_counter() - t_start)
    return checklist


@app.get(
    "/api/checklists/{checklist_id}",
    response_model=GeneratedChecklist,
    summary="Retrieve checklist by ID",
    tags=["Checklists"],
    responses={
        404: {"model": ErrorResponse, "description": "Checklist not found"},
    },
)
async def get_checklist_endpoint(checklist_id: str):
    """Fetch a previously generated checklist from MongoDB by its UUID."""
    log.info("GET /api/checklists/%s", checklist_id)
    checklist = await db.get_checklist(checklist_id)
    if checklist is None:
        log.warning("Checklist not found: %s", checklist_id)
        raise HTTPException(status_code=404, detail="Checklist not found.")
    log.info("Checklist retrieved — id=%s items=%d", checklist_id, checklist.item_count)
    return checklist


@app.get(
    "/api/checklists/{checklist_id}/items",
    response_model=TranslateResponse,
    summary="Get checklist items translated into target language",
    tags=["Translation"],
    responses={
        404: {"model": ErrorResponse, "description": "Checklist not found"},
    },
)
async def get_translated_items(
    checklist_id: str,
    lang: str = Query(
        default="EN",
        description="Target language code: EN, NB, FR, AR, PL, ID, ES, PT-BR, NL, RO",
    ),
):
    """
    Returns checklist items translated into the requested language via DeepL.

    - **EN / EN-GB / EN-US**: passthrough — original items returned unchanged
    - All other codes: DeepL translation with in-memory cache per `(checklist_id, lang)` pair
    - `cache_hit: true` means the translation was served from cache (no DeepL API call made)
    - Protected fields (severity, id, examination_frequency) are never translated
    """
    log.info("GET /api/checklists/%s/items?lang=%s", checklist_id, lang)
    checklist = await db.get_checklist(checklist_id)
    if checklist is None:
        log.warning("Checklist not found for translation: %s", checklist_id)
        raise HTTPException(status_code=404, detail="Checklist not found.")

    items = [item.model_dump() for item in checklist.items]

    t0 = time.perf_counter()
    translated, cache_hit = translator_svc.translate_checklist_items(
        checklist_id, items, lang
    )
    log.info("Translation complete — lang=%s cache_hit=%s items=%d elapsed=%.2fs",
             lang.upper(), cache_hit, len(translated), time.perf_counter() - t0)

    return {
        "checklist_id": checklist_id,
        "language": lang.upper(),
        "cache_hit": cache_hit,
        "items": translated,
    }
