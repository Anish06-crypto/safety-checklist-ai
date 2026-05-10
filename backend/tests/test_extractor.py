import hashlib
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_mock_parse_response(markdown: str):
    mock_response = MagicMock()
    mock_response.markdown = markdown
    return mock_response


def _write_temp_pdf(tmp_path, content: bytes = b"fake pdf content") -> str:
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(content)
    return str(pdf_file)


def test_returns_expected_keys(tmp_path):
    mock_response = _make_mock_parse_response("## Section 1\nInspect crown block.")
    with patch("services.extractor._get_client") as mock_get_client:
        mock_get_client.return_value.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path))

    assert "sample_text" in result
    assert "prose_text" in result
    assert "annex_blocks" in result
    assert "document_hash" in result


def test_prose_text_is_full_ade_markdown(tmp_path):
    markdown = "## DROPS Inspection\nCheck all overhead equipment."
    mock_response = _make_mock_parse_response(markdown)
    with patch("services.extractor._get_client") as mock_get_client:
        mock_get_client.return_value.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path))

    assert result["prose_text"] == markdown


def test_sample_text_is_first_500_chars(tmp_path):
    markdown = "A" * 1000
    mock_response = _make_mock_parse_response(markdown)
    with patch("services.extractor._get_client") as mock_get_client:
        mock_get_client.return_value.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path))

    assert result["sample_text"] == "A" * 500


def test_annex_blocks_is_empty_list(tmp_path):
    mock_response = _make_mock_parse_response("some markdown")
    with patch("services.extractor._get_client") as mock_get_client:
        mock_get_client.return_value.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path))

    assert result["annex_blocks"] == []


def test_document_hash_is_sha256_of_file(tmp_path):
    content = b"deterministic pdf content"
    expected_hash = hashlib.sha256(content).hexdigest()[:16]
    mock_response = _make_mock_parse_response("markdown content")
    with patch("services.extractor._get_client") as mock_get_client:
        mock_get_client.return_value.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path, content))

    assert result["document_hash"] == expected_hash


def test_document_hash_is_16_chars(tmp_path):
    mock_response = _make_mock_parse_response("markdown content")
    with patch("services.extractor._get_client") as mock_get_client:
        mock_get_client.return_value.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path))

    assert len(result["document_hash"]) == 16


def test_ade_called_with_correct_model(tmp_path):
    mock_response = _make_mock_parse_response("markdown")
    with patch("services.extractor._get_client") as mock_get_client:
        mock_client = mock_get_client.return_value
        mock_client.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        extract_from_pdf(_write_temp_pdf(tmp_path), filename="drops.pdf")

    call_kwargs = mock_client.parse.call_args
    assert call_kwargs.kwargs.get("model") == "dpt-2-latest"


def test_filename_passed_to_extractor(tmp_path):
    """Filename flows through — ADE uses it for file type inference."""
    mock_response = _make_mock_parse_response("markdown")
    with patch("services.extractor._get_client") as mock_get_client:
        mock_client = mock_get_client.return_value
        mock_client.parse.return_value = mock_response
        from services.extractor import extract_from_pdf
        # Should not raise — filename param accepted
        result = extract_from_pdf(_write_temp_pdf(tmp_path), filename="drops_procedure.pdf")

    assert result is not None


def test_pymupdf_fallback_when_use_ade_false(tmp_path, monkeypatch):
    """When USE_ADE=false, PyMuPDF is used and ADE client is never called."""
    monkeypatch.setenv("USE_ADE", "false")
    with patch("services.extractor._get_client") as mock_get_client:
        from services.extractor import extract_from_pdf
        result = extract_from_pdf(_write_temp_pdf(tmp_path))

    mock_get_client.assert_not_called()
    assert "prose_text" in result
    assert result["annex_blocks"] == []