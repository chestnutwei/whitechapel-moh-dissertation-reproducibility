"""Run controlled keyword counts on the final narrative MOH corpus."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
PASSAGES_PATH = OUTPUT_TABLES_DIR / "moh_narrative_passages.csv"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from moh_keyword_dictionary import (  # noqa: E402
    TERM_GROUPS,
    clean_text,
    count_canonical_terms_nonoverlapping,
)


def main() -> None:
    passages = pd.read_csv(PASSAGES_PATH)
    narrative = passages[passages["likely_narrative"] == True].copy()
    narrative["text_clean"] = narrative["passage_text"].map(clean_text)
    narrative_word_totals = narrative.groupby("report_year")["word_count"].sum().to_dict()

    rows = []
    for _, passage in narrative.iterrows():
        term_counts = count_canonical_terms_nonoverlapping(passage["text_clean"])
        for category, terms in TERM_GROUPS.items():
            for term in terms:
                rows.append(
                    {
                        "report_year": int(passage["report_year"]),
                        "passage_id": passage["passage_id"],
                        "category": category,
                        "term": term,
                        "raw_count": term_counts[(category, term)],
                        "passage_word_count": int(passage["word_count"]),
                    }
                )

    counts = pd.DataFrame(rows)
    by_year = (
        counts.groupby(["report_year", "category", "term"], as_index=False)
        .agg(raw_count=("raw_count", "sum"))
        .sort_values(["report_year", "category", "term"])
    )
    by_year["narrative_word_count"] = by_year["report_year"].map(narrative_word_totals).fillna(0).astype(int)
    by_year["frequency_per_10000_words"] = by_year.apply(
        lambda row: (row["raw_count"] / row["narrative_word_count"] * 10000) if row["narrative_word_count"] else 0,
        axis=1,
    )

    total_words = int(narrative["word_count"].sum())
    summary = (
        by_year.groupby(["category", "term"], as_index=False)
        .agg(raw_count=("raw_count", "sum"))
        .sort_values(["category", "raw_count", "term"], ascending=[True, False, True])
    )
    summary["narrative_word_count"] = total_words
    summary["frequency_per_10000_words"] = summary["raw_count"] / total_words * 10000

    by_year.to_csv(OUTPUT_TABLES_DIR / "moh_narrative_keyword_counts.csv", index=False)
    summary.to_csv(OUTPUT_TABLES_DIR / "moh_narrative_keyword_summary.csv", index=False)

    print(f"Wrote {len(by_year)} narrative keyword rows.")
    print(f"Wrote {len(summary)} canonical dictionary summary rows.")
    print(f"Narrative passages counted: {len(narrative)}")
    print(f"Narrative words counted: {total_words}")


if __name__ == "__main__":
    main()
