import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
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
            chunk_id="chunk-uuid-123",
        )
    ],
    item_count=1,
)

EXTRACT_RESULT = {
    "sample_text": "DROPS Procedure for Dropped Object Prevention Scheme",
    "prose_text": "## Section 3\nInspection requirements for crown block...",
    "chunks": [{"id": "chunk-uuid-123", "type": "text", "grounding": {"page": 1, "box": [10, 10, 100, 100]}}],
    "document_hash": "deadbeef",
}

DETECT_DROPS = {"is_drops": True, "detected_keywords": ["DROPS"]}
DETECT_NOT_DROPS = {"is_drops": False, "detected_keywords": []}


def _get_client():
    from main import app
    return TestClient(app)


def test_health_returns_ok():
    client = _get_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_rejects_non_pdf():
    client = _get_client()
    response = client.post(
        "/api/checklists/generate",
        files={"file": ("report.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 422


def test_generate_rejects_non_drops_document(monkeypatch):
    monkeypatch.setattr(
        "services.extractor.extract_from_pdf",
        lambda path, **kwargs: EXTRACT_RESULT,
    )
    monkeypatch.setattr("main.db.get_extraction", AsyncMock(return_value=None))
    monkeypatch.setattr("main.db.save_extraction", AsyncMock())
    monkeypatch.setattr("main.db.save_pdf", AsyncMock())
    monkeypatch.setattr(
        "services.detector.detect_document_type",
        lambda _: DETECT_NOT_DROPS,
    )

    client = _get_client()
    response = client.post(
        "/api/checklists/generate",
        files={"file": ("procedure.pdf", b"fake pdf content", "application/pdf")},
    )
    assert response.status_code == 422
    assert "DROPS" in response.json()["detail"]


def test_generate_returns_cached_checklist_on_hash_match(monkeypatch):
    monkeypatch.setattr(
        "services.extractor.extract_from_pdf",
        lambda path, **kwargs: EXTRACT_RESULT,
    )
    monkeypatch.setattr("services.detector.detect_document_type", lambda _: DETECT_DROPS)
    monkeypatch.setattr("main.db.get_extraction", AsyncMock(return_value=None))
    monkeypatch.setattr("main.db.save_extraction", AsyncMock())
    monkeypatch.setattr("main.db.save_pdf", AsyncMock())
    monkeypatch.setattr(
        "main.db.get_by_hash",
        AsyncMock(return_value=SAMPLE_CHECKLIST),
    )

    client = _get_client()
    response = client.post(
        "/api/checklists/generate",
        files={"file": ("drops.pdf", b"fake pdf content", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["id"] == "cl-abc123"


def test_generate_full_pipeline_saves_and_returns_checklist(monkeypatch):
    monkeypatch.setattr(
        "services.extractor.extract_from_pdf",
        lambda path, **kwargs: EXTRACT_RESULT,
    )
    monkeypatch.setattr("services.detector.detect_document_type", lambda _: DETECT_DROPS)
    monkeypatch.setattr("main.db.get_extraction", AsyncMock(return_value=None))
    monkeypatch.setattr("main.db.save_extraction", AsyncMock())
    monkeypatch.setattr("main.db.save_pdf", AsyncMock())
    monkeypatch.setattr("main.db.get_by_hash", AsyncMock(return_value=None))
    monkeypatch.setattr(
        "services.generator.generate_from_prose",
        lambda *args, **kwargs: SAMPLE_CHECKLIST,
    )
    monkeypatch.setattr("main.db.save_checklist", AsyncMock(return_value="cl-abc123"))

    client = _get_client()
    response = client.post(
        "/api/checklists/generate",
        files={"file": ("drops.pdf", b"fake pdf content", "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "cl-abc123"
    assert data["item_count"] == 1


def test_generate_force_bypasses_cache(monkeypatch):
    monkeypatch.setattr(
        "services.extractor.extract_from_pdf",
        lambda path, **kwargs: EXTRACT_RESULT,
    )
    monkeypatch.setattr("services.detector.detect_document_type", lambda _: DETECT_DROPS)
    monkeypatch.setattr("main.db.get_extraction", AsyncMock(return_value=None))
    monkeypatch.setattr("main.db.save_extraction", AsyncMock())
    monkeypatch.setattr("main.db.save_pdf", AsyncMock())
    monkeypatch.setattr("main.db.get_by_hash", AsyncMock(return_value=SAMPLE_CHECKLIST))
    monkeypatch.setattr(
        "services.generator.generate_from_prose",
        lambda *args, **kwargs: SAMPLE_CHECKLIST,
    )
    monkeypatch.setattr("main.db.save_checklist", AsyncMock(return_value="cl-abc123"))

    client = _get_client()
    response = client.post(
        "/api/checklists/generate?force=true",
        files={"file": ("drops.pdf", b"fake pdf content", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["id"] == "cl-abc123"


def test_get_checklist_returns_200(monkeypatch):
    monkeypatch.setattr("main.db.get_checklist", AsyncMock(return_value=SAMPLE_CHECKLIST))

    client = _get_client()
    response = client.get("/api/checklists/cl-abc123")
    assert response.status_code == 200
    assert response.json()["id"] == "cl-abc123"


def test_get_checklist_returns_404_when_not_found(monkeypatch):
    monkeypatch.setattr("main.db.get_checklist", AsyncMock(return_value=None))

    client = _get_client()
    response = client.get("/api/checklists/unknown-id")
    assert response.status_code == 404


def test_get_items_returns_items_with_language(monkeypatch):
    monkeypatch.setattr("main.db.get_checklist", AsyncMock(return_value=SAMPLE_CHECKLIST))
    monkeypatch.setattr(
        "services.translator.translate_checklist_items",
        lambda checklist_id, items, lang: (items, True),
    )

    client = _get_client()
    response = client.get("/api/checklists/cl-abc123/items?lang=EN")
    assert response.status_code == 200
    data = response.json()
    assert data["checklist_id"] == "cl-abc123"
    assert data["language"] == "EN"
    assert len(data["items"]) == 1


def test_get_items_returns_404_when_checklist_not_found(monkeypatch):
    monkeypatch.setattr("main.db.get_checklist", AsyncMock(return_value=None))

    client = _get_client()
    response = client.get("/api/checklists/unknown/items?lang=NB")
    assert response.status_code == 404