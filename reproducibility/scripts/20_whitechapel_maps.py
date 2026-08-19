#!/usr/bin/env python3
"""Reproduce dissertation Figures 5 and 7 from the unified repository.

The source CSV files are never edited. Historical locations are read from two
separate, manually prepared image-pixel coordinate tables. These coordinates
are tied to the supplied Booth Sheet 63 JPEG and are not GIS geocodes.

The file is divided with ``# %%`` markers so it can also be run one section at
a time in editors that support Python cells.
"""

# %% 1. Imports and paths
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
COORDINATE_DIR = ROOT / "maps" / "coordinates"
MAP_DIR = ROOT / "outputs" / "figures"
AUDIT_DIR = ROOT / "audit" / "rerun"
BOOTH_PATH = ROOT / "maps" / "background_map" / "Booth_Sheet63_Whitechapel_1898_1899.jpg"

WORKPLACE_PATH = ROOT / "outputs" / "tables" / "technical" / "workplace_address_extraction.csv"
REVIEW_PATH = ROOT / "analysis" / "chapter3" / "spatial_review_log.csv"
VALIDATION_PATH = ROOT / "outputs" / "tables" / "technical" / "spatial_disease_validation.csv"
WORKPLACE_COORD_PATH = COORDINATE_DIR / "workplace_map_points_verified.csv"
PLACE_COORD_PATH = COORDINATE_DIR / "place_map_points_verified.csv"
OUT_OF_SHEET_PATH = COORDINATE_DIR / "out_of_sheet_place_references.csv"

EXPECTED_SIZE = (10059, 6746)
CROP_BOX = (4600, 200, 9800, 4600)  # includes the verified Bell Lane-area sites

MAP_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def split_places(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def crop_xy(row: dict[str, str]) -> tuple[float, float]:
    left, top, right, bottom = CROP_BOX
    x = float(row["image_x"])
    y = float(row["image_y"])
    if not (left <= x <= right and top <= y <= bottom):
        raise ValueError(f"Coordinate outside the fixed crop: {(x, y)}")
    return x - left, y - top


# %% 2. Load the frozen source tables and the un-georeferenced Booth scan
workplace_rows = read_csv(WORKPLACE_PATH)
review_rows = read_csv(REVIEW_PATH)
validation_rows = read_csv(VALIDATION_PATH)
workplace_coordinate_rows = read_csv(WORKPLACE_COORD_PATH)
place_coordinate_rows = read_csv(PLACE_COORD_PATH)
out_of_sheet_rows = read_csv(OUT_OF_SHEET_PATH)

booth_image = Image.open(BOOTH_PATH)
if booth_image.size != EXPECTED_SIZE:
    raise ValueError(
        f"Coordinates require a {EXPECTED_SIZE} image; found {booth_image.size}."
    )
booth_crop = booth_image.crop(CROP_BOX)

# The coordinate tables contain image_x/image_y only. They do not contain
# longitude, latitude, a CRS, control points or a geographic transformation.
WORKPLACE_REQUIRED_FIELDS = {
    "address", "image_x", "image_y", "status", "spatial_precision",
    "number_precision", "evidence_basis", "verification_note", "reviewed_on",
}
PLACE_REQUIRED_FIELDS = (WORKPLACE_REQUIRED_FIELDS - {"address"}) | {"place"}
OUT_OF_SHEET_REQUIRED_FIELDS = {
    "place", "mapping_status", "spatial_precision", "number_precision",
    "evidence_basis", "verification_note", "reviewed_on",
}
if not workplace_coordinate_rows or not WORKPLACE_REQUIRED_FIELDS.issubset(workplace_coordinate_rows[0]):
    raise ValueError("Verified workplace-coordinate schema is incomplete")
if not place_coordinate_rows or not PLACE_REQUIRED_FIELDS.issubset(place_coordinate_rows[0]):
    raise ValueError("Verified place-coordinate schema is incomplete")
if not out_of_sheet_rows or not OUT_OF_SHEET_REQUIRED_FIELDS.issubset(out_of_sheet_rows[0]):
    raise ValueError("Out-of-sheet place-reference schema is incomplete")


# %% 3. Figure 5 data: 24 proceedings aggregated to 23 unique addresses
def normalise_workplace_type(value: str) -> str:
    value = value.strip().lower()
    if value in {"workshop", "workshops"}:
        return "Workshop"
    if value == "bakehouse":
        return "Bakehouse"
    raise ValueError(f"Unexpected workplace type: {value}")


def outcome_group(value: str) -> str:
    """Documented display grouping; the original outcome text remains in CSV."""
    text = value.casefold()
    if "close" in text or "closed" in text or "disused" in text:
        return "closure_or_disuse"
    if "work done" in text or "works later carried out" in text:
        return "remedied_or_withdrawn"
    if "dismissed" in text or "outside retained passage context" in text:
        return "dismissed_or_unobserved"
    return "other_enforcement"


workplace_by_address: dict[str, list[dict[str, str]]] = defaultdict(list)
for row in workplace_rows:
    item = dict(row)
    item["normalised_type"] = normalise_workplace_type(row["workplace_type"])
    item["outcome_group"] = outcome_group(row["outcome"])
    workplace_by_address[row["address"].strip()].append(item)

workplace_coordinates = {
    row["address"].strip(): row for row in workplace_coordinate_rows
}

assert len(workplace_rows) == 24
assert len(workplace_by_address) == 23
assert Counter(row["normalised_type"] for rows in workplace_by_address.values() for row in rows) == {
    "Workshop": 20,
    "Bakehouse": 4,
}
assert {address: len(rows) for address, rows in workplace_by_address.items() if len(rows) > 1} == {
    "27 Old Montague Street": 2
}
assert set(workplace_by_address) == set(workplace_coordinates)


# %% 4. Draw Figure 5
OUTCOME_STYLE = {
    "remedied_or_withdrawn": ("#2E7D32", "Remedied / summons withdrawn"),
    "closure_or_disuse": ("#B71C1C", "Closure or disuse ordered"),
    "other_enforcement": ("#D98200", "Other order, fine or abatement"),
    "dismissed_or_unobserved": ("#6B7280", "Dismissed / outcome unavailable"),
}
OUTCOME_PRECEDENCE = [
    "closure_or_disuse",
    "remedied_or_withdrawn",
    "other_enforcement",
    "dismissed_or_unobserved",
]

address_order = sorted(workplace_by_address)
address_ids = {address: number for number, address in enumerate(address_order, 1)}

fig5, ax5 = plt.subplots(figsize=(10.2, 12.0))
ax5.imshow(booth_crop, origin="upper")
ax5.set_xlim(0, booth_crop.width)
ax5.set_ylim(booth_crop.height, 0)
ax5.set_axis_off()

figure5_points = []
coincident_ids: dict[tuple[float, float], list[int]] = defaultdict(list)
for address in address_order:
    coincident_ids[crop_xy(workplace_coordinates[address])].append(address_ids[address])
annotated_coordinates: set[tuple[float, float]] = set()
for address in address_order:
    records = workplace_by_address[address]
    types = {row["normalised_type"] for row in records}
    if len(types) != 1:
        raise ValueError(f"Mixed workplace types at {address}: {types}")
    workplace_type = next(iter(types))
    outcomes = {row["outcome_group"] for row in records}
    displayed_outcome = next(key for key in OUTCOME_PRECEDENCE if key in outcomes)
    x, y = crop_xy(workplace_coordinates[address])
    marker = "o" if workplace_type == "Workshop" else "^"
    colour = OUTCOME_STYLE[displayed_outcome][0]
    ax5.scatter(
        [x], [y], marker=marker, s=150, c=[colour], edgecolors="black",
        linewidths=0.9, alpha=0.94, zorder=4,
    )
    coordinate = (x, y)
    if coordinate not in annotated_coordinates:
        label = "/".join(str(value) for value in coincident_ids[coordinate])
        ax5.annotate(
            label, (x, y), xytext=(5, 5),
            textcoords="offset points", fontsize=7.2, weight="bold",
            bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.82),
            zorder=5,
        )
        annotated_coordinates.add(coordinate)
    if len(records) > 1:
        ax5.annotate(
            f"x{len(records)} proceedings", (x, y), xytext=(7, -12),
            textcoords="offset points", fontsize=6.5, color="#111827", zorder=5,
        )
    figure5_points.append(
        {
            "address": address,
            "proceedings": len(records),
            "workplace_type": workplace_type,
            "displayed_outcome": displayed_outcome,
            "status": workplace_coordinates[address]["status"],
            "spatial_precision": workplace_coordinates[address]["spatial_precision"],
            "number_precision": workplace_coordinates[address]["number_precision"],
        }
    )

type_handles = [
    Line2D([0], [0], marker="o", color="none", markerfacecolor="white",
           markeredgecolor="black", markersize=8, label="Workshop"),
    Line2D([0], [0], marker="^", color="none", markerfacecolor="white",
           markeredgecolor="black", markersize=8, label="Bakehouse"),
]
outcome_handles = [
    Line2D([0], [0], marker="o", color="none", markerfacecolor=colour,
           markeredgecolor="black", markersize=8, label=label)
    for colour, label in OUTCOME_STYLE.values()
]
legend1 = ax5.legend(
    handles=type_handles, title="Premises type", loc="upper left",
    frameon=True, framealpha=0.94, fontsize=8, title_fontsize=8,
)
ax5.add_artist(legend1)
ax5.legend(
    handles=outcome_handles, title="Recorded outcome (display grouping)",
    loc="upper right", frameon=True, framealpha=0.94,
    fontsize=8, title_fontsize=8,
)

fig5.suptitle(
    "Documented workplace enforcement addresses in Whitechapel, 1894-1896",
    x=0.5, y=0.975, fontsize=15, weight="bold",
)
fig5.text(
    0.5, 0.945,
    "24 proceedings at 23 unique addresses; one point per textual address.",
    ha="center", fontsize=9.5,
)

key_lines = [f"{address_ids[address]}. {address}" for address in address_order]
rows_per_column = math.ceil(len(key_lines) / 3)
for column in range(3):
    block = key_lines[column * rows_per_column : (column + 1) * rows_per_column]
    fig5.text(
        0.04 + column * 0.32, 0.205, "\n".join(block),
        ha="left", va="top", fontsize=7.2, linespacing=1.25,
    )

fig5.text(
    0.04, 0.052,
    "Location note: reviewed image-pixel positions are tied to this un-georeferenced Booth Sheet 63 scan. They are approximate, scan-specific historical locations, not GIS or doorway-precision geocodes.",
    ha="left", va="bottom", fontsize=7.4, wrap=True,
)
fig5.text(
    0.04, 0.027,
    "Background: Charles Booth, Hand Coloured Map Descriptive of London Poverty 1898-1899, Sheet 63 (LSE Digital Library; out of copyright).",
    ha="left", va="bottom", fontsize=7.4,
)
fig5.subplots_adjust(top=0.925, bottom=0.235, left=0.025, right=0.975)
fig5.savefig(MAP_DIR / "figure_05_workplace_enforcement_map.png", dpi=300,
             bbox_inches="tight", facecolor="white")
fig5.savefig(MAP_DIR / "figure_05_workplace_enforcement_map.pdf",
             bbox_inches="tight", facecolor="white")
plt.close(fig5)

# Keep the PNG canvas equal to the dissertation's existing Figure 5 canvas so
# replacing the embedded image does not distort Word's fixed display frame.
figure5_png = Image.open(MAP_DIR / "figure_05_workplace_enforcement_map.png").convert("RGB")
figure5_png.thumbnail((2961, 3469), Image.Resampling.LANCZOS)
figure5_canvas = Image.new("RGB", (2961, 3469), "white")
figure5_canvas.paste(
    figure5_png,
    ((figure5_canvas.width - figure5_png.width) // 2,
     (figure5_canvas.height - figure5_png.height) // 2),
)
figure5_canvas.save(
    MAP_DIR / "figure_05_workplace_enforcement_map.png", dpi=(300, 300)
)


# %% 5. Figure 7 data: keep 32 records, 16 places and 12 pairs separate
retained_review_rows = [
    row for row in review_rows
    if row["review_status"].strip() != "exclude_from_substantive_interpretation"
]

passages_by_place: dict[str, set[str]] = defaultdict(set)
for row in retained_review_rows:
    for place in split_places(row["matched_places"]):
        passages_by_place[place].add(row["passage_id"].strip())

place_coordinates = {row["place"].strip(): row for row in place_coordinate_rows}
out_of_sheet_references = {row["place"].strip(): row for row in out_of_sheet_rows}
pair_counts = Counter(row["validation_status"].strip() for row in validation_rows)

assert len(review_rows) == 38
assert len(retained_review_rows) == 32
assert len({row["passage_id"].strip() for row in retained_review_rows}) == 32
assert len(passages_by_place) == 16
assert len(validation_rows) == 12
assert pair_counts == {
    "false_structural_adjacency": 9,
    "direct_place_institution_disease": 2,
    "management_context_only": 1,
}
assert not (set(place_coordinates) & set(out_of_sheet_references))
assert set(passages_by_place) == set(place_coordinates) | set(out_of_sheet_references)
assert all(
    row["mapping_status"].strip() == "outside_sheet_extent"
    for row in out_of_sheet_references.values()
)

# Figure 7 deliberately does not convert the 12 pair-level classifications
# into place-level categories. Figure 6 reports those 12 validation outcomes.


# %% 6. Draw simplified Figure 7 with one neutral in-sheet symbol class
place_order = sorted(passages_by_place, key=lambda p: (-len(passages_by_place[p]), p))
place_ids = {place: number for number, place in enumerate(place_order, 1)}

fig7, ax7 = plt.subplots(figsize=(10.2, 11.4))
ax7.imshow(booth_crop, origin="upper")
ax7.set_xlim(0, booth_crop.width)
ax7.set_ylim(booth_crop.height, 0)
ax7.set_axis_off()

figure7_points = []
for place in place_order:
    passage_count = len(passages_by_place[place])
    if place in out_of_sheet_references:
        figure7_points.append(
            {
                "place": place,
                "retained_source_valid_passages": passage_count,
                "mapping_status": out_of_sheet_references[place]["mapping_status"],
                "status": "outside_sheet_extent",
                "spatial_precision": out_of_sheet_references[place]["spatial_precision"],
            }
        )
        continue
    x, y = crop_xy(place_coordinates[place])
    marker_size = 95 + 42 * math.sqrt(passage_count)
    ax7.scatter(
        [x], [y], marker="o", s=marker_size, c=["#FFFFFF"],
        edgecolors="#111827", linewidths=1.2, alpha=0.95, zorder=4,
    )
    ax7.annotate(
        str(place_ids[place]), (x, y), xytext=(5, 5),
        textcoords="offset points", fontsize=7.5, weight="bold",
        bbox=dict(boxstyle="round,pad=0.13", fc="white", ec="none", alpha=0.84),
        zorder=5,
    )
    figure7_points.append(
        {
            "place": place,
            "retained_source_valid_passages": passage_count,
            "mapping_status": "in_sheet_verified_coordinate",
            "status": place_coordinates[place]["status"],
            "spatial_precision": place_coordinates[place]["spatial_precision"],
        }
    )

size_handles = []
for count in (1, 4, 11):
    size_handles.append(
        plt.scatter([], [], s=95 + 42 * math.sqrt(count), c="white",
                    edgecolors="#111827", linewidths=1.2,
                    label=f"{count} retained passage" + ("s" if count != 1 else ""))
    )
ax7.legend(
    handles=size_handles, title="Marker-size examples", loc="upper right",
    frameon=True, framealpha=0.94, fontsize=7.7, title_fontsize=8,
)

fig7.suptitle(
    "Source-validated named-place references in the Whitechapel MOH narrative corpus, 1890-1899",
    x=0.5, y=0.975, fontsize=14.2, weight="bold",
)
fig7.text(
    0.5, 0.945,
    "32 retained source-valid records across 16 places; marker size = distinct retained passages per place.",
    ha="center", fontsize=9.2,
)

place_key_lines = []
for place in place_order:
    suffix = " - out of sheet" if place in out_of_sheet_references else ""
    place_key_lines.append(
        f"{place_ids[place]}. {place} ({len(passages_by_place[place])}){suffix}"
    )
rows_per_column = math.ceil(len(place_key_lines) / 3)
for column in range(3):
    block = place_key_lines[column * rows_per_column : (column + 1) * rows_per_column]
    fig7.text(
        0.04 + column * 0.32, 0.18, "\n".join(block),
        ha="left", va="top", fontsize=7.6, linespacing=1.3,
    )

fig7.text(
    0.04, 0.066,
    "Interpretation and location note: documentary visibility, not disease incidence, sanitary risk or prevalence. In-sheet points use approximate, scan-specific manually assigned image pixels, not GIS geocodes.",
    ha="left", va="bottom", fontsize=7.4, wrap=True,
)
fig7.text(
    0.04, 0.043,
    f"Mile End Old Town ({len(passages_by_place['Mile End Old Town'])} retained passages) is a neighbouring administrative reference; no in-sheet point is assigned because it falls outside, or largely outside, Sheet 63.",
    ha="left", va="bottom", fontsize=7.4, wrap=True,
)
fig7.text(
    0.04, 0.019,
    "Background: Charles Booth, Hand Coloured Map Descriptive of London Poverty 1898-1899, Sheet 63 (LSE Digital Library; out of copyright).",
    ha="left", va="bottom", fontsize=7.4,
)
fig7.subplots_adjust(top=0.925, bottom=0.225, left=0.025, right=0.975)
fig7.savefig(MAP_DIR / "figure_07_source_validated_places_map.png", dpi=300,
             bbox_inches="tight", facecolor="white")
fig7.savefig(MAP_DIR / "figure_07_source_validated_places_map.pdf",
             bbox_inches="tight", facecolor="white")
plt.close(fig7)

# Match the prior Figure 7 canvas to preserve the existing Word layout.
figure7_png = Image.open(MAP_DIR / "figure_07_source_validated_places_map.png").convert("RGB")
figure7_png.thumbnail((3256, 3302), Image.Resampling.LANCZOS)
figure7_canvas = Image.new("RGB", (3256, 3302), "white")
figure7_canvas.paste(
    figure7_png,
    ((figure7_canvas.width - figure7_png.width) // 2,
     (figure7_canvas.height - figure7_png.height) // 2),
)
figure7_canvas.save(
    MAP_DIR / "figure_07_source_validated_places_map.png", dpi=(300, 300)
)


# %% 7. Save an audit with source, coordinate and output hashes
audit_paths = [
    WORKPLACE_PATH,
    REVIEW_PATH,
    VALIDATION_PATH,
    WORKPLACE_COORD_PATH,
    PLACE_COORD_PATH,
    OUT_OF_SHEET_PATH,
    BOOTH_PATH,
    MAP_DIR / "figure_05_workplace_enforcement_map.png",
    MAP_DIR / "figure_05_workplace_enforcement_map.pdf",
    MAP_DIR / "figure_07_source_validated_places_map.png",
    MAP_DIR / "figure_07_source_validated_places_map.pdf",
]

audit = {
    "spatial_method_boundary": {
        "reproducible_code_steps": [
            "read frozen CSV files",
            "aggregate 24 proceedings to 23 textual addresses",
            "filter 38 review rows to 32 retained source-valid records",
            "aggregate those records to 16 named places",
            "keep the separate 12 place-disease pair classifications at pair level",
            "verify every retained place has either a verified in-sheet coordinate or an explicit outside-sheet status",
            "plot the supplied scan-specific image-pixel coordinates",
        ],
        "manual_historical_steps_not_reproduced_by_code": [
            "identify a historical street, court, alley, institution or district on the scan",
            "choose an approximate point or centroid",
            "interpolate or otherwise estimate an address along a historical street",
            "review the point against Booth Sheet 63 and independent historical-map evidence",
        ],
        "georeferencing": "none; manual image-pixel coordinates tied to the supplied JPEG",
    },
    "figure_5": {
        "source_rows": len(workplace_rows),
        "unique_addresses": len(workplace_by_address),
        "duplicate_address": {"27 Old Montague Street": 2},
        "normalised_record_types": {"Workshop": 20, "Bakehouse": 4},
        "points": figure5_points,
    },
    "figure_6_retained_in_dissertation": {
        "place_disease_pairs": len(validation_rows),
        "pair_level_counts": dict(pair_counts),
    },
    "figure_7": {
        "retained_source_valid_records": len(retained_review_rows),
        "named_places": len(passages_by_place),
        "in_sheet_mapped_places": len(place_coordinates),
        "out_of_sheet_places": len(out_of_sheet_references),
        "uses_pair_status_as_symbol_class": False,
        "points": figure7_points,
    },
    "files": {
        str(path.relative_to(ROOT)): {"sha256": file_hash(path)}
        for path in audit_paths
    },
    "excluded_legacy_input": "The pre-review spatial-summary table is not used or distributed; no third frequency map is produced.",
}

(AUDIT_DIR / "map_inputs_and_outputs_audit.json").write_text(
    json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
)

print(json.dumps({
    "figure_5_addresses": len(workplace_by_address),
    "figure_7_places": len(passages_by_place),
    "figure_6_pairs": len(validation_rows),
    "maps_directory": str(MAP_DIR),
    "audit": str(AUDIT_DIR / "map_inputs_and_outputs_audit.json"),
}, indent=2))
