from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from portable_fonts import load_pillow_font

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"
CHAPTER3_TABLES_DIR = TABLES_DIR / "chapter3"

CANDIDATES_PATH = TABLES_DIR / "moh_close_reading_candidates.csv"
KEYWORD_COUNTS_PATH = TABLES_DIR / "moh_narrative_keyword_counts.csv"

FIG2_PATH = FIGURES_DIR / "figure_02_theme_distribution.png"
FIG3_PATH = FIGURES_DIR / "figure_03_by_year_heatmap.png"
FIG2_DATA_PATH = CHAPTER3_TABLES_DIR / "fig2_theme_distribution_data.csv"
FIG3_DATA_PATH = CHAPTER3_TABLES_DIR / "fig3_by_year_heatmap_data.csv"
MANIFEST_PATH = CHAPTER3_TABLES_DIR / "chapter3_figure_manifest.json"

CATEGORY_ORDER = ["disease", "governance", "housing", "inequality", "sanitary"]
DISPLAY_CATEGORY = {"sanitary": "sanitation"}
HEATMAP_DISPLAY_CATEGORY = {"sanitary": "sanitation", "inequality": "inequality\n(direct)"}
INDIRECT_INEQUALITY_TERMS = {"lodgers", "infirmary"}

def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return load_pillow_font(size, bold=bold)


def interpolate_colour(start: str, end: str, fraction: float) -> tuple[int, int, int]:
    fraction = max(0.0, min(1.0, fraction))
    start_rgb = tuple(int(start[index:index + 2], 16) for index in (1, 3, 5))
    end_rgb = tuple(int(end[index:index + 2], 16) for index in (1, 3, 5))
    return tuple(round(start_rgb[c] + (end_rgb[c] - start_rgb[c]) * fraction) for c in range(3))


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> float:
    left, _top, right, _bottom = draw.textbbox((0, 0), text, font=font)
    return right - left


def draw_figure_2(data: pd.DataFrame) -> None:
    width, height = 2000, 1250
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    label_font = load_font(52)
    tick_font = load_font(38)
    value_font = load_font(48, bold=True)
    axis_font = load_font(48)
    plot_left, plot_right = 360, 1770
    plot_top, plot_bottom = 90, 1030
    plot_width = plot_right - plot_left
    values = data["candidate_records"].tolist()
    maximum = max(values)
    axis_maximum = int(math.ceil((maximum * 1.12) / 50.0) * 50)

    for tick in range(0, axis_maximum + 1, 50):
        x = plot_left + (tick / axis_maximum) * plot_width
        draw.line((x, plot_top, x, plot_bottom), fill="#E2E7EC", width=3)
        label = str(tick)
        draw.text((x - text_width(draw, label, tick_font) / 2, plot_bottom + 24), label, font=tick_font, fill="#4C5561")

    bar_height = 125
    gap = (plot_bottom - plot_top - bar_height * len(data)) / (len(data) - 1)
    for index, row in data.reset_index(drop=True).iterrows():
        category = str(row["category"])
        value = int(row["candidate_records"])
        y0 = plot_top + index * (bar_height + gap)
        y1 = y0 + bar_height
        x1 = plot_left + (value / axis_maximum) * plot_width
        fill = "#2F6F9F" if category == "inequality" else "#66717D"
        draw.rounded_rectangle((plot_left, y0, x1, y1), radius=10, fill=fill)
        label = DISPLAY_CATEGORY.get(category, category)
        draw.text((plot_left - 28, (y0 + y1) / 2), label, font=label_font, fill="#38414A", anchor="rm")
        draw.text((x1 + 22, (y0 + y1) / 2), str(value), font=value_font, fill="#111827", anchor="lm")

    draw.text(((plot_left + plot_right) / 2, height - 62), "Number of candidate records", font=axis_font, fill="#111827", anchor="mm")
    image.save(FIG2_PATH, dpi=(300, 300), optimize=True)


def draw_vertical_axis_label(image: Image.Image, text: str, position: tuple[int, int], font: ImageFont.FreeTypeFont) -> None:
    scratch = Image.new("RGBA", (500, 100), (255, 255, 255, 0))
    scratch_draw = ImageDraw.Draw(scratch)
    scratch_draw.text((250, 50), text, font=font, fill="#111827", anchor="mm")
    rotated = scratch.rotate(90, expand=True)
    image.paste(rotated, (position[0] - rotated.width // 2, position[1] - rotated.height // 2), rotated)


def draw_figure_3(pivot: pd.DataFrame) -> None:
    width, height = 2200, 1600
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    year_font = load_font(42)
    category_font = load_font(42)
    value_font = load_font(38, bold=True)
    axis_font = load_font(48)
    legend_font = load_font(34)
    plot_left, plot_top = 300, 80
    cell_width, cell_height = 300, 125
    plot_right = plot_left + cell_width * len(CATEGORY_ORDER)
    plot_bottom = plot_top + cell_height * len(pivot.index)
    maximum = float(pivot.to_numpy().max())

    for row_index, year in enumerate(pivot.index):
        y0 = plot_top + row_index * cell_height
        y1 = y0 + cell_height
        draw.text((plot_left - 32, (y0 + y1) / 2), str(year), font=year_font, fill="#4C5561", anchor="rm")
        for column_index, category in enumerate(CATEGORY_ORDER):
            x0 = plot_left + column_index * cell_width
            x1 = x0 + cell_width
            value = float(pivot.loc[year, category])
            fraction = value / maximum if maximum else 0
            fill = interpolate_colour("#F3F7FB", "#438FC0", fraction)
            draw.rectangle((x0, y0, x1, y1), fill=fill, outline="white", width=5)
            luminance = 0.2126 * fill[0] + 0.7152 * fill[1] + 0.0722 * fill[2]
            text_fill = "white" if luminance < 140 else "#111827"
            draw.text(((x0 + x1) / 2, (y0 + y1) / 2), f"{value:.1f}", font=value_font, fill=text_fill, anchor="mm")

    for column_index, category in enumerate(CATEGORY_ORDER):
        x = plot_left + column_index * cell_width + cell_width / 2
        label = HEATMAP_DISPLAY_CATEGORY.get(category, category)
        draw.multiline_text((x, plot_bottom + 34), label, font=category_font, fill="#4C5561", anchor="ma", align="center", spacing=4)

    draw.text(((plot_left + plot_right) / 2, height - 72), "Category", font=axis_font, fill="#111827", anchor="mm")
    draw_vertical_axis_label(image, "Report year", (78, (plot_top + plot_bottom) // 2), axis_font)

    legend_left = plot_right + 100
    legend_top = plot_top + 360
    legend_width, legend_height = 62, 420
    draw.multiline_text((legend_left, legend_top - 100), "Hits per 10,000\nnarrative words", font=legend_font, fill="#111827", spacing=6)
    for offset in range(legend_height):
        fraction = 1 - offset / max(1, legend_height - 1)
        colour = interpolate_colour("#F3F7FB", "#438FC0", fraction)
        draw.line((legend_left, legend_top + offset, legend_left + legend_width, legend_top + offset), fill=colour, width=1)
    draw.rectangle((legend_left, legend_top, legend_left + legend_width, legend_top + legend_height), outline="#D3DAE2", width=2)
    ticks = [0, maximum / 4, maximum / 2, maximum * 3 / 4, maximum]
    for tick in ticks:
        y = legend_top + legend_height - (tick / maximum) * legend_height if maximum else legend_top + legend_height
        draw.line((legend_left + legend_width, y, legend_left + legend_width + 14, y), fill="#7B8490", width=2)
        draw.text((legend_left + legend_width + 25, y), f"{tick:.1f}", font=legend_font, fill="#111827", anchor="lm")

    image.save(FIG3_PATH, dpi=(300, 300), optimize=True)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    CHAPTER3_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    candidates = pd.read_csv(CANDIDATES_PATH)
    keyword_counts = pd.read_csv(KEYWORD_COUNTS_PATH)

    figure_2_data = (
        candidates.groupby("category").size().rename("candidate_records").reset_index().sort_values("candidate_records", ascending=False).reset_index(drop=True)
    )
    figure_2_data.to_csv(FIG2_DATA_PATH, index=False)

    # Figure 3 uses direct socioeconomic vocabulary only for the inequality column.
    # lodgers and infirmary remain in candidate retrieval (Figure 2) but are excluded
    # from descriptive inequality frequency because their meaning is context-dependent.
    figure3_counts = keyword_counts[~((keyword_counts["category"] == "inequality") & keyword_counts["term"].isin(INDIRECT_INEQUALITY_TERMS))].copy()
    grouped = figure3_counts.groupby(["report_year", "category"], as_index=False).agg(
        raw_count=("raw_count", "sum"),
        narrative_word_count=("narrative_word_count", "first"),
    )
    grouped["hits_per_10000_words"] = grouped["raw_count"] / grouped["narrative_word_count"] * 10000
    figure_3_data = grouped.sort_values(["report_year", "category"])
    figure_3_data.to_csv(FIG3_DATA_PATH, index=False)
    pivot = (
        figure_3_data.pivot(index="report_year", columns="category", values="hits_per_10000_words")
        .reindex(columns=CATEGORY_ORDER).fillna(0).sort_index(ascending=False)
    )

    draw_figure_2(figure_2_data)
    draw_figure_3(pivot)

    category_counts = {str(row.category): int(row.candidate_records) for row in figure_2_data.itertuples(index=False)}
    manifest = {
        "inputs": [str(CANDIDATES_PATH.relative_to(PROJECT_ROOT)), str(KEYWORD_COUNTS_PATH.relative_to(PROJECT_ROOT))],
        "outputs": [str(FIG2_PATH.relative_to(PROJECT_ROOT)), str(FIG3_PATH.relative_to(PROJECT_ROOT)), str(FIG2_DATA_PATH.relative_to(PROJECT_ROOT)), str(FIG3_DATA_PATH.relative_to(PROJECT_ROOT))],
        "candidate_records": int(len(candidates)),
        "unique_candidate_passages": int(candidates["passage_id"].nunique()),
        "category_counts": category_counts,
        "figure3_unit": "non-overlapping canonical keyword hits per 10,000 narrative words; inequality uses direct socioeconomic entries only",
        "figure3_inequality_scope": "direct_only; lodgers and infirmary excluded after sensitivity check",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
