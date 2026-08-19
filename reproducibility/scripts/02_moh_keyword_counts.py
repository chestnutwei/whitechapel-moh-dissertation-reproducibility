"""
Count controlled disease, sanitary, housing, and governance terms by report year.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
CORPUS_PATH = OUTPUT_TABLES_DIR / "moh_corpus_clean.csv"

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


def clean_term(term: str) -> str:
    term = term.lower().replace("&", " and ")
    term = re.sub(r"[^a-z0-9'\s-]", " ", term)
    term = re.sub(r"\s+", " ", term)
    return term.strip()


def count_term(text_clean: str, term: str) -> int:
    term_clean = clean_term(term)
    pattern = rf"(?<![a-z0-9]){re.escape(term_clean)}(?![a-z0-9])"
    return len(re.findall(pattern, text_clean))


def main() -> None:
    corpus = pd.read_csv(CORPUS_PATH)
    rows = []

    for _, doc in corpus.iterrows():
        text_clean = str(doc["text_clean"])
        word_count = int(doc["word_count"])
        for category, terms in TERM_GROUPS.items():
            for term in terms:
                raw_count = count_term(text_clean, term)
                rows.append(
                    {
                        "report_id": doc["report_id"],
                        "report_year": int(doc["report_year"]),
                        "category": category,
                        "term": term,
                        "raw_count": raw_count,
                        "word_count": word_count,
                        "frequency_per_10000_words": (raw_count / word_count * 10000) if word_count else 0,
                    }
                )

    by_year = pd.DataFrame(rows).sort_values(["report_year", "category", "term"])
    summary = (
        by_year.groupby(["category", "term"], as_index=False)
        .agg(raw_count=("raw_count", "sum"), word_count=("word_count", "sum"))
        .sort_values(["category", "raw_count", "term"], ascending=[True, False, True])
    )
    summary["frequency_per_10000_words"] = summary.apply(
        lambda row: (row["raw_count"] / row["word_count"] * 10000) if row["word_count"] else 0,
        axis=1,
    )

    by_year.to_csv(OUTPUT_TABLES_DIR / "moh_keyword_counts_by_year.csv", index=False)
    summary.to_csv(OUTPUT_TABLES_DIR / "moh_keyword_counts_summary.csv", index=False)

    print(f"Wrote {len(by_year)} by-year keyword rows.")
    print(f"Wrote {len(summary)} summary keyword rows.")


if __name__ == "__main__":
    main()
