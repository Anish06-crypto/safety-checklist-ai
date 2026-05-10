import pytest
import json
from unittest.mock import MagicMock
from models.checklist import GeneratedChecklist, ChecklistItem, DROPSSeverity

VALID_ITEM = {
    "action": "Inspect crown block assembly sheave pins.",
    "acceptance_criteria": "All sheave pins intact, no deformation.",
    "failure_criteria": "Any cracked or missing pin — remove from service immediately.",
    "severity": "CRITICAL",
    "source_section": "3.1 Independent Dropped Objects Inspections",
    "examination_frequency": "6-monthly",
}

CHUNKS_DATA = [
    {"id": "chunk-uuid-123", "markdown": "Inspect crown block assembly sheave pins.", "type": "text"}
]


def _make_mock_client(response_content: str):
    mock_message = MagicMock()
    mock_message.content = response_content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


def test_returns_generated_checklist_instance(monkeypatch):
    mock_client = _make_mock_client(json.dumps([VALID_ITEM]))
    monkeypatch.setattr("services.generator._groq_client", mock_client)

    from services.generator import generate_from_prose
    result = generate_from_prose("prose text", "test.pdf", "abc123", [])

    assert isinstance(result, GeneratedChecklist)


def test_item_count_equals_items_length(monkeypatch):
    mock_client = _make_mock_client(json.dumps([VALID_ITEM]))
    monkeypatch.setattr("services.generator._groq_client", mock_client)

    from services.generator import generate_from_prose
    result = generate_from_prose("prose text", "test.pdf", "abc123", CHUNKS_DATA)

    assert result.item_count == len(result.items)


def test_status_is_current(monkeypatch):
    mock_client = _make_mock_client(json.dumps([VALID_ITEM]))
    monkeypatch.setattr("services.generator._groq_client", mock_client)

    from services.generator import generate_from_prose
    result = generate_from_prose("prose text", "test.pdf", "abc123", [])

    assert result.status == "current"


def test_source_document_hash_matches_input(monkeypatch):
    mock_client = _make_mock_client(json.dumps([VALID_ITEM]))
    monkeypatch.setattr("services.generator._groq_client", mock_client)

    from services.generator import generate_from_prose
    result = generate_from_prose("prose text", "test.pdf", "deadbeef", [])

    assert result.source_document_hash == "deadbeef"


def test_malformed_items_are_skipped(monkeypatch):
    malformed = {"action": "", "severity": "NOT_VALID"}
    mock_client = _make_mock_client(json.dumps([malformed, VALID_ITEM]))
    monkeypatch.setattr("services.generator._groq_client", mock_client)

    from services.generator import generate_from_prose
    result = generate_from_prose("prose text", "test.pdf", "abc123", [])

    assert result.item_count == 1
    assert result.items[0].action == VALID_ITEM["action"]


def test_markdown_fences_are_handled(monkeypatch):
    fenced = f"```json\n{json.dumps([VALID_ITEM])}\n```"
    mock_client = _make_mock_client(fenced)
    monkeypatch.setattr("services.generator._groq_client", mock_client)

    from services.generator import generate_from_prose
    result = generate_from_prose("prose text", "test.pdf", "abc123", [])

    assert result.item_count == 1


def test_fallback_model_used_on_exception(monkeypatch):
    success_response = _make_mock_client(json.dumps([VALID_ITEM])).chat.completions.create.return_value
    mock_client = MagicMock()
    call_count = {"n": 0}

    def failing_then_succeeding(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("primary model unavailable")
        return success_response

    mock_client.chat.completions.create.side_effect = failing_then_succeeding
    monkeypatch.setattr("services.generator._groq_client", mock_client)

    from services.generator import generate_from_prose
    result = generate_from_prose("prose text", "test.pdf", "abc123", [])

    assert call_count["n"] == 2
    assert isinstance(result, GeneratedChecklist)
