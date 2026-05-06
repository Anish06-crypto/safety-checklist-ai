import pytest
from services.table_parser import parse_annex_blocks
from models.checklist import ChecklistItem, DROPSSeverity

SAMPLE_ANNEX = [
    {
        "page": 42,
        "blocks": [
            "Annex C — Post Jarring Checklist",
            "Check crown block assembly sheave pins and keeper plates.",
            "Inspect secondary retention wires for kinking or corrosion.",
            "Verify all fasteners are secure and undamaged.",
            "Training Matrix overview.",
            "Inspect hook latch mechanism for positive engagement.",
        ],
    }
]


def test_returns_list_of_checklist_items():
    result = parse_annex_blocks(SAMPLE_ANNEX)
    assert isinstance(result, list)
    assert all(isinstance(item, ChecklistItem) for item in result)


def test_imperative_verb_blocks_are_included():
    result = parse_annex_blocks(SAMPLE_ANNEX)
    actions = [item.action for item in result]
    assert any("Check crown block" in a for a in actions)
    assert any("Inspect secondary retention" in a for a in actions)
    assert any("Verify all fasteners" in a for a in actions)
    assert any("Inspect hook latch" in a for a in actions)


def test_non_imperative_blocks_are_excluded():
    result = parse_annex_blocks(SAMPLE_ANNEX)
    actions = [item.action for item in result]
    # "Training Matrix overview." does not start with an imperative verb
    assert not any("Training Matrix" in a for a in actions)
    # "Annex C — Post Jarring Checklist" is a heading, not an action
    assert not any("Post Jarring Checklist" in a for a in actions)


def test_each_item_has_non_empty_action():
    result = parse_annex_blocks(SAMPLE_ANNEX)
    assert all(len(item.action) > 0 for item in result)


def test_severity_defaults_to_major():
    result = parse_annex_blocks(SAMPLE_ANNEX)
    assert all(item.severity == DROPSSeverity.MAJOR for item in result)


def test_examination_frequency_defaults_to_pre_use():
    result = parse_annex_blocks(SAMPLE_ANNEX)
    assert all(item.examination_frequency == "Pre-use" for item in result)


def test_returns_empty_list_for_empty_input():
    result = parse_annex_blocks([])
    assert result == []
