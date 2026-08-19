"""Match gazetteer places with longest-first, non-overlapping spans."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from place_matching import (
    match_places,
    nested_surface_form_pairs,
    surface_forms_from_gazetteer,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GAZETTEER_PATH = PROJECT_ROOT / "data" / "gazetteer" / "whitechapel_places_gazetteer.csv"
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
CORPUS_PATH = OUTPUT_TABLES_DIR / "moh_corpus_clean.csv"
AUDIT_DIR = PROJECT_ROOT / "audit"


UNIT_TESTS = [
    ("Mile End New Town", {"Mile End New Town": 1, "Mile End Old Town": 0, "Mile End": 0}),
    ("Mile End Old Town", {"Mile End New Town": 0, "Mile End Old Town": 1, "Mile End": 0}),
    ("Mile End", {"Mile End New Town": 0, "Mile End Old Town": 0, "Mile End": 1}),
    (
        "Mile End New Town and Mile End Old Town",
        {"Mile End New Town": 1, "Mile End Old Town": 1, "Mile End": 0},
    ),
]


def run_unit_tests(surface_forms) -> pd.DataFrame:
    rows = []
    for test_number, (text, expected) in enumerate(UNIT_TESTS, 1):
        accepted, _excluded = match_places(text, surface_forms)
        actual = Counter(match.standard_name for match in accepted)
        status = "PASS" if all(actual[name] == count for name, count in expected.items()) else "FAIL"
        rows.append(
            {
                "test_number": test_number,
                "text": text,
                "expected": "; ".join(f"{name}={count}" for name, count in expected.items()),
                "actual": "; ".join(f"{name}={actual[name]}" for name in expected),
                "status": status,
            }
        )
    tests = pd.DataFrame(rows)
    if not (tests["status"] == "PASS").all():
        raise AssertionError(f"Place matcher unit-test failure:\n{tests}")
    return tests


def main() -> None:
    gazetteer = pd.read_csv(GAZETTEER_PATH)
    corpus = pd.read_csv(CORPUS_PATH)
    surface_forms = surface_forms_from_gazetteer(gazetteer)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_TABLES_DIR.mkdir(parents=True, exist_ok=True)

    unit_tests = run_unit_tests(surface_forms)
    unit_tests.to_csv(AUDIT_DIR / "place_matcher_unit_tests.csv", index=False)
    nested_audit = pd.DataFrame(nested_surface_form_pairs(surface_forms))
    nested_audit.to_csv(AUDIT_DIR / "gazetteer_nested_name_audit.csv", index=False)
    if nested_audit.empty or not (nested_audit["test_status"] == "PASS").all():
        raise AssertionError("Gazetteer nested-name audit did not pass")

    rows = []
    accepted_audit_rows = []
    excluded_audit_rows = []

    for _, doc in corpus.iterrows():
        accepted, excluded = match_places(str(doc["text_clean"]), surface_forms)
        matches_by_place = defaultdict(list)
        for match in accepted:
            matches_by_place[match.place_id].append(match)
            accepted_audit_rows.append(
                {
                    "report_id": doc["report_id"],
                    "report_year": int(doc["report_year"]),
                    **asdict(match),
                }
            )
        for match in excluded:
            excluded_audit_rows.append(
                {
                    "report_id": doc["report_id"],
                    "report_year": int(doc["report_year"]),
                    **asdict(match),
                }
            )

        for _, place in gazetteer.iterrows():
            retained = matches_by_place[str(place["place_id"])]
            rows.append(
                {
                    "place_id": place["place_id"],
                    "standard_name": place["standard_name"],
                    "type": place["type"],
                    "report_id": doc["report_id"],
                    "report_year": int(doc["report_year"]),
                    "mention_count": len(retained),
                    "matched_variants": "; ".join(sorted({match.surface_form for match in retained})),
                }
            )

    by_year = pd.DataFrame(rows).sort_values(["report_year", "standard_name"])
    summary = (
        by_year.groupby(["place_id", "standard_name", "type"], as_index=False)
        .agg(total_mentions=("mention_count", "sum"), years_mentioned=("mention_count", lambda values: int((values > 0).sum())))
        .sort_values(["total_mentions", "standard_name"], ascending=[False, True])
    )

    by_year.to_csv(OUTPUT_TABLES_DIR / "moh_place_mentions_by_year.csv", index=False)
    summary.to_csv(OUTPUT_TABLES_DIR / "moh_place_mentions_summary.csv", index=False)
    pd.DataFrame(accepted_audit_rows).to_csv(
        OUTPUT_TABLES_DIR / "moh_place_accepted_spans.csv", index=False
    )
    pd.DataFrame(excluded_audit_rows).to_csv(
        OUTPUT_TABLES_DIR / "moh_place_excluded_nested_spans.csv", index=False
    )

    print(f"Wrote {len(by_year)} place-by-year rows.")
    print(f"Wrote {len(summary)} place summary rows.")
    print(f"Accepted spans: {len(accepted_audit_rows)}; excluded overlapping spans: {len(excluded_audit_rows)}.")
    print(f"Matcher unit tests: {len(unit_tests)} PASS; gazetteer nested pairs: {len(nested_audit)} PASS.")


if __name__ == "__main__":
    main()
