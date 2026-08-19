"""Generate Figure 1 and its data directly from the corpus-preparation output."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
CHAPTER3 = TABLES / "chapter3"
FIGURES = ROOT / "outputs" / "figures"


def main() -> None:
    passages = pd.read_csv(TABLES / "moh_narrative_passages.csv")
    reports = pd.read_csv(ROOT / "data" / "metadata" / "moh_reports_metadata.csv")
    narrative = passages[passages["likely_narrative"].astype(str).str.casefold() == "true"]
    table_context = passages[passages["likely_narrative"].astype(str).str.casefold() != "true"]

    rows = [
        {"metric": "Reports", "value": int(len(reports)), "figure_use": "bar"},
        {"metric": "Total passages", "value": int(len(passages)), "figure_use": "bar"},
        {"metric": "Narrative passages", "value": int(len(narrative)), "figure_use": "bar"},
        {"metric": "Table-context passages", "value": int(len(table_context)), "figure_use": "bar"},
        {"metric": "Narrative subset words", "value": int(narrative["word_count"].sum()), "figure_use": "subtitle"},
    ]
    data = pd.DataFrame(rows)
    CHAPTER3.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    data.to_csv(CHAPTER3 / "fig1_corpus_workflow_data.csv", index=False)

    chart_order = ["Reports", "Narrative passages", "Table-context passages", "Total passages"]
    chart = data.set_index("metric").loc[chart_order]
    words = int(data.loc[data["metric"] == "Narrative subset words", "value"].iloc[0])
    plt.style.use("seaborn-v0_8-whitegrid")
    figure, axis = plt.subplots(figsize=(9, 5.2), dpi=300)
    bars = axis.barh(chart.index, chart["value"], color="#5f5f5f")
    axis.bar_label(bars, padding=2, fontsize=10)
    axis.set_xlabel("Count", fontsize=11)
    axis.set_xlim(0, max(chart["value"]) * 1.05)
    axis.set_title(
        f"Figure 1. Corpus workflow summary\nNarrative subset = {words:,} words",
        loc="left", fontsize=14,
    )
    axis.spines[["top", "right", "left", "bottom"]].set_visible(False)
    figure.tight_layout()
    figure.savefig(FIGURES / "figure_01_corpus_workflow.png", dpi=300, facecolor="white")
    plt.close(figure)
    print(f"Wrote Figure 1 from {len(reports)} reports and {len(passages)} passages.")


if __name__ == "__main__":
    main()
