import os
import tempfile

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import database.mongo as db
import services.detector as detector_svc
import services.extractor as extractor_svc
import services.generator as generator_svc
import services.table_parser as table_parser_svc
import services.translator as translator_svc

app = FastAPI(title="InteCheck AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/checklists/generate")
async def generate(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted.")

    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        extracted = extractor_svc.extract_from_pdf(tmp_path)
    finally:
        os.unlink(tmp_path)

    detection = detector_svc.detect_document_type(extracted["sample_text"])
    if not detection["is_drops"]:
        raise HTTPException(
            status_code=422,
            detail="Document does not appear to be a DROPS procedure.",
        )

    existing = await db.get_by_hash(extracted["document_hash"])
    if existing:
        return existing

    annex_items = table_parser_svc.parse_annex_blocks(extracted["annex_blocks"])
    checklist = generator_svc.generate_from_prose(
        extracted["prose_text"],
        file.filename,
        extracted["document_hash"],
        annex_items,
    )
    await db.save_checklist(checklist)
    return checklist


@app.get("/api/checklists/{checklist_id}")
async def get_checklist_endpoint(checklist_id: str):
    checklist = await db.get_checklist(checklist_id)
    if checklist is None:
        raise HTTPException(status_code=404, detail="Checklist not found.")
    return checklist


@app.get("/api/checklists/{checklist_id}/items")
async def get_translated_items(
    checklist_id: str,
    lang: str = Query(default="EN"),
):
    checklist = await db.get_checklist(checklist_id)
    if checklist is None:
        raise HTTPException(status_code=404, detail="Checklist not found.")

    items = [item.model_dump() for item in checklist.items]
    translated, cache_hit = translator_svc.translate_checklist_items(
        checklist_id, items, lang
    )

    return {
        "checklist_id": checklist_id,
        "language": lang.upper(),
        "cache_hit": cache_hit,
        "items": translated,
    }
