import uuid
from models.checklist import ChecklistItem, DROPSSeverity

IMPERATIVE_VERBS = {
    "check", "inspect", "verify", "ensure", "confirm",
    "examine", "test", "measure", "review", "assess",
}


def parse_annex_blocks(annex_pages: list[dict]) -> list[ChecklistItem]:
    items = []
    for page in annex_pages:
        source = f"Annex — Page {page['page']}"
        for block in page["blocks"]:
            first_word = block.split()[0].lower().rstrip(".,;:") if block.split() else ""
            if first_word in IMPERATIVE_VERBS:
                items.append(ChecklistItem(
                    id=str(uuid.uuid4()),
                    action=block,
                    acceptance_criteria="Meets DROPS inspection requirements.",
                    failure_criteria=(
                        "Remove from service immediately. "
                        "Tag component and notify supervisor before operations resume."
                    ),
                    severity=DROPSSeverity.MAJOR,
                    source_section=source,
                    examination_frequency="Pre-use",
                ))
    return items
