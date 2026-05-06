DROPS_KEYWORDS = [
    "DROPS",
    "dropped object",
    "Dropped Object Prevention",
    "DROPS Calculator",
]


def detect_document_type(text: str) -> dict:
    text_upper = text.upper()
    matched = [kw for kw in DROPS_KEYWORDS if kw.upper() in text_upper]
    return {
        "is_drops": len(matched) > 0,
        "detected_keywords": matched,
    }
