import hashlib
import os
import tempfile
from pathlib import Path
from landingai_ade import LandingAIADE

# Client is initialised once — reads VISION_AGENT_API_KEY from environment
_client = None


def _get_client() -> LandingAIADE:
    global _client
    if _client is None:
        _client = LandingAIADE()
    return _client


def _compute_hash(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def extract_from_pdf(file_path: str, filename: str = "document.pdf") -> dict:
    doc_hash = _compute_hash(file_path)

    if os.environ.get("USE_ADE", "true").lower() == "false":
        # PyMuPDF fallback — no ADE credits consumed
        import fitz
        doc = fitz.open(file_path)
        markdown = "\n\n".join(
            doc[i].get_text() for i in range(len(doc))
        )
        doc.close()
        return {
            "sample_text": markdown[:500],
            "prose_text": markdown,
            "chunks": [],
            "document_hash": doc_hash,
        }

    client = _get_client()

    # ADE parse — preserves tables, images, charts as structured markdown
    response = client.parse(
        document=Path(file_path),
        model="dpt-2-latest",
    )

    markdown = response.markdown

    # Sample text for DROPS detection — first 500 chars
    sample_text = markdown[:500]


    return {
        "sample_text": sample_text,
        "markdown": response.markdown,
        "prose_text": response.markdown,
        "chunks": [c.model_dump() for c in response.chunks],
        "grounding": response.grounding,
        "document_hash": doc_hash,
    }