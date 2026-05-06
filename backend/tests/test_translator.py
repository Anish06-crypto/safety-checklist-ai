import pytest
from unittest.mock import MagicMock, patch
from services.translator import translate_checklist_items, _clear_cache

SAMPLE_ITEMS = [
    {
        "id": "item-1",
        "action": "Inspect crown block assembly.",
        "acceptance_criteria": "All components secure.",
        "failure_criteria": "Remove from service immediately.",
        "severity": "CRITICAL",
        "source_section": "Annex C",
        "examination_frequency": "Pre-use",
    }
]


@pytest.fixture(autouse=True)
def clear_cache():
    _clear_cache()
    yield
    _clear_cache()


def _make_mock_client(translated_text="TRANSLATED"):
    mock_result = MagicMock()
    mock_result.text = translated_text
    mock_client = MagicMock()
    mock_client.translate_text.return_value = [mock_result] * 4
    return mock_client


def test_english_passthrough_returns_items_unchanged():
    items, cache_hit = translate_checklist_items("cl-1", SAMPLE_ITEMS, "EN")
    assert items == SAMPLE_ITEMS
    assert cache_hit is True


def test_en_gb_treated_as_english_passthrough():
    items, cache_hit = translate_checklist_items("cl-1", SAMPLE_ITEMS, "EN-GB")
    assert cache_hit is True


def test_en_us_treated_as_english_passthrough():
    items, cache_hit = translate_checklist_items("cl-1", SAMPLE_ITEMS, "EN-US")
    assert cache_hit is True


def test_first_translation_call_hits_deepl(monkeypatch):
    mock_client = _make_mock_client("Inspiser kranblokk.")
    monkeypatch.setattr("services.translator._deepl_client", mock_client)

    _, cache_hit = translate_checklist_items("cl-1", SAMPLE_ITEMS, "NB")

    assert cache_hit is False
    mock_client.translate_text.assert_called_once()


def test_second_call_same_language_serves_from_cache(monkeypatch):
    mock_client = _make_mock_client("Inspiser kranblokk.")
    monkeypatch.setattr("services.translator._deepl_client", mock_client)

    translate_checklist_items("cl-1", SAMPLE_ITEMS, "NB")
    _, cache_hit = translate_checklist_items("cl-1", SAMPLE_ITEMS, "NB")

    assert cache_hit is True
    assert mock_client.translate_text.call_count == 1


def test_severity_not_translated(monkeypatch):
    mock_client = _make_mock_client("TRANSLATED")
    monkeypatch.setattr("services.translator._deepl_client", mock_client)

    items, _ = translate_checklist_items("cl-1", SAMPLE_ITEMS, "FR")

    assert items[0]["severity"] == "CRITICAL"


def test_id_not_translated(monkeypatch):
    mock_client = _make_mock_client("TRANSLATED")
    monkeypatch.setattr("services.translator._deepl_client", mock_client)

    items, _ = translate_checklist_items("cl-1", SAMPLE_ITEMS, "FR")

    assert items[0]["id"] == "item-1"


def test_examination_frequency_not_translated(monkeypatch):
    mock_client = _make_mock_client("TRANSLATED")
    monkeypatch.setattr("services.translator._deepl_client", mock_client)

    items, _ = translate_checklist_items("cl-1", SAMPLE_ITEMS, "FR")

    assert items[0]["examination_frequency"] == "Pre-use"


def test_text_fields_are_translated(monkeypatch):
    mock_client = _make_mock_client("TRANSLATED")
    monkeypatch.setattr("services.translator._deepl_client", mock_client)

    items, _ = translate_checklist_items("cl-1", SAMPLE_ITEMS, "FR")

    assert items[0]["action"] == "TRANSLATED"
    assert items[0]["acceptance_criteria"] == "TRANSLATED"
    assert items[0]["failure_criteria"] == "TRANSLATED"
    assert items[0]["source_section"] == "TRANSLATED"


def test_different_checklist_id_creates_separate_cache_entry(monkeypatch):
    mock_client = _make_mock_client("TRANSLATED")
    monkeypatch.setattr("services.translator._deepl_client", mock_client)

    translate_checklist_items("cl-1", SAMPLE_ITEMS, "NB")
    _, cache_hit = translate_checklist_items("cl-2", SAMPLE_ITEMS, "NB")

    assert cache_hit is False
    assert mock_client.translate_text.call_count == 2
