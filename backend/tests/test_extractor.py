import hashlib
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Minimal valid PDF binary — PyMuPDF accepts this without error
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\n"
    b"startxref\n190\n%%EOF\n"
)


def _make_mock_parse_response(markdown: str):
    mock_response = MagicMock()
    mock_response.markdown = markdown
    return mock_response


def _write_temp_pdf(tmp_path, content: bytes = MINIMAL_PDF) -> str:
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(content)
    return str(pdf_file)


def test_returns_expected_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_ADE", "true")
    import services.extractor as ext
    ext._client = None
    mock_response = _make_mock_parse_response("## Section 1\nInspect crown block.")
    with patch("services.extractor.LandingAIADE") as mock_ade_class:
        mock_ade_class.return_value.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path))
    assert "sample_text" in result
    assert "prose_text" in result
    assert "annex_blocks" in result
    assert "document_hash" in result


def test_prose_text_is_full_ade_markdown(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_ADE", "true")
    import services.extractor as ext
    ext._client = None
    markdown = "## DROPS Inspection\nCheck all overhead equipment."
    mock_response = _make_mock_parse_response(markdown)
    with patch("services.extractor.LandingAIADE") as mock_ade_class:
        mock_ade_class.return_value.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path))
    assert result["prose_text"] == markdown


def test_sample_text_is_first_500_chars(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_ADE", "true")
    import services.extractor as ext
    ext._client = None
    markdown = "A" * 1000
    mock_response = _make_mock_parse_response(markdown)
    with patch("services.extractor.LandingAIADE") as mock_ade_class:
        mock_ade_class.return_value.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path))
    assert result["sample_text"] == "A" * 500


def test_annex_blocks_is_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_ADE", "true")
    import services.extractor as ext
    ext._client = None
    mock_response = _make_mock_parse_response("some markdown")
    with patch("services.extractor.LandingAIADE") as mock_ade_class:
        mock_ade_class.return_value.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path))
    assert result["annex_blocks"] == []


def test_document_hash_is_sha256_of_file(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_ADE", "true")
    import services.extractor as ext
    ext._client = None
    content = MINIMAL_PDF
    expected_hash = hashlib.sha256(content).hexdigest()[:16]
    mock_response = _make_mock_parse_response("markdown content")
    with patch("services.extractor.LandingAIADE") as mock_ade_class:
        mock_ade_class.return_value.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path, content))
    assert result["document_hash"] == expected_hash


def test_document_hash_is_16_chars(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_ADE", "true")
    import services.extractor as ext
    ext._client = None
    mock_response = _make_mock_parse_response("markdown content")
    with patch("services.extractor.LandingAIADE") as mock_ade_class:
        mock_ade_class.return_value.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path))
    assert len(result["document_hash"]) == 16


def test_ade_called_with_correct_model(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_ADE", "true")
    import services.extractor as ext
    ext._client = None
    mock_response = _make_mock_parse_response("markdown")
    with patch("services.extractor.LandingAIADE") as mock_ade_class:
        mock_instance = mock_ade_class.return_value
        mock_instance.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        extract_from_pdf(_write_temp_pdf(tmp_path), filename="drops.pdf")
    call_kwargs = mock_instance.parse.call_args
    assert call_kwargs.kwargs.get("model") == "dpt-2-latest"


def test_filename_passed_to_extractor(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_ADE", "true")
    import services.extractor as ext
    ext._client = None
    mock_response = _make_mock_parse_response("markdown")
    with patch("services.extractor.LandingAIADE") as mock_ade_class:
        mock_ade_class.return_value.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path), filename="drops_procedure.pdf")
    assert result is not None


def test_pymupdf_fallback_when_use_ade_false(tmp_path, monkeypatch):
    """When USE_ADE=false, PyMuPDF is used and ADE client is never called."""
    monkeypatch.setenv("USE_ADE", "false")
    import services.extractor as ext
    ext._client = None
    with patch("services.extractor.LandingAIADE") as mock_ade_class:
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path, MINIMAL_PDF))
    mock_ade_class.assert_not_called()
    assert "prose_text" in result
    assert result["annex_blocks"] == []