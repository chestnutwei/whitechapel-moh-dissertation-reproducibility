"""
Extract likely narrative MOH passages for spatial reference using a Whitechapel gazetteer.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from place_matching import match_places, normalize, surface_forms_from_gazetteer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
PASSAGES_PATH = OUTPUT_TABLES_DIR / "moh_narrative_passages.csv"
METADATA_PATH = PROJECT_ROOT / "data" / "metadata" / "moh_reports_metadata.csv"
GAZETTEER_PATH = PROJECT_ROOT / "data" / "gazetteer" / "whitechapel_places_gazetteer.csv"

CANDIDATE_OUTPUT_PATH = OUTPUT_TABLES_DIR / "moh_spatial_reference_candidates.csv"


def clean_text(text: str) -> str:
    return normalize(text)


def main() -> None:
    passages = pd.read_csv(PASSAGES_PATH)
    metadata = pd.read_csv(METADATA_PATH)
    gazetteer = pd.read_csv(GAZETTEER_PATH)

    source_by_year = {
        int(row.report_year): row.local_file
        for row in metadata.itertuples()
        if pd.notna(row.report_year)
    }

    surface_forms = surface_forms_from_gazetteer(gazetteer)

    narrative = passages[passages["likely_narrative"] == True].copy()
    narrative["text_clean"] = narrative["passage_text"].map(clean_text)

    candidate_rows = []
    for _, passage in narrative.iterrows():
        accepted, _excluded = match_places(passage["text_clean"], surface_forms)
        matched_places = list(dict.fromkeys(match.standard_name for match in accepted))
        if not accepted:
            continue

        candidate_rows.append(
            {
                "report_year": int(passage["report_year"]),
                "passage_id": passage["passage_id"],
                "matched_places": "; ".join(dict.fromkeys(matched_places)),
                "passage_text": passage["passage_text"],
                "source_file": source_by_year.get(int(passage["report_year"]), ""),
                "notes": f"Likely narrative passage {passage['passage_id']}; spatial reference candidate; verify OCR/source before quotation.",
            }
        )

    candidates = pd.DataFrame(
        candidate_rows,
        columns=["report_year", "passage_id", "matched_places", "passage_text", "source_file", "notes"],
    ).sort_values(["report_year", "passage_id"])

    candidates.to_csv(CANDIDATE_OUTPUT_PATH, index=False)

    print(f"Wrote {len(candidates)} spatial candidate rows.")


if __name__ == "__main__":
    main()
