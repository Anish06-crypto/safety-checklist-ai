import pytest
from services.detector import detect_document_type


def test_detects_drops_keyword():
    result = detect_document_type("This is a DROPS inspection procedure document.")
    assert result["is_drops"] is True


def test_detects_dropped_object_case_insensitive():
    result = detect_document_type("procedures for dropped object prevention on site.")
    assert result["is_drops"] is True


def test_returns_false_for_non_drops_document():
    result = detect_document_type("This is a LOLER thorough examination report for lifting equipment.")
    assert result["is_drops"] is False


def test_returns_matched_keywords():
    result = detect_document_type("DROPS Calculator and dropped object prevention.")
    assert "DROPS" in result["detected_keywords"]
    assert "dropped object" in result["detected_keywords"]


def test_returns_empty_keywords_when_no_match():
    result = detect_document_type("Health and safety at work regulations.")
    assert result["detected_keywords"] == []


def test_handles_empty_string():
    result = detect_document_type("")
    assert result["is_drops"] is False
    assert result["detected_keywords"] == []
