import pytest
from unittest.mock import AsyncMock, MagicMock
from models.checklist import ChecklistItem, DROPSSeverity, GeneratedChecklist

SAMPLE_CHECKLIST = GeneratedChecklist(
    id="cl-abc123",
    document_name="drops_procedure.pdf",
    generated_at="2026-05-06T10:00:00",
    source_document_hash="deadbeef",
    status="current",
    items=[
        ChecklistItem(
            id="item-1",
            action="Inspect crown block assembly.",
            acceptance_criteria="All components secure.",
            failure_criteria="Remove from service immediately.",
            severity=DROPSSeverity.CRITICAL,
            source_section="Section 3.1",
            examination_frequency="6-monthly",
        )
    ],
    item_count=1,
)


def _make_mock_db(find_one_result=None):
    mock_collection = AsyncMock()
    mock_collection.insert_one = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=find_one_result)
    mock_db = MagicMock()
    mock_db.checklists = mock_collection
    return mock_db


async def test_save_checklist_returns_id(monkeypatch):
    mock_db = _make_mock_db()
    monkeypatch.setattr("database.mongo._get_db", AsyncMock(return_value=mock_db))

    from database.mongo import save_checklist
    result = await save_checklist(SAMPLE_CHECKLIST)

    assert result == "cl-abc123"


async def test_save_checklist_calls_insert_one(monkeypatch):
    mock_db = _make_mock_db()
    monkeypatch.setattr("database.mongo._get_db", AsyncMock(return_value=mock_db))

    from database.mongo import save_checklist
    await save_checklist(SAMPLE_CHECKLIST)

    mock_db.checklists.insert_one.assert_called_once()


async def test_get_checklist_returns_generated_checklist(monkeypatch):
    doc = {**SAMPLE_CHECKLIST.model_dump()}
    mock_db = _make_mock_db(find_one_result=doc)
    monkeypatch.setattr("database.mongo._get_db", AsyncMock(return_value=mock_db))

    from database.mongo import get_checklist
    result = await get_checklist("cl-abc123")

    assert isinstance(result, GeneratedChecklist)
    assert result.id == "cl-abc123"


async def test_get_checklist_returns_none_when_not_found(monkeypatch):
    mock_db = _make_mock_db(find_one_result=None)
    monkeypatch.setattr("database.mongo._get_db", AsyncMock(return_value=mock_db))

    from database.mongo import get_checklist
    result = await get_checklist("nonexistent")

    assert result is None


async def test_get_by_hash_returns_checklist(monkeypatch):
    doc = {**SAMPLE_CHECKLIST.model_dump()}
    mock_db = _make_mock_db(find_one_result=doc)
    monkeypatch.setattr("database.mongo._get_db", AsyncMock(return_value=mock_db))

    from database.mongo import get_by_hash
    result = await get_by_hash("deadbeef")

    assert isinstance(result, GeneratedChecklist)
    assert result.source_document_hash == "deadbeef"


async def test_get_by_hash_returns_none_when_not_found(monkeypatch):
    mock_db = _make_mock_db(find_one_result=None)
    monkeypatch.setattr("database.mongo._get_db", AsyncMock(return_value=mock_db))

    from database.mongo import get_by_hash
    result = await get_by_hash("unknown")

    assert result is None


async def test_get_checklist_strips_mongo_id(monkeypatch):
    doc = {**SAMPLE_CHECKLIST.model_dump(), "_id": "some-mongo-object-id"}
    mock_db = _make_mock_db(find_one_result=doc)
    monkeypatch.setattr("database.mongo._get_db", AsyncMock(return_value=mock_db))

    from database.mongo import get_checklist
    result = await get_checklist("cl-abc123")

    assert isinstance(result, GeneratedChecklist)
