"""
Identify likely narrative prose passages in the Whitechapel MOH corpus.

This script uses the existing `moh_corpus_clean.csv` output and does not collect
new data. The heuristics are intentionally conservative because previous pilot
work showed that tables can inflate term and place co-occurrence counts.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
CORPUS_PATH = OUTPUT_TABLES_DIR / "moh_corpus_clean.csv"
OUTPUT_PATH = OUTPUT_TABLES_DIR / "moh_narrative_passages.csv"
OVERRIDES_PATH = PROJECT_ROOT / "data" / "metadata" / "narrative_classification_overrides.csv"

MIN_PASSAGE_WORDS = 55
TARGET_PASSAGE_WORDS = 170
MAX_PASSAGE_WORDS = 260

KEY_TERMS = [
    "sanitary",
    "sanitation",
    "fever",
    "scarlet fever",
    "diphtheria",
    "cholera",
    "smallpox",
    "measles",
    "typhus",
    "typhoid",
    "nuisance",
    "nuisances",
    "overcrowding",
    "overcrowded",
    "lodging house",
    "common lodging house",
    "drainage",
    "drain",
    "drains",
    "water supply",
    "inspector",
    "inspectors",
    "sanitary authority",
    "medical officer",
    "board",
    "vestry",
    "dwellings",
    "houses",
]

TABLE_SIGNAL_WORDS = {
    "table",
    "total",
    "totals",
    "rate",
    "rates",
    "deaths",
    "death",
    "cases",
    "case",
    "registered",
    "quarter",
    "quarters",
    "number",
    "numbers",
    "columns",
    "classification",
    "appendix",
}

COLUMN_SIGNAL_WORDS = {
    "year",
    "street",
    "district",
    "sub",
    "age",
    "ages",
    "males",
    "females",
    "persons",
    "cause",
    "causes",
    "name",
    "place",
    "total",
}


def word_tokens(text: str) -> list[str]:
    return re.findall(r"\b[a-zA-Z][a-zA-Z'-]*\b", text)


def clean_for_matching(text: str) -> str:
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9'\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def term_present(text_clean: str, term: str) -> bool:
    term_clean = clean_for_matching(term)
    pattern = rf"(?<![a-z0-9]){re.escape(term_clean)}(?![a-z0-9])"
    return bool(re.search(pattern, text_clean))


def split_sentence_like_units(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    # Add extra breaks before frequent table headings so table blocks can be
    # classified as their own passages instead of contaminating nearby prose.
    text = re.sub(r"\b(TABLE\s+[A-Z0-9]+\.?)", r"||BREAK||\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(APPENDIX|REGISTERED COMMON LODGING HOUSES|MODEL DWELLINGS)\b", r"||BREAK||\1", text, flags=re.IGNORECASE)

    rough_units: list[str] = []
    for block in text.split("||BREAK||"):
        block = block.strip()
        if not block:
            continue
        pieces = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", block)
        rough_units.extend(piece.strip() for piece in pieces if piece.strip())
    return rough_units


def build_passages(text: str) -> list[str]:
    passages: list[str] = []
    current: list[str] = []
    current_words = 0

    for unit in split_sentence_like_units(text):
        unit_words = len(word_tokens(unit))
        if unit_words > MAX_PASSAGE_WORDS:
            words = unit.split()
            for start in range(0, len(words), TARGET_PASSAGE_WORDS):
                chunk = " ".join(words[start : start + TARGET_PASSAGE_WORDS]).strip()
                if chunk:
                    passages.append(chunk)
            current = []
            current_words = 0
            continue

        if current and current_words + unit_words > MAX_PASSAGE_WORDS:
            passages.append(" ".join(current).strip())
            current = []
            current_words = 0

        current.append(unit)
        current_words += unit_words

        if current_words >= TARGET_PASSAGE_WORDS:
            passages.append(" ".join(current).strip())
            current = []
            current_words = 0

    if current:
        passages.append(" ".join(current).strip())

    return [passage for passage in passages if len(word_tokens(passage)) >= MIN_PASSAGE_WORDS]


def classify_passage(passage: str) -> tuple[bool, bool, str]:
    words = word_tokens(passage)
    word_count = len(words)
    text_clean = clean_for_matching(passage)
    clean_tokens = text_clean.split()
    number_count = len(re.findall(r"\b\d+(?:[.,]\d+)?\b", passage))
    numeric_density = number_count / max(word_count, 1)
    punctuation_count = len(re.findall(r"[.!?;:]", passage))
    sentence_mark_density = punctuation_count / max(word_count, 1)
    table_signal_count = sum(clean_tokens.count(word) for word in TABLE_SIGNAL_WORDS)
    repeated_column_words = [word for word in COLUMN_SIGNAL_WORDS if clean_tokens.count(word) >= 3]
    short_token_ratio = sum(1 for token in clean_tokens if len(token) <= 2) / max(len(clean_tokens), 1)

    table_reasons = []
    if numeric_density >= 0.10 or number_count >= 18:
        table_reasons.append(f"dense_numbers={number_count}")
    if table_signal_count >= 8:
        table_reasons.append(f"table_signal_words={table_signal_count}")
    if len(repeated_column_words) >= 2:
        table_reasons.append("repeated_headings=" + "|".join(sorted(repeated_column_words)))
    if short_token_ratio >= 0.34:
        table_reasons.append(f"fragmented_short_tokens={short_token_ratio:.2f}")
    if re.search(r"\b(table|total|totals)\b", text_clean) and number_count >= 8:
        table_reasons.append("explicit_table_or_total_with_numbers")

    prose_reasons = []
    if word_count >= 80:
        prose_reasons.append("substantial_length")
    if sentence_mark_density >= 0.012:
        prose_reasons.append("sentence_punctuation")
    if numeric_density < 0.06:
        prose_reasons.append("low_numeric_density")
    if table_signal_count < 8:
        prose_reasons.append("limited_table_signal_words")

    likely_table = bool(table_reasons)
    likely_narrative = len(prose_reasons) >= 3 and not likely_table
    notes = "Narrative signals: " + ", ".join(prose_reasons)
    if table_reasons:
        notes += " | Table signals: " + ", ".join(table_reasons)
    return likely_narrative, likely_table, notes


def matched_terms(passage: str) -> str:
    text_clean = clean_for_matching(passage)
    found = [term for term in KEY_TERMS if term_present(text_clean, term)]
    return "; ".join(found)


def parse_bool(value: object) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"Cannot parse Boolean override value: {value!r}")


def apply_manual_overrides(output: pd.DataFrame) -> pd.DataFrame:
    if not OVERRIDES_PATH.exists():
        raise FileNotFoundError(f"Required manual override file is missing: {OVERRIDES_PATH}")

    overrides = pd.read_csv(OVERRIDES_PATH)
    required = {"passage_id", "likely_narrative", "likely_table_context", "reason"}
    missing = required - set(overrides.columns)
    if missing:
        raise ValueError(f"Override file is missing columns: {', '.join(sorted(missing))}")
    if overrides["passage_id"].duplicated().any():
        duplicates = overrides.loc[overrides["passage_id"].duplicated(), "passage_id"].tolist()
        raise ValueError(f"Duplicate passage IDs in override file: {duplicates}")

    passage_ids = set(output["passage_id"])
    missing_ids = sorted(set(overrides["passage_id"]) - passage_ids)
    if missing_ids:
        raise ValueError(f"Override passage IDs not found in generated output: {missing_ids}")

    for row in overrides.itertuples(index=False):
        mask = output["passage_id"] == row.passage_id
        output.loc[mask, "likely_narrative"] = parse_bool(row.likely_narrative)
        output.loc[mask, "likely_table_context"] = parse_bool(row.likely_table_context)
        reason = str(row.reason).strip()
        output.loc[mask, "notes"] = output.loc[mask, "notes"].astype(str) + f" | Manual override: {reason}"

    print(f"Manual classification overrides applied: {len(overrides)}")
    return output


def main() -> None:
    corpus = pd.read_csv(CORPUS_PATH)
    rows = []

    for doc in corpus.sort_values("report_year").itertuples():
        passages = build_passages(str(doc.text))
        for index, passage in enumerate(passages, start=1):
            word_count = len(word_tokens(passage))
            likely_narrative, likely_table, notes = classify_passage(passage)
            rows.append(
                {
                    "report_year": int(doc.report_year),
                    "passage_id": f"{int(doc.report_year)}_{index:04d}",
                    "passage_text": passage,
                    "word_count": word_count,
                    "likely_narrative": likely_narrative,
                    "likely_table_context": likely_table,
                    "matched_terms": matched_terms(passage),
                    "notes": notes,
                }
            )

    output = pd.DataFrame(
        rows,
        columns=[
            "report_year",
            "passage_id",
            "passage_text",
            "word_count",
            "likely_narrative",
            "likely_table_context",
            "matched_terms",
            "notes",
        ],
    )
    output = apply_manual_overrides(output)
    output.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(output)} passages.")
    print(f"Likely narrative passages: {int(output['likely_narrative'].sum())}")
    print(f"Likely table-context passages: {int(output['likely_table_context'].sum())}")


if __name__ == "__main__":
    main()
