"""Frozen controlled dictionary and limited lexical normalisation rules.

The dictionary contains 55 canonical analytical entries. Surface-form aliases are
restricted to source-verified lexical variants observed in the MOH corpus. OCR
misreadings are not repaired through this layer.
"""

from __future__ import annotations

import re


DISEASE_TERMS = [
    "fever",
    "scarlet fever",
    "cholera",
    "smallpox",
    "typhus",
    "typhoid",
    "measles",
    "influenza",
    "diphtheria",
    "diarrhoea",
    "consumption",
    "notification",
    "isolation",
]

SANITARY_TERMS = [
    "sanitary",
    "sanitation",
    "sewer",
    "sewers",
    "sewage",
    "drainage",
    "drain",
    "drains",
    "nuisance",
    "nuisances",
    "filth",
    "dirty",
    "refuse",
    "water supply",
]

HOUSING_TERMS = [
    "overcrowding",
    "overcrowded",
    "lodging house",
    "common lodging house",
    "dwellings",
    "houses",
    "rooms",
    "tenement",
    "model dwellings",
]

GOVERNANCE_TERMS = [
    "inspection",
    "inspections",
    "inspector",
    "notices",
    "summonses",
    "sanitary authority",
    "medical officer",
    "board",
    "vestry",
    "local government board",
]

INEQUALITY_TERMS = [
    "working classes",
    "working class",
    "poor",
    "poorer",
    "poorest",
    "poverty",
    "destitute",
    "lodgers",
    "infirmary",
]

TERM_GROUPS = {
    "disease": DISEASE_TERMS,
    "sanitary": SANITARY_TERMS,
    "housing": HOUSING_TERMS,
    "governance": GOVERNANCE_TERMS,
    "inequality": INEQUALITY_TERMS,
}

# Source-verified lexical variants only. These are genuine forms visible in the
# source text, not OCR corrections. Canonical forms are always accepted as well.
LEXICAL_VARIANTS = {
    "smallpox": ["small-pox"],
    "lodging house": [
        "lodging-house",
        "lodginghouse",
        "lodging houses",
        "lodging-houses",
        "lodginghouses",
    ],
    "common lodging house": [
        "common lodging-house",
        "common lodginghouse",
        "common lodging houses",
        "common lodging-houses",
        "common lodginghouses",
    ],
    "water supply": ["water-supply"],
    "working class": ["working-class"],
}

# Retrieval-type metadata used in Appendix A. Direct entries retrieve the named
# concept. Indirect entries broaden retrieval but require contextual review.
RETRIEVAL_TYPE = {term: "direct" for terms in TERM_GROUPS.values() for term in terms}
RETRIEVAL_TYPE.update({"lodgers": "indirect administrative marker", "infirmary": "indirect institutional marker"})

RATIONALE = {
    "lodging house": "Accommodation form; social meaning is assessed through contextual review rather than assigned by the dictionary.",
    "common lodging house": "Accommodation form and regulated housing institution; retained in housing.",
    "lodgers": "Administrative/social classification of persons; contextual review is required before treating a hit as inequality evidence.",
    "infirmary": "Context-dependent institutional marker; six retrieved passages were reviewed individually and four contributed to inequality interpretation.",
    "smallpox": "Disease concept with source-verified hyphenated surface form in the corpus.",
    "water supply": "Sanitary infrastructure concept with source-verified hyphenated surface form.",
    "working class": "Direct socioeconomic label with source-verified hyphenated surface form.",
}

OCR_EXCLUSIONS = {
    "LodingHouses": "OCR-induced misreading of LodgingHouses; documented during source verification and not added to lexical-normalisation aliases."
}


def clean_text(text: str) -> str:
    """Normalise case and punctuation while retaining hyphens for auditability."""
    text = str(text).lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9'\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def all_surface_forms(canonical: str) -> list[str]:
    """Return canonical term plus the frozen set of source-verified variants."""
    return [canonical, *LEXICAL_VARIANTS.get(canonical, [])]


def build_surface_records() -> list[tuple[str, str, str, str]]:
    """Return (category, canonical, surface, cleaned_surface), longest first."""
    rows: list[tuple[str, str, str, str]] = []
    for category, terms in TERM_GROUPS.items():
        for canonical in terms:
            for surface in all_surface_forms(canonical):
                rows.append((category, canonical, surface, clean_text(surface)))
    rows.sort(key=lambda row: (-len(row[3]), row[3], row[1]))
    return rows


SURFACE_RECORDS = build_surface_records()


def count_canonical_terms_nonoverlapping(text_clean: str) -> dict[tuple[str, str], int]:
    """Count non-overlapping surface-form hits and aggregate to canonical entries."""
    occupied = [False] * len(text_clean)
    counts = {
        (category, canonical): 0
        for category, terms in TERM_GROUPS.items()
        for canonical in terms
    }

    for category, canonical, _surface, surface_clean in SURFACE_RECORDS:
        pattern = rf"(?<![a-z0-9]){re.escape(surface_clean)}(?![a-z0-9])"
        for match in re.finditer(pattern, text_clean):
            start, end = match.span()
            if any(occupied[start:end]):
                continue
            counts[(category, canonical)] += 1
            for position in range(start, end):
                occupied[position] = True
    return counts


def matched_canonical_terms_nonoverlapping(text_clean: str) -> set[tuple[str, str]]:
    """Return unique (canonical, category) entries found in a passage."""
    occupied = [False] * len(text_clean)
    matched: set[tuple[str, str]] = set()

    for category, canonical, _surface, surface_clean in SURFACE_RECORDS:
        pattern = rf"(?<![a-z0-9]){re.escape(surface_clean)}(?![a-z0-9])"
        for match in re.finditer(pattern, text_clean):
            start, end = match.span()
            if any(occupied[start:end]):
                continue
            matched.add((canonical, category))
            for position in range(start, end):
                occupied[position] = True
    return matched
