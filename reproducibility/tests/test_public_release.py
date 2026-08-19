#!/usr/bin/env python3
"""Independent public-release invariants; exits non-zero on any failure."""

from __future__ import annotations

import csv
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

# The test dynamically imports the frozen dictionary below. Disable bytecode
# writes so a normal invocation does not create source-tree __pycache__ debris.
sys.dont_write_bytecode = True

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
TECH = TABLES / "technical"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    check(
        sys.version_info[:2] == (3, 12),
        "Python 3.12.x is supported; the canonical verified release is 3.12.13",
    )

    quality = rows(TABLES / "moh_quality_check.csv")
    passages = rows(TABLES / "moh_narrative_passages.csv")
    candidates = rows(TABLES / "moh_close_reading_candidates.csv")
    inequality = rows(TECH / "inequality_marker_sensitivity_summary.csv")
    assignments = rows(TECH / "nmf_component_assignment.csv")
    workplaces = rows(TECH / "workplace_address_summary.csv")
    spatial = rows(TABLES / "moh_spatial_reference_candidates.csv")
    validation = rows(TECH / "spatial_disease_validation_summary.csv")
    points = rows(ROOT / "maps" / "coordinates" / "place_map_points_verified.csv")
    outside = rows(ROOT / "maps" / "coordinates" / "out_of_sheet_place_references.csv")

    check(len(quality) == 10, "expected 10 source reports")
    check(sum(int(row["word_count"]) for row in quality) == 121057, "source word total")
    check(len(passages) == 657, "passage total")
    check(sum(row["likely_narrative"] == "True" for row in passages) == 275, "narrative total")
    check(sum(row["likely_table_context"] == "True" for row in passages) == 382, "table total")
    check(sum(int(row["word_count"]) for row in passages if row["likely_narrative"] == "True") == 51428, "narrative words")

    dictionary_path = ROOT / "scripts" / "moh_keyword_dictionary.py"
    spec = importlib.util.spec_from_file_location("frozen_dictionary", dictionary_path)
    dictionary = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(dictionary)
    check(sum(len(values) for values in dictionary.TERM_GROUPS.values()) == 55, "dictionary size")
    check(sum(len(values) for values in dictionary.LEXICAL_VARIANTS.values()) == 13, "lexical variants")

    check(len(candidates) == 804, "candidate row total")
    check(len({row["passage_id"] for row in candidates}) == 250, "distinct candidates")
    expected_categories = {"governance": 264, "sanitary": 249, "housing": 158, "disease": 86, "inequality": 47}
    check(Counter(row["category"] for row in candidates) == Counter(expected_categories), "category candidate counts")

    check(inequality == [
        {"scope": "all", "candidate_records": "47", "distinct_passages": "41", "raw_hits": "57"},
        {"scope": "direct_only", "candidate_records": "33", "distinct_passages": "29", "raw_hits": "36"},
    ], "inequality sensitivity")

    manifest = json.loads((TECH / "topic_model_manifest.json").read_text(encoding="utf-8"))
    check(manifest["narrative_passages_total"] == 275, "NMF corpus total")
    check(manifest["excluded_front_matter_passages"] == 6, "NMF exclusions")
    check(manifest["topic_model_passages"] == 269, "NMF modeled passages")
    check(manifest["topic_model_original_word_count"] == 50303, "NMF words")
    primary = manifest["primary_solution"]
    check((primary["k"], primary["initialisation"], primary["random_state"]) == (7, "nndsvda", 0), "primary NMF settings")
    check((primary["max_iter"], primary["tol"]) == (1500, 1e-5), "primary NMF convergence settings")
    check(manifest["seeds"] == [1, 21, 42, 84, 100], "sensitivity seeds")
    check(np.load(TECH / "nmf_primary_components_k7.npy").shape == (7, 4000), "NMF component shape")
    check([int(row["topic_id"]) for row in assignments] == [3, 4, 1, 2, 6], "retained topic assignment")

    check(workplaces[-1] == {"year": "Total", "enforcement_records": "24", "unique_addresses": "23", "workshop_records": "20", "bakehouse_records": "4"}, "workplace totals")
    check(len(spatial) == 38, "raw spatial candidates")
    check(len(points) == 15 and len(outside) == 1, "mapped and out-of-sheet places")
    check(outside[0]["place"] == "Mile End Old Town", "out-of-sheet identity")
    check(Counter({row["validation_status"]: int(row["place_passage_pairs"]) for row in validation}) == Counter({"false_structural_adjacency": 9, "direct_place_institution_disease": 2, "management_context_only": 1}), "validation distribution")

    required_ids = {"1890_0018", "1893_0092", "1895_0009", "1897_0054", "1897_0055", "1897_0056", "1892_0026", "1890_0024", "1898_0008", "1894_0059", "1895_0014"}
    current_ids = {row["passage_id"] for row in passages}
    check(required_ids <= current_ids, "all cited passage IDs must resolve")

    expected_figures = {
        "figure_01_corpus_workflow.png", "figure_02_theme_distribution.png",
        "figure_03_by_year_heatmap.png", "figure_04_nmf_primary_topics_by_year.png",
        "figure_05_workplace_enforcement_map.png", "figure_05_workplace_enforcement_map.pdf",
        "figure_06_spatial_disease_validation.png", "figure_07_source_validated_places_map.png",
        "figure_07_source_validated_places_map.pdf",
    }
    actual_figures = {path.name for path in (ROOT / "outputs" / "figures").iterdir() if path.is_file()}
    check(actual_figures == expected_figures, "final figure allow-list")

    forbidden = ["/" + "Users" + "/", "/private/" + "tmp/", "Desk" + "top/", "JiangJie_" + "CASA0010_" + "Dissertation"]
    text_suffixes = {".py", ".md", ".txt", ".csv", ".json"}
    active_roots = [ROOT / "scripts", ROOT / "tests", ROOT / "data", ROOT / "maps", ROOT / "analysis", ROOT.parent / "references"]
    active_files = [ROOT / "run_all.py", ROOT / "README.md", ROOT / "RUN_ORDER.md", ROOT / "environment.txt", ROOT / "requirements-lock.txt", ROOT.parent / "README.md", ROOT.parent / "RIGHTS_AND_LICENSING.md"]
    scan_paths = active_files + [path for base in active_roots for path in base.rglob("*")]
    for path in scan_paths:
        if path.is_file() and path.suffix.lower() in text_suffixes:
            text = path.read_text(encoding="utf-8", errors="ignore")
            check(not any(token in text for token in forbidden), f"private path or dissertation reference: {path}")
    debris = [
        path
        for path in ROOT.parent.rglob("*")
        if ".venv" not in path.parts
        and (
            path.name == ".DS_Store"
            or path.name.startswith("._")
            or "__MACOSX" in path.parts
            or "__pycache__" in path.parts
            or ".ipynb_checkpoints" in path.parts
            or ".pytest_cache" in path.parts
            or path.suffix == ".pyc"
        )
    ]
    check(not debris, f"packaging debris present: {debris[:3]}")

    print("public release regression checks: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
