import pytest
import os
from services.extractor import extract_from_pdf

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "drops_fixture.pdf")


def test_returns_non_empty_prose_text():
    result = extract_from_pdf(FIXTURE_PATH)
    assert isinstance(result["prose_text"], str)
    assert len(result["prose_text"]) > 0


def test_returns_non_empty_annex_blocks():
    result = extract_from_pdf(FIXTURE_PATH)
    assert isinstance(result["annex_blocks"], list)
    assert len(result["annex_blocks"]) > 0


def test_document_hash_is_non_empty_string():
    result = extract_from_pdf(FIXTURE_PATH)
    assert isinstance(result["document_hash"], str)
    assert len(result["document_hash"]) > 0


def test_document_hash_is_deterministic():
    result_a = extract_from_pdf(FIXTURE_PATH)
    result_b = extract_from_pdf(FIXTURE_PATH)
    assert result_a["document_hash"] == result_b["document_hash"]


def test_sample_text_is_first_500_chars():
    result = extract_from_pdf(FIXTURE_PATH)
    assert len(result["sample_text"]) <= 500


def test_intro_pages_not_in_prose_text():
    result = extract_from_pdf(FIXTURE_PATH)
    # Fixture pages 1-21 contain "Introduction Section" — must not appear in prose
    assert "Introduction Section" not in result["prose_text"]


def test_annex_pages_in_annex_blocks_not_prose():
    result = extract_from_pdf(FIXTURE_PATH)
    # Annex content must appear in annex_blocks
    all_annex_text = " ".join(
        " ".join(page["blocks"]) for page in result["annex_blocks"]
    )
    assert "Annex" in all_annex_text
    # Annex content must NOT appear in prose_text
    assert "Post Jarring Checklist" not in result["prose_text"]
