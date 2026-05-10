# main.py
import hashlib
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, List

import fitz
from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
    """
    t_start = time.perf_counter()
    log.info("POST /api/checklists/generate — file=%s size=%s bytes force=%s",
             file.filename, file.size, force)

    if not file.filename.lower().endswith(".pdf"):
        log.warning("Rejected non-PDF upload: %s", file.filename)
        raise HTTPException(status_code=422, detail="Only PDF files are accepted.")

    contents = await file.read()
    doc_hash = hashlib.sha256(contents).hexdigest()[:16]
    log.info("[1/7] Document hash computed — hash=%s bytes=%d", doc_hash, len(contents))

    t0 = time.perf_counter()
    extraction_cache = None if force else await db.get_extraction(doc_hash)
    
    if extraction_cache:
        log.info("[2/7] Extraction cache HIT — hash=%s (%.2fs) — ADE skipped",
                 doc_hash, time.perf_counter() - t0)
        extracted = {
            "sample_text": extraction_cache["markdown"][:500],
            "prose_text": extraction_cache["markdown"],
            "chunks": extraction_cache["chunks"],
            "document_hash": doc_hash,
        }
    else:
        log.info("[2/7] Extraction cache MISS — hash=%s — calling ADE", doc_hash)
        
        # Save PDF to persistent uploads directory for on-the-fly cropping
        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)
        pdf_path = uploads_dir / f"{doc_hash}.pdf"
        
        if not pdf_path.exists():
            with open(pdf_path, "wb") as f:
                f.write(contents)
        
        tmp_path = str(pdf_path)

        try:
            t_ade = time.perf_counter()
            extracted = extractor_svc.extract_from_pdf(tmp_path, filename=file.filename)
            log.info("[2/7] ADE extraction complete — hash=%s prose_chars=%d (%.2fs)",
                     extracted["document_hash"],
                     len(extracted["prose_text"]),
                     time.perf_counter() - t_ade)

            await db.save_extraction(
                extracted["document_hash"],
                extracted["prose_text"],
                extracted.get("chunks", [])
            )
            log.info("[2/7] Markdown cached in MongoDB — hash=%s", extracted["document_hash"])
        finally:
            os.unlink(tmp_path)

    detection = detector_svc.detect_document_type(extracted["sample_text"])
    if not detection["is_drops"]:
        log.warning("Rejected non-DROPS document: %s", file.filename)
        raise HTTPException(status_code=422, detail="Document does not appear to be a DROPS procedure.")

    t0 = time.perf_counter()
    if force:
        log.info("[4/7] Checklist cache BYPASS — force=true")
        cached_checklist = None
    else:
        cached_checklist = await db.get_by_hash(doc_hash)

    if cached_checklist:
        log.info("[4/7] Checklist cache HIT — hash=%s (%.2fs)", doc_hash, time.perf_counter() - t0)
        return cached_checklist

    log.info("[5/7] Generating checklist items from markdown via Groq LLM")
    # Debug: Check for grounding markers
    marker_count = extracted["prose_text"].count("<a id=")
    log.debug("Grounding markers found in markdown: %d", marker_count)
    
    t0 = time.perf_counter()
    checklist = generator_svc.generate_from_prose(
        extracted["prose_text"],
        file.filename,
        doc_hash,
        []
    )
    log.info("[6/7] Checklist generated — items=%d (%.2fs)", len(checklist.items), time.perf_counter() - t0)

    await db.save_checklist(checklist)
    log.info("[7/7] Pipeline complete — total_time=%.2fs", time.perf_counter() - t_start)
    return checklist


@app.get(
    "/api/checklists/{checklist_id}",
    response_model=GeneratedChecklist,
    summary="Retrieve a generated checklist by ID",
    tags=["Checklists"],
)
async def get_checklist(checklist_id: str):
    checklist = await db.get_checklist(checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")
    return checklist


@app.get(
    "/api/checklists/{checklist_id}/items",
    response_model=TranslateResponse,
    summary="Get translated checklist items",
    tags=["Translation"],
)
async def get_translated_items(
    checklist_id: str,
    lang: str = Query(..., description="Target language (e.g., NB, FR, ES)")
):
    t0 = time.perf_counter()
    checklist = await db.get_checklist(checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    translated, cache_hit = translator_svc.translate_checklist_items(
        checklist_id, checklist.items, lang.upper()
    )
    log.info("GET /api/checklists/%s/items?lang=%s — cache_hit=%s items=%d (%.2fs)",
             checklist_id, lang.upper(), cache_hit, len(translated), time.perf_counter() - t0)

    return {
        "checklist_id": checklist_id,
        "language": lang.upper(),
        "cache_hit": cache_hit,
        "items": [item.model_dump() for item in translated],
    }


@app.get(
    "/api/extractions/{document_hash}/chunks",
    summary="Get visual grounding chunks (bounding boxes) for a document",
    tags=["Checklists"],
)
async def get_chunks(document_hash: str):
    """
    Returns the list of chunks (with bounding boxes) for a given document hash.
    Used by the frontend to highlight regions on the PDF using `chunk_id`.
    """
    data = await db.get_extraction(document_hash)
    if not data:
        raise HTTPException(status_code=404, detail="Grounding data not found for this document.")
    return data["chunks"]
@app.get("/api/extractions/{doc_hash}/chunks/{chunk_id}/image", tags=["Grounding"])
async def get_chunk_image(doc_hash: str, chunk_id: str):
    """Serve a cropped image of the chunk from the source PDF using PyMuPDF"""
    # 1. Get grounding data
    extraction = await db.get_extraction(doc_hash)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    # 2. Find the chunk metadata
    chunk = next((c for c in extraction["chunks"] if c["id"] == chunk_id), None)
    if not chunk or "grounding" not in chunk:
        raise HTTPException(status_code=404, detail="Grounding metadata not found for this chunk")
    
    # 3. Open source PDF
    pdf_path = Path("uploads") / f"{doc_hash}.pdf"
    if not pdf_path.exists():
        log.warning("Source PDF missing for crop: %s", pdf_path)
        raise HTTPException(status_code=404, detail="Source PDF missing. Please re-upload.")
    
    # 4. Perform crop
    try:
        doc = fitz.open(str(pdf_path))
        page_idx = chunk["grounding"]["page"] - 1
        page = doc[page_idx]
        box = chunk["grounding"]["box"]
        
        w, h = page.rect.width, page.rect.height
        if isinstance(box, dict):
            rect = fitz.Rect(box["left"] * w, box["top"] * h, box["right"] * w, box["bottom"] * h)
        else:
            rect = fitz.Rect(box[0] * w / 1000, box[1] * h / 1000, box[2] * w / 1000, box[3] * h / 1000)

        # Bake the blue highlight box into the page BEFORE rendering PNG
        page.draw_rect(rect, color=(0.23, 0.51, 0.96), width=2, overlay=True)

        # Contextual crop
        crop_rect = fitz.Rect(rect.x0 - 40, rect.y0 - 40, rect.x1 + 40, rect.y1 + 40)
        crop_rect.x0 = max(0, crop_rect.x0)
        crop_rect.y0 = max(0, crop_rect.y0)
        crop_rect.x1 = min(w, crop_rect.x1)
        crop_rect.y1 = min(h, crop_rect.y1)
        
        pix = page.get_pixmap(clip=crop_rect, matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        doc.close()
        
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        log.error("Failed to crop PDF for chunk %s: %s", chunk_id, e)
        raise HTTPException(status_code=500, detail="Failed to process image evidence")
