"""Extract close-reading candidate records from the final narrative MOH corpus."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
PASSAGES_PATH = OUTPUT_TABLES_DIR / "moh_narrative_passages.csv"
METADATA_PATH = PROJECT_ROOT / "data" / "metadata" / "moh_reports_metadata.csv"
OUTPUT_PATH = OUTPUT_TABLES_DIR / "moh_close_reading_candidates.csv"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from moh_keyword_dictionary import (  # noqa: E402
    clean_text,
    matched_canonical_terms_nonoverlapping,
)


def main() -> None:
    passages = pd.read_csv(PASSAGES_PATH)
    metadata = pd.read_csv(METADATA_PATH)

    source_by_year = {
        int(row.report_year): row.local_file
        for row in metadata.itertuples()
        if pd.notna(row.report_year)
    }

    narrative = passages[passages["likely_narrative"] == True].copy()
    rows = []

    for _, passage in narrative.iterrows():
        text_clean = clean_text(passage["passage_text"])
        matched = matched_canonical_terms_nonoverlapping(text_clean)

        for term, category in sorted(matched, key=lambda item: (item[1], item[0])):
            rows.append(
                {
                    "report_year": int(passage["report_year"]),
                    "passage_id": passage["passage_id"],
                    "term": term,
                    "category": category,
                    "word_count": int(passage["word_count"]),
                    "passage_text": passage["passage_text"],
                    "source_file": source_by_year.get(int(passage["report_year"]), ""),
                }
            )

    candidates = pd.DataFrame(rows).sort_values(
        ["report_year", "passage_id", "category", "term"]
    )
    candidates.to_csv(OUTPUT_PATH, index=False)

    print(f"Wrote {len(candidates)} close-reading candidate records to {OUTPUT_PATH}.")
    print(f"Distinct candidate passages: {candidates['passage_id'].nunique()}")
    if not candidates.empty:
        print(candidates.groupby("category").size().sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main()
