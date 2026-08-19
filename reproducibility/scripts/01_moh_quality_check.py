"""
Quality check and corpus table builder for downloaded Whitechapel MOH reports.

This script uses only files already present in data/raw/moh/.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOH_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "moh"
METADATA_PATH = PROJECT_ROOT / "data" / "metadata" / "moh_reports_metadata.csv"
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"

CHECK_TERMS = [
    "sanitary",
    "fever",
    "nuisance",
    "overcrowding",
    "lodging",
    "drainage",
    "sewer",
    "smallpox",
    "cholera",
]


def clean_text(text: str) -> str:
    """Normalize text enough for pilot counting while preserving meaning."""
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[\u2018\u2019]", "'", text)
    text = re.sub(r"[\u201c\u201d]", '"', text)
    text = re.sub(r"[^a-z0-9'\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def count_words(text: str) -> int:
    return len(re.findall(r"\b[a-zA-Z][a-zA-Z'-]*\b", text))


def count_term(text_clean: str, term: str) -> int:
    term_clean = clean_text(term)
    pattern = rf"(?<![a-z0-9]){re.escape(term_clean)}(?![a-z0-9])"
    return len(re.findall(pattern, text_clean, flags=re.IGNORECASE))


def report_id_from_filename(path: Path) -> str:
    match = re.search(r"_(b[0-9a-z]+)_fulltext\.txt$", path.name, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def year_from_filename(path: Path) -> int | None:
    match = re.search(r"Whitechapel_(\d{4})_", path.name)
    return int(match.group(1)) if match else None


def detect_ocr_noise(text: str) -> tuple[bool, str]:
    if not text:
        return False, ""

    replacement_count = text.count("\ufffd")
    question_runs = len(re.findall(r"\?{3,}", text))
    non_ascii = sum(1 for char in text if ord(char) > 127)
    non_ascii_ratio = non_ascii / max(len(text), 1)
    suspicious_cjk = len(re.findall(r"[\u3400-\u9fff]", text))
    broken_word_marks = len(re.findall(r"[A-Za-z][\u3400-\u9fff][A-Za-z]?", text))

    signals = []
    if replacement_count:
        signals.append(f"replacement_chars={replacement_count}")
    if question_runs:
        signals.append(f"question_mark_runs={question_runs}")
    if non_ascii_ratio > 0.002:
        signals.append(f"non_ascii_ratio={non_ascii_ratio:.4f}")
    if suspicious_cjk:
        signals.append(f"suspicious_cjk_chars={suspicious_cjk}")
    if broken_word_marks:
        signals.append(f"broken_word_marks={broken_word_marks}")

    return bool(signals), "; ".join(signals)


def load_metadata() -> pd.DataFrame:
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    metadata["report_year"] = pd.to_numeric(metadata["report_year"], errors="coerce").astype("Int64")
    return metadata


def main() -> None:
    OUTPUT_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    metadata = load_metadata()
    metadata_by_id = metadata.set_index("report_id", drop=False)

    quality_rows = []
    corpus_rows = []

    for path in sorted(MOH_RAW_DIR.glob("*_fulltext.txt")):
        text = path.read_text(encoding="utf-8", errors="replace")
        text_clean = clean_text(text)
        report_id = report_id_from_filename(path)
        meta = metadata_by_id.loc[report_id].to_dict() if report_id in metadata_by_id.index else {}
        report_year = meta.get("report_year") or year_from_filename(path)
        word_count = count_words(text)
        char_count = len(text)
        line_count = len(text.splitlines())
        appears_empty = char_count == 0 or word_count < 20
        ocr_noise_present, ocr_noise_notes = detect_ocr_noise(text)

        quality_row = {
            "file_name": path.name,
            "report_id": report_id,
            "report_year": int(report_year) if pd.notna(report_year) else "",
            "character_count": char_count,
            "word_count": word_count,
            "number_of_lines": line_count,
            "appears_empty": appears_empty,
            "ocr_noise_present": ocr_noise_present,
            "ocr_noise_notes": ocr_noise_notes,
        }
        for term in CHECK_TERMS:
            quality_row[f"term_{term}"] = count_term(text_clean, term)
        quality_rows.append(quality_row)

        corpus_rows.append(
            {
                "report_id": report_id,
                "district": meta.get("district", ""),
                "report_year": int(report_year) if pd.notna(report_year) else "",
                "published_year": meta.get("published_year", ""),
                "source": "Wellcome/London's Pulse",
                "url": meta.get("url", ""),
                "text": text,
                "text_clean": text_clean,
                "word_count": word_count,
            }
        )

    quality = pd.DataFrame(quality_rows).sort_values("report_year")
    corpus = pd.DataFrame(corpus_rows).sort_values("report_year")

    quality.to_csv(OUTPUT_TABLES_DIR / "moh_quality_check.csv", index=False)
    corpus.to_csv(OUTPUT_TABLES_DIR / "moh_corpus_clean.csv", index=False)

    print(f"Wrote {len(quality)} quality rows.")
    print(f"Wrote {len(corpus)} corpus rows.")


if __name__ == "__main__":
    main()
