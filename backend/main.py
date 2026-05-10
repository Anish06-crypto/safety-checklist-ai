# main.py
import hashlib
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
import services.translator as translator_svc
from models.checklist import GeneratedChecklist

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG,
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
        "**Pipeline:** PDF upload → hash check → ADE extraction (cached) → "
        "DROPS detection → checklist cache check → "
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
    force: bool = Query(default=False, description="Bypass checklist cache and force regeneration"),
):
    """
    Full generation pipeline:

    1. Validate PDF file type
    2. Compute SHA-256 document hash from raw bytes
    3. Check MongoDB raw_extractions for cached ADE markdown (skip ADE if hit)
    4. If cache miss: call ADE, persist markdown to raw_extractions, delete temp file
    5. Detect DROPS keywords in sample text — reject non-DROPS documents
    6. Check MongoDB for existing checklist with same document hash — skipped if force=true
    7. Generate checklist items from ADE markdown via Groq LLM
    8. Persist checklist to MongoDB
    9. Return GeneratedChecklist JSON

    ADE credits are only consumed once per unique document regardless of how many
    times the same PDF is uploaded. The raw markdown is stored in MongoDB and
    reused on all subsequent requests for the same document hash.
    """
    t_start = time.perf_counter()
    log.info("POST /api/checklists/generate — file=%s size=%s bytes force=%s",
             file.filename, file.size, force)

    # --- [1/7] Validate file type ---
    if not file.filename.lower().endswith(".pdf"):
        log.warning("Rejected non-PDF upload: %s", file.filename)
        raise HTTPException(status_code=422, detail="Only PDF files are accepted.")

    # --- [2/7] Read bytes and compute hash ---
    # Hash is computed from raw bytes in memory — no disk I/O needed for this step.
    # This lets us check the extraction cache before writing a temp file at all.
    contents = await file.read()
    doc_hash = hashlib.sha256(contents).hexdigest()[:16]
    log.info("[1/7] Document hash computed — hash=%s bytes=%d", doc_hash, len(contents))

    # --- [3/7] Check ADE extraction cache ---
    t0 = time.perf_counter()
    cached_markdown = await db.get_extraction(doc_hash)

    if cached_markdown:
        # ADE already ran on this document — reuse stored markdown, spend 0 credits
        log.info("[2/7] Extraction cache HIT — hash=%s (%.2fs) — ADE skipped",
                 doc_hash, time.perf_counter() - t0)
        extracted = {
            "sample_text": cached_markdown[:500],
            "prose_text": cached_markdown,
            "annex_blocks": [],
            "document_hash": doc_hash,
        }
    else:
        # Cache miss — write temp file, call ADE, persist markdown, clean up
        log.info("[2/7] Extraction cache MISS — hash=%s — calling ADE", doc_hash)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        log.debug("Temp file written: %s (%d bytes)", tmp_path, len(contents))

        try:
            t_ade = time.perf_counter()
            extracted = extractor_svc.extract_from_pdf(tmp_path, filename=file.filename)
            log.info("[2/7] ADE extraction complete — hash=%s prose_chars=%d (%.2fs)",
                     extracted["document_hash"],
                     len(extracted["prose_text"]),
                     time.perf_counter() - t_ade)

            # Persist raw markdown — future uploads of the same PDF skip ADE entirely
            await db.save_extraction(extracted["document_hash"], extracted["prose_text"])
            log.info("[2/7] Markdown cached in MongoDB — hash=%s", extracted["document_hash"])

        finally:
            # Always delete temp file — runs even if ADE throws an exception
            os.unlink(tmp_path)
            log.debug("Temp file deleted: %s", tmp_path)

    # --- [4/7] Detect DROPS document ---
    detection = detector_svc.detect_document_type(extracted["sample_text"])
    log.info("[3/7] Document detection — is_drops=%s keywords=%s",
             detection["is_drops"], detection["detected_keywords"])
    if not detection["is_drops"]:
        log.warning("Rejected non-DROPS document: %s", file.filename)
        raise HTTPException(
            status_code=422,
            detail="Document does not appear to be a DROPS procedure.",
        )

    # --- [5/7] Checklist cache check ---
    t0 = time.perf_counter()
    if force:
        log.info("[4/7] Checklist cache BYPASS — force=true, skipping hash lookup")
    else:
        existing = await db.get_by_hash(extracted["document_hash"])
        if existing:
            log.info("[4/7] Checklist cache HIT — returning existing id=%s (%.2fs)",
                     existing.id, time.perf_counter() - t0)
            return existing
        log.info("[4/7] Checklist cache MISS — hash=%s (%.2fs)",
                 extracted["document_hash"], time.perf_counter() - t0)

    # --- [6/7] LLM generation ---
    t0 = time.perf_counter()
    log.info("[5/7] Calling Groq LLM for checklist generation...")
    checklist = generator_svc.generate_from_prose(
        extracted["prose_text"],
        file.filename,
        extracted["document_hash"],
        [],  # ADE markdown contains everything — no separate annex items
    )
    log.info("[5/7] LLM generation complete — %d items (%.2fs)",
             checklist.item_count, time.perf_counter() - t0)

    # --- [7/7] Persist checklist ---
    await db.save_checklist(checklist)
    log.info("Checklist saved to MongoDB — id=%s", checklist.id)

    log.info("POST /api/checklists/generate DONE — id=%s items=%d elapsed=%.2fs",
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
    - All other codes: DeepL translation with in-memory cache per (checklist_id, lang) pair
    - cache_hit: true means the translation was served from cache (no DeepL API call made)
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