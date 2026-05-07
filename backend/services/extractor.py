import fitz
import hashlib


def _is_annex_page(page) -> bool:
    blocks = page.get_text("blocks")
    if not blocks:
        return False
    # Check first 4 blocks — real PDFs often have page numbers or headers
    # before the "Annex X" heading
    for block in blocks[:4]:
        text = block[4].strip().upper()
        if text.startswith("ANNEX"):
            return True
    return False


def _compute_hash(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def extract_from_pdf(file_path: str) -> dict:
    doc = fitz.open(file_path)

    sample_text = doc[0].get_text()[:500] if len(doc) > 0 else ""

    prose_text = ""
    for page_num in range(21, min(35, len(doc))):
        page = doc[page_num]
        if not _is_annex_page(page):
            prose_text += page.get_text()

    annex_blocks = []
    for page_num in range(39, len(doc)):
        page = doc[page_num]
        if _is_annex_page(page):
            blocks = page.get_text("blocks")
            annex_blocks.append({
                "page": page_num + 1,
                "blocks": [b[4].strip() for b in blocks if b[4].strip()],
            })

    doc_hash = _compute_hash(file_path)
    doc.close()

    return {
        "sample_text": sample_text,
        "prose_text": prose_text,
        "annex_blocks": annex_blocks,
        "document_hash": doc_hash,
    }
