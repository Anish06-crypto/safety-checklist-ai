import os
from motor.motor_asyncio import AsyncIOMotorClient
from models.checklist import GeneratedChecklist

_mongo_client = None
_db = None


def _get_db():
    global _mongo_client, _db
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(
            os.environ.get("MONGODB_URI", ""),
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=30000,
        )
        _db = _mongo_client[os.environ.get("MONGODB_DB", "intecheck")]
    return _db


async def save_checklist(checklist: GeneratedChecklist) -> str:
    db = _get_db()
    await db.checklists.insert_one(checklist.model_dump())
    return checklist.id


async def get_checklist(checklist_id: str) -> GeneratedChecklist | None:
    db = _get_db()
    doc = await db.checklists.find_one({"id": checklist_id})
    if doc is None:
        return None
    doc.pop("_id", None)
    return GeneratedChecklist(**doc)


async def get_by_hash(document_hash: str) -> GeneratedChecklist | None:
    db = _get_db()
    doc = await db.checklists.find_one(
        {"source_document_hash": document_hash, "status": "current"}
    )
    if doc is None:
        return None
    doc.pop("_id", None)
    return GeneratedChecklist(**doc)
