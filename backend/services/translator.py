import os
import deepl

SUPPORTED_LANGUAGES = {
    "EN": "English", "NB": "Norwegian", "FR": "French",
    "AR": "Arabic", "PL": "Polish", "ID": "Indonesian",
    "ES": "Spanish", "PT-BR": "Portuguese", "NL": "Dutch", "RO": "Romanian",
}

_ENGLISH_CODES = {"EN", "EN-GB", "EN-US"}
_FIELDS_TO_TRANSLATE = ["action", "acceptance_criteria", "failure_criteria", "source_section"]
_PROTECTED_FIELDS = {"severity", "id", "examination_frequency"}

_cache: dict = {}
_deepl_client = None


def _get_client():
    global _deepl_client
    if _deepl_client is None:
        _deepl_client = deepl.Translator(os.environ.get("DEEPL_API_KEY", ""))
    return _deepl_client


def _clear_cache():
    _cache.clear()


def translate_checklist_items(
    checklist_id: str,
    items: list[dict],
    target_language: str,
) -> tuple[list[dict], bool]:
    if target_language.upper() in _ENGLISH_CODES:
        return items, True

    cache_key = f"{checklist_id}:{target_language.upper()}"
    if cache_key in _cache:
        return _cache[cache_key], True

    client = _get_client()
    translated_items = []

    for item in items:
        fields = [item.get(f, "") for f in _FIELDS_TO_TRANSLATE]
        results = client.translate_text(fields, target_lang=target_language)
        translated_items.append({
            **item,
            "action": results[0].text,
            "acceptance_criteria": results[1].text,
            "failure_criteria": results[2].text,
            "source_section": results[3].text,
        })

    _cache[cache_key] = translated_items
    return translated_items, False
