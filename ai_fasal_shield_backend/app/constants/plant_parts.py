from __future__ import annotations


# This is intentionally SMALL. It is not a symptom-translation dictionary.
# It only validates concrete plant-part words explicitly present in the raw
# Urdu/Punjabi/English Q1 answer.
PLANT_PART_TERMS: dict[str, tuple[str, ...]] = {
    "leaves": (
        "پتا", "پتہ", "پتے", "پتوں", "پتیاں", "leaf", "leaves",
    ),
    "stem": (
        "تنا", "تنے", "تنوں", "stem", "stalk",
    ),
    "roots": (
        "جڑ", "جڑیں", "جڑوں", "جڑاں", "root", "roots",
    ),
    "boll": (
        "ٹینڈا", "ٹینڈے", "ٹینڈوں", "ٹینڈیاں", "boll", "bolls",
    ),
    "panicle": (
        "بالی", "بالیاں", "بالیوں", "panicle", "panicles",
    ),
    "grain": (
        "دانہ", "دانے", "دانوں", "grain", "grains",
    ),
    "whole plant": (
        "پودا", "پودے", "پودوں", "بوٹا", "بوٹے", "whole plant",
    ),
}


def explicit_plant_part_mentions(raw_text: str | None) -> list[tuple[str, str]]:
    """Return explicit canonical plant parts with the exact raw term seen.

    Results are ordered by where the term first occurs in the farmer answer.
    This supports faithful context propagation after conjunction splitting, for
    example ``پتے پیلے ... اور مڑ رہے ہیں`` -> prefix the second fragment with
    the already-explicit raw subject ``پتے``.
    """
    text = raw_text or ""
    folded = text.casefold()
    if not folded.strip():
        return []

    matches: list[tuple[int, str, str]] = []
    for plant_part, terms in PLANT_PART_TERMS.items():
        best: tuple[int, str] | None = None
        # Prefer the earliest occurrence; on equal positions prefer the longer
        # term so "whole plant" wins over a shorter accidental substring.
        for term in terms:
            idx = folded.find(term.casefold())
            if idx < 0:
                continue
            if best is None or idx < best[0] or (idx == best[0] and len(term) > len(best[1])):
                best = (idx, term)
        if best is not None:
            matches.append((best[0], plant_part, best[1]))

    matches.sort(key=lambda item: item[0])
    return [(plant_part, raw_term) for _, plant_part, raw_term in matches]


def explicit_plant_parts(raw_text: str | None) -> list[str]:
    return [part for part, _ in explicit_plant_part_mentions(raw_text)]


def contains_explicit_plant_part(text: str | None) -> bool:
    return bool(explicit_plant_part_mentions(text))


def validate_affected_part(raw_text: str | None, qwen_part: str | None) -> str | None:
    """Prefer an explicitly named raw plant part over an LLM contradiction.

    If the raw answer does not contain one of our small high-confidence plant
    part terms, retain Qwen's value rather than inventing a part in Python.
    """
    explicit = explicit_plant_parts(raw_text)
    if not explicit:
        return qwen_part
    if len(explicit) == 1:
        return explicit[0]
    return " and ".join(explicit)
