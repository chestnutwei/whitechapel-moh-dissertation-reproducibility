"""
Find place and keyword co-occurrences within +/-50 words in the MOH corpus.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path

import pandas as pd

from place_matching import match_places, normalize, surface_forms_from_gazetteer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GAZETTEER_PATH = PROJECT_ROOT / "data" / "gazetteer" / "whitechapel_places_gazetteer.csv"
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
CORPUS_PATH = OUTPUT_TABLES_DIR / "moh_corpus_clean.csv"
WINDOW_WORDS = 50

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
]

TERM_GROUPS = {
    "disease": DISEASE_TERMS,
    "sanitary": SANITARY_TERMS,
    "housing": HOUSING_TERMS,
    "governance": GOVERNANCE_TERMS,
}


def tokenize(text_clean: str) -> list[str]:
    return re.findall(r"\b[a-z0-9']+\b", text_clean.lower())


def phrase_positions(tokens: list[str], phrase: str) -> list[int]:
    phrase_tokens = tokenize(normalize(phrase))
    if not phrase_tokens:
        return []
    width = len(phrase_tokens)
    return [
        index
        for index in range(0, len(tokens) - width + 1)
        if tokens[index : index + width] == phrase_tokens
    ]


def main() -> None:
    gazetteer = pd.read_csv(GAZETTEER_PATH)
    corpus = pd.read_csv(CORPUS_PATH)
    surface_forms = surface_forms_from_gazetteer(gazetteer)

    term_records = []
    for category, terms in TERM_GROUPS.items():
        for term in terms:
            term_records.append({"category": category, "term": term, "term_norm": normalize(term)})

    rows = []
    summary_counter = defaultdict(int)

    for _, doc in corpus.iterrows():
        text_clean = normalize(str(doc["text_clean"]))
        tokens = tokenize(text_clean)
        token_starts = [match.start() for match in re.finditer(r"\b[a-z0-9']+\b", text_clean)]
        accepted_places, _excluded_places = match_places(text_clean, surface_forms)
        place_matches = defaultdict(list)
        for match in accepted_places:
            token_position = bisect_right(token_starts, match.start) - 1
            place_matches[match.place_id].append((token_position, match.surface_form))
        term_positions = {
            record["term"]: phrase_positions(tokens, record["term_norm"])
            for record in term_records
        }

        for _, place in gazetteer.iterrows():
            retained = place_matches[str(place["place_id"])]
            place_positions = [position for position, _surface in retained]
            matched_variants = sorted({surface for _position, surface in retained})

            if not place_positions:
                continue

            for record in term_records:
                positions = term_positions[record["term"]]
                if not positions:
                    continue
                cooccurrences = 0
                for place_pos in place_positions:
                    for term_pos in positions:
                        if abs(term_pos - place_pos) <= WINDOW_WORDS:
                            cooccurrences += 1
                if cooccurrences:
                    row = {
                        "report_id": doc["report_id"],
                        "report_year": int(doc["report_year"]),
                        "place_id": place["place_id"],
                        "standard_name": place["standard_name"],
                        "matched_variants": "; ".join(sorted(set(matched_variants))),
                        "category": record["category"],
                        "term": record["term"],
                        "window_words": WINDOW_WORDS,
                        "cooccurrence_count": cooccurrences,
                    }
                    rows.append(row)
                    summary_counter[(place["place_id"], place["standard_name"], record["category"], record["term"])] += cooccurrences

    cooccurrence = pd.DataFrame(rows)
    if cooccurrence.empty:
        cooccurrence = pd.DataFrame(
            columns=[
                "report_id",
                "report_year",
                "place_id",
                "standard_name",
                "matched_variants",
                "category",
                "term",
                "window_words",
                "cooccurrence_count",
            ]
        )

    summary_rows = [
        {
            "place_id": place_id,
            "standard_name": standard_name,
            "category": category,
            "term": term,
            "cooccurrence_count": count,
        }
        for (place_id, standard_name, category, term), count in summary_counter.items()
    ]
    summary = pd.DataFrame(summary_rows)
    if summary.empty:
        summary = pd.DataFrame(columns=["place_id", "standard_name", "category", "term", "cooccurrence_count"])
    else:
        summary = summary.sort_values(["cooccurrence_count", "standard_name", "term"], ascending=[False, True, True])

    cooccurrence.to_csv(OUTPUT_TABLES_DIR / "moh_place_term_cooccurrence.csv", index=False)
    summary.to_csv(OUTPUT_TABLES_DIR / "moh_top_place_term_pairs.csv", index=False)

    print(f"Wrote {len(cooccurrence)} co-occurrence rows.")
    print(f"Wrote {len(summary)} top pair rows.")


if __name__ == "__main__":
    main()
