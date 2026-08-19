"""
Create simple pilot figures from MOH quality, keyword, place, and co-occurrence outputs.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"


def save_bar(x, y, title, xlabel, ylabel, path, *, rotation=0, color="#3f6f8f"):
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x, y, color=color)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=rotation)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def word_counts_by_year():
    quality = pd.read_csv(OUTPUT_TABLES_DIR / "moh_quality_check.csv")
    quality = quality.sort_values("report_year")
    save_bar(
        quality["report_year"].astype(str),
        quality["word_count"],
        "MOH Word Counts by Report Year",
        "Report year",
        "Words",
        FIGURES_DIR / "moh_word_counts_by_year.png",
        color="#4b7f52",
    )


def top_keywords():
    summary = pd.read_csv(OUTPUT_TABLES_DIR / "moh_keyword_counts_summary.csv")
    top = summary.sort_values("raw_count", ascending=False).head(20).sort_values("raw_count")
    labels = [f"{row.term} ({row.category})" for row in top.itertuples()]

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(labels, top["raw_count"], color="#7b5e8e")
    ax.set_title("Top Controlled Keywords in Whitechapel MOH Reports")
    ax.set_xlabel("Raw count")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "moh_top_keywords.png", dpi=200)
    plt.close(fig)


def keyword_categories_by_year():
    by_year = pd.read_csv(OUTPUT_TABLES_DIR / "moh_keyword_counts_by_year.csv")
    category_year = (
        by_year.groupby(["report_year", "category"], as_index=False)["frequency_per_10000_words"]
        .sum()
        .pivot(index="report_year", columns="category", values="frequency_per_10000_words")
        .fillna(0)
        .sort_index()
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    for category in category_year.columns:
        ax.plot(category_year.index.astype(str), category_year[category], marker="o", label=category)
    ax.set_title("Keyword Category Frequencies by Report Year")
    ax.set_xlabel("Report year")
    ax.set_ylabel("Frequency per 10,000 words")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "moh_keyword_categories_by_year.png", dpi=200)
    plt.close(fig)


def top_place_mentions():
    summary = pd.read_csv(OUTPUT_TABLES_DIR / "moh_place_mentions_summary.csv")
    top = summary[summary["total_mentions"] > 0].sort_values("total_mentions", ascending=False).head(15)
    if top.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No gazetteer place mentions found", ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(FIGURES_DIR / "moh_top_place_mentions.png", dpi=200)
        plt.close(fig)
        return

    top = top.sort_values("total_mentions")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top["standard_name"], top["total_mentions"], color="#9a6b3f")
    ax.set_title("Top Gazetteer Place Mentions")
    ax.set_xlabel("Mentions")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "moh_top_place_mentions.png", dpi=200)
    plt.close(fig)


def place_term_heatmap():
    pairs = pd.read_csv(OUTPUT_TABLES_DIR / "moh_top_place_term_pairs.csv")
    pairs = pairs[pairs["cooccurrence_count"] > 0]
    if len(pairs) < 3:
        return

    top_places = (
        pairs.groupby("standard_name")["cooccurrence_count"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .index
    )
    top_terms = (
        pairs.groupby("term")["cooccurrence_count"]
        .sum()
        .sort_values(ascending=False)
        .head(12)
        .index
    )
    matrix = (
        pairs[pairs["standard_name"].isin(top_places) & pairs["term"].isin(top_terms)]
        .pivot_table(index="standard_name", columns="term", values="cooccurrence_count", aggfunc="sum", fill_value=0)
        .reindex(index=top_places, columns=top_terms)
        .fillna(0)
    )
    if matrix.empty or np.count_nonzero(matrix.to_numpy()) < 3:
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    image = ax.imshow(matrix.to_numpy(), aspect="auto", cmap="YlGnBu")
    ax.set_title("Place-Term Co-occurrence Heatmap")
    ax.set_xticks(np.arange(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns, rotation=45, ha="right")
    ax.set_yticks(np.arange(len(matrix.index)))
    ax.set_yticklabels(matrix.index)
    fig.colorbar(image, ax=ax, label="Co-occurrences")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "moh_place_term_heatmap.png", dpi=200)
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    word_counts_by_year()
    top_keywords()
    keyword_categories_by_year()
    top_place_mentions()
    place_term_heatmap()
    print("Wrote basic MOH pilot figures.")


if __name__ == "__main__":
    main()
