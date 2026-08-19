#!/usr/bin/env python3
"""Run the 21 public analytical stages and write a stage-by-stage audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
AUDIT = ROOT / "audit"
LOG_DIR = AUDIT / "logs"
RERUN_DIR = AUDIT / "rerun"
HASH_DIR = AUDIT / "hashes"
LOG = LOG_DIR / "full_clean_rerun.log"
STATUS = RERUN_DIR / "full_clean_rerun_status.json"
FINAL_FIGURE_NAMES = {
    "figure_01_corpus_workflow.png",
    "figure_02_theme_distribution.png",
    "figure_03_by_year_heatmap.png",
    "figure_04_nmf_primary_topics_by_year.png",
    "figure_05_workplace_enforcement_map.png",
    "figure_05_workplace_enforcement_map.pdf",
    "figure_06_spatial_disease_validation.png",
    "figure_07_source_validated_places_map.png",
    "figure_07_source_validated_places_map.pdf",
}

STAGES = [
    ("01_corpus_preparation", "scripts/01_moh_quality_check.py"),
    ("02_dictionary_keyword_retrieval", "scripts/02_moh_keyword_counts.py"),
    ("03_place_retrieval", "scripts/03_moh_place_matching.py"),
    ("04_place_term_cooccurrence", "scripts/04_moh_place_term_cooccurrence.py"),
    ("05_basic_diagnostic_figures", "scripts/05_moh_basic_figures.py"),
    ("06_cooccurrence_contexts", "scripts/06_moh_cooccurrence_contexts.py"),
    ("07_narrative_filtering", "scripts/07_moh_narrative_extraction.py"),
    ("08_narrative_keyword_retrieval", "scripts/08_moh_narrative_keyword_analysis.py"),
    ("09_close_reading_candidates", "scripts/09_moh_close_reading_candidates.py"),
    ("10_spatial_reference_candidates", "scripts/10_moh_spatial_reference_candidates.py"),
    ("11_figure_1", "scripts/00_corpus_workflow_figure.py"),
    ("12_figures_2_and_3", "scripts/11_moh_chapter3_figures.py"),
    ("13_dictionary_appendix", "scripts/12_moh_keyword_dictionary_appendix.py"),
    ("14_nmf_primary_and_seed_sensitivity", "scripts/13_moh_topic_model_sensitivity.py"),
    ("15_lda_sensitivity", "scripts/14_moh_lda_sensitivity.py"),
    ("16_lexical_normalisation_audit", "scripts/15_moh_lexical_normalisation_audit.py"),
    ("17_spatial_disease_validation", "scripts/16_moh_spatial_disease_validation.py"),
    ("18_primary_nmf_figure_4_and_spatial_figure_6", "scripts/17_moh_technical_figures.py"),
    ("19_inequality_sensitivity", "scripts/18_moh_inequality_marker_sensitivity.py"),
    ("20_workplace_address_extraction", "scripts/19_moh_workplace_address_extraction.py"),
    ("21_figures_5_and_7_maps", "scripts/20_whitechapel_maps.py"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def final_files() -> list[Path]:
    included_roots = [
        ROOT / "data", ROOT / "maps", ROOT / "scripts", ROOT / "notebooks",
        ROOT / "outputs", ROOT / "analysis", AUDIT,
    ]
    included_files = [
        ROOT / "README.md", ROOT / "RUN_ORDER.md", ROOT / "requirements-lock.txt",
        ROOT / "environment.txt", ROOT / ".python-version", ROOT / "run_all.py",
    ]
    files = [path for path in included_files if path.is_file()]
    for base in included_roots:
        if base.exists():
            files.extend(path for path in base.rglob("*") if path.is_file())
    return sorted({
        path for path in files
        if "__pycache__" not in path.parts
        and ".ipynb_checkpoints" not in path.parts
        and path.name != ".DS_Store"
        and path.name not in {"final_file_hashes.csv", "hash_verification.csv"}
        and HASH_DIR not in path.parents
        and (AUDIT / "cache") not in path.parents
        and (AUDIT / "matplotlib") not in path.parents
    })


def write_and_verify_hash_manifest() -> tuple[int, int]:
    HASH_DIR.mkdir(parents=True, exist_ok=True)
    manifest = HASH_DIR / "final_file_hashes.csv"
    records = [(path.relative_to(ROOT).as_posix(), sha256(path)) for path in final_files()]
    manifest.write_text(
        "path,sha256\n" + "".join(f'"{relative}",{digest}\n' for relative, digest in records),
        encoding="utf-8",
    )

    verification = HASH_DIR / "hash_verification.csv"
    mismatches = 0
    rows = ["path,expected_sha256,actual_sha256,match"]
    for relative, expected in records:
        actual = sha256(ROOT / relative)
        match = expected == actual
        mismatches += int(not match)
        rows.append(f"{relative},{expected},{actual},{str(match).lower()}")
    verification.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return len(records), mismatches


def snapshot_generated_files() -> dict[str, tuple[int, int]]:
    paths = []
    for base in (OUTPUTS, RERUN_DIR):
        if base.exists():
            paths.extend(path for path in base.rglob("*") if path.is_file())
    return {
        path.relative_to(ROOT).as_posix(): (path.stat().st_mtime_ns, path.stat().st_size)
        for path in paths if path != STATUS
    }


def cleanup_generated_debris() -> None:
    """Enforce the explicit submission allow-list, including on failed runs."""
    figure_dir = OUTPUTS / "figures"
    if figure_dir.exists():
        for path in figure_dir.iterdir():
            if path.is_file() and path.name not in FINAL_FIGURE_NAMES:
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
    for cache_dir in (AUDIT / "cache", AUDIT / "matplotlib"):
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
    for bytecode_dir in sorted(ROOT.rglob("__pycache__"), reverse=True):
        if bytecode_dir.is_dir():
            shutil.rmtree(bytecode_dir)
    for bytecode_file in ROOT.rglob("*.pyc"):
        bytecode_file.unlink()


def run_pipeline(args: argparse.Namespace) -> int:

    if args.hash_only:
        count, mismatches = write_and_verify_hash_manifest()
        print(json.dumps({"hashed_files": count, "mismatches": mismatches}, indent=2))
        return 1 if mismatches else 0

    if args.clean and OUTPUTS.exists():
        resolved = OUTPUTS.resolve()
        if resolved.parent != ROOT.resolve() or resolved.name != "outputs":
            raise RuntimeError(f"Refusing to clean unexpected path: {resolved}")
        shutil.rmtree(resolved)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RERUN_DIR.mkdir(parents=True, exist_ok=True)
    HASH_DIR.mkdir(parents=True, exist_ok=True)

    started = datetime.now(timezone.utc).isoformat()
    status = {
        "started_utc": started,
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "clean_start": bool(args.clean),
        "stages": [],
    }
    with LOG.open("w", encoding="utf-8") as log:
        log.write(f"Whitechapel full rerun\nstarted_utc={started}\npython={sys.version}\n\n")
        for name, relative_script in STAGES:
            script = ROOT / relative_script
            stage_started = datetime.now(timezone.utc)
            before = snapshot_generated_files()
            process_env = os.environ.copy()
            process_env["MPLCONFIGDIR"] = str(AUDIT / "matplotlib")
            process_env["XDG_CACHE_HOME"] = str(AUDIT / "cache")
            process_env["PYTHONDONTWRITEBYTECODE"] = "1"
            Path(process_env["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
            Path(process_env["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                [sys.executable, str(script)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=process_env,
            )
            stage_finished = datetime.now(timezone.utc)
            after = snapshot_generated_files()
            changed_outputs = sorted(
                relative for relative, signature in after.items()
                if before.get(relative) != signature
            )
            diagnostic_lines = [
                line for line in result.stdout.splitlines()
                if any(token in line.casefold() for token in ("warning", "error", "traceback"))
            ]
            record = {
                "stage": name,
                "script": relative_script,
                "started_utc": stage_started.isoformat(),
                "finished_utc": stage_finished.isoformat(),
                "duration_seconds": round((stage_finished - stage_started).total_seconds(), 3),
                "status": "success" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "output_files": changed_outputs,
                "warnings_or_errors": diagnostic_lines,
            }
            status["stages"].append(record)
            section = f"[{record['status'].upper()}] {name} ({relative_script})\n{result.stdout}\n"
            print(section, end="")
            log.write(section)
            log.flush()
            STATUS.write_text(json.dumps(status, indent=2), encoding="utf-8")
            if result.returncode:
                status["completed_utc"] = datetime.now(timezone.utc).isoformat()
                status["overall_status"] = "failed"
                STATUS.write_text(json.dumps(status, indent=2), encoding="utf-8")
                return result.returncode

    # Earlier diagnostic stages intentionally create five pilot plots. Remove
    # them before enforcing the documented nine-file public figure allow-list.
    cleanup_generated_debris()
    status["completed_utc"] = datetime.now(timezone.utc).isoformat()
    status["overall_status"] = "success"
    figure_dir = OUTPUTS / "figures"
    actual_final_figures = {path.name for path in figure_dir.iterdir() if path.is_file()}
    if actual_final_figures != FINAL_FIGURE_NAMES:
        missing = sorted(FINAL_FIGURE_NAMES - actual_final_figures)
        unexpected = sorted(actual_final_figures - FINAL_FIGURE_NAMES)
        raise RuntimeError(f"Final figure set mismatch; missing={missing}; unexpected={unexpected}")
    STATUS.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps({
        "overall_status": status["overall_status"],
        "successful_stages": len(status["stages"]),
        "failed_stages": 0,
        "workflow": "public analytical reproducibility stages 1-21",
        "return_code": 0,
    }, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="remove prior generated outputs before running")
    parser.add_argument("--hash-only", action="store_true", help="regenerate and verify final hash manifests only")
    args = parser.parse_args()
    try:
        return run_pipeline(args)
    finally:
        cleanup_generated_debris()


if __name__ == "__main__":
    raise SystemExit(main())
