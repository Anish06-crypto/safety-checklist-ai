import os
from motor.motor_asyncio import AsyncIOMotorClient
from models.checklist import GeneratedChecklist

_mongo_client = None
_db = None


async def _get_db():
    global _mongo_client, _db
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(
            os.environ.get("MONGODB_URI", ""),
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=30000,
        )
        _db = _mongo_client[os.environ.get("MONGODB_DB", "intecheck")]
        # Ensure index exists — must be awaited
        await _db.raw_extractions.create_index("document_hash", unique=True)
    return _db


async def save_checklist(checklist: GeneratedChecklist) -> str:
    db = await _get_db()
    await db.checklists.insert_one(checklist.model_dump())
    return checklist.id


async def get_checklist(checklist_id: str) -> GeneratedChecklist | None:
    db = await _get_db()
    doc = await db.checklists.find_one({"id": checklist_id})
    if doc is None:
        return None
    doc.pop("_id", None)
    return GeneratedChecklist(**doc)


async def get_by_hash(document_hash: str) -> GeneratedChecklist | None:
    db = await _get_db()
    doc = await db.checklists.find_one(
        {"source_document_hash": document_hash, "status": "current"}
    )
    if doc is None:
        return None
    doc.pop("_id", None)
    return GeneratedChecklist(**doc)


async def get_extraction(document_hash: str) -> dict | None:
    db = await _get_db()
    doc = await db.raw_extractions.find_one({"document_hash": document_hash})
    if doc:
        return {"markdown": doc["markdown"], "chunks": doc.get("chunks", [])}
    return None


async def save_extraction(document_hash: str, markdown: str, chunks: list[dict]) -> None:
    db = await _get_db()
    await db.raw_extractions.update_one(
        {"document_hash": document_hash},
        {
            "$set": {
                "document_hash": document_hash,
                "markdown": markdown,
                "chunks": chunks,
            }
        },
        upsert=True,
    )