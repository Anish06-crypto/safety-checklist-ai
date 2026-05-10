from pydantic import BaseModel
from enum import Enum


class DROPSSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class ChecklistItem(BaseModel):
    id: str
    action: str
    acceptance_criteria: str
    failure_criteria: str
    severity: DROPSSeverity
    source_section: str
    examination_frequency: str
    chunk_id: str | None = None


class GeneratedChecklist(BaseModel):
    id: str
    document_name: str
    generated_at: str
    source_document_hash: str
    status: str
    items: list[ChecklistItem]
    item_count: int
