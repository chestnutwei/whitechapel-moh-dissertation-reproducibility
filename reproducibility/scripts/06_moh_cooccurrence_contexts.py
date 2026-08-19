"""
Extract context snippets for the top MOH place-term co-occurrence pairs.

This validation step uses only existing project outputs. It does not collect data.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
CORPUS_PATH = OUTPUT_TABLES_DIR / "moh_corpus_clean.csv"
TOP_PAIRS_PATH = OUTPUT_TABLES_DIR / "moh_top_place_term_pairs.csv"
OUTPUT_PATH = OUTPUT_TABLES_DIR / "moh_top_place_term_pairs_contexts.csv"

TOP_PAIR_LIMIT = 30
SNIPPETS_PER_PAIR = 5
CONTEXT_WORDS = 80

TABLE_WORDS = {"table", "total", "rate", "deaths", "death", "cases", "case"}
REPEATED_COLUMN_WORDS = {
    "year",
    "quarter",
    "district",
    "sub",
    "place",
    "name",
    "street",
    "age",
    "cause",
    "causes",
}


def normalize(value: str) -> str:
    value = str(value).lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9'\s-]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b[a-z0-9']+\b", normalize(text))


def phrase_positions(tokens: list[str], phrase: str) -> list[int]:
    phrase_tokens = tokenize(phrase)
    if not phrase_tokens:
        return []
    width = len(phrase_tokens)
    return [
        index
        for index in range(0, len(tokens) - width + 1)
        if tokens[index : index + width] == phrase_tokens
    ]


def snippet_from_tokens(tokens: list[str], place_pos: int, term_pos: int) -> str:
    focus_start = min(place_pos, term_pos)
    focus_end = max(place_pos, term_pos)
    start = max(0, focus_start - CONTEXT_WORDS)
    end = min(len(tokens), focus_end + CONTEXT_WORDS + 1)
    return " ".join(tokens[start:end])


def likely_table_context(snippet: str) -> tuple[bool, str]:
    tokens = tokenize(snippet)
    if not tokens:
        return False, "empty snippet"

    number_count = len(re.findall(r"\b\d+\b", snippet))
    table_word_counts = {word: tokens.count(word) for word in TABLE_WORDS}
    table_word_hits = sum(table_word_counts.values())
    repeated_columns = [word for word in REPEATED_COLUMN_WORDS if tokens.count(word) >= 2]

    short_tokens = sum(1 for token in tokens if len(token) <= 2)
    short_ratio = short_tokens / len(tokens)
    fragmented = len(tokens) < 45 or short_ratio > 0.32

    reasons = []
    if number_count >= 8:
        reasons.append(f"many_numbers={number_count}")
    if table_word_hits >= 5:
        reasons.append(f"repeated_table_words={table_word_hits}")
    if repeated_columns:
        reasons.append("repeated_columns=" + "|".join(sorted(repeated_columns)))
    if fragmented:
        reasons.append(f"fragmented_or_short={len(tokens)}_tokens")

    return bool(reasons), "; ".join(reasons) if reasons else "prose-like by simple heuristics"


def classify_notes(snippet: str, table_flag: bool, table_notes: str) -> str:
    tokens = tokenize(snippet)
    if table_flag:
        return f"Likely table/statistical context: {table_notes}"
    if len(tokens) < 70:
        return "Short context; manual checking recommended."
    return "Appears more prose-like by simple heuristics; still check manually before interpretation."


def main() -> None:
    corpus = pd.read_csv(CORPUS_PATH)
    top_pairs = (
        pd.read_csv(TOP_PAIRS_PATH)
        .sort_values(
            ["cooccurrence_count", "standard_name", "term"],
            ascending=[False, True, True],
        )
        .head(TOP_PAIR_LIMIT)
    )

    corpus_tokens = {
        int(row.report_year): tokenize(row.text_clean)
        for row in corpus.itertuples()
    }

    rows = []
    for pair in top_pairs.itertuples():
        pair_rows = []
        place_phrase = pair.standard_name
        term_phrase = pair.term

        for report_year, tokens in sorted(corpus_tokens.items()):
            place_positions = phrase_positions(tokens, place_phrase)
            term_positions = phrase_positions(tokens, term_phrase)
            if not place_positions or not term_positions:
                continue

            seen_snippets = set()
            for place_pos in place_positions:
                for term_pos in term_positions:
                    if abs(place_pos - term_pos) > 50:
                        continue
                    snippet = snippet_from_tokens(tokens, place_pos, term_pos)
                    if snippet in seen_snippets:
                        continue
                    seen_snippets.add(snippet)
                    table_flag, table_notes = likely_table_context(snippet)
                    pair_rows.append(
                        {
                            "standard_name": pair.standard_name,
                            "term": pair.term,
                            "category": pair.category,
                            "report_year": report_year,
                            "snippet": snippet,
                            "likely_table_context": table_flag,
                            "notes": classify_notes(snippet, table_flag, table_notes),
                        }
                    )
                    if len(pair_rows) >= SNIPPETS_PER_PAIR:
                        break
                if len(pair_rows) >= SNIPPETS_PER_PAIR:
                    break
            if len(pair_rows) >= SNIPPETS_PER_PAIR:
                break

        rows.extend(pair_rows)

    contexts = pd.DataFrame(
        rows,
        columns=["standard_name", "term", "category", "report_year", "snippet", "likely_table_context", "notes"],
    )
    contexts.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(contexts)} context snippets for {len(top_pairs)} top pairs.")


if __name__ == "__main__":
    main()
