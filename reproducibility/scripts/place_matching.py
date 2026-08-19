"""Auditable longest-match-first matching for controlled place gazetteers."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SurfaceForm:
    place_id: str
    standard_name: str
    place_type: str
    surface_form: str


@dataclass(frozen=True)
class PlaceMatch:
    place_id: str
    standard_name: str
    place_type: str
    surface_form: str
    start: int
    end: int


@dataclass(frozen=True)
class ExcludedMatch:
    place_id: str
    standard_name: str
    place_type: str
    surface_form: str
    start: int
    end: int
    blocked_by_place_id: str
    blocked_by_standard_name: str
    blocked_by_surface_form: str
    blocked_by_start: int
    blocked_by_end: int
    exclusion_reason: str = "overlaps_longer_retained_surface_form"


def normalize(value: str) -> str:
    value = str(value).lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9'\s-]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def surface_forms_from_gazetteer(gazetteer: pd.DataFrame) -> list[SurfaceForm]:
    """Return unique normalized surface forms and reject ambiguous ownership."""
    by_surface: dict[str, SurfaceForm] = {}
    for _, row in gazetteer.iterrows():
        raw_forms = [row["standard_name"]]
        variant_value = row.get("variant", "")
        if pd.notna(variant_value) and str(variant_value).strip():
            raw_forms.extend(re.split(r"[|;]", str(variant_value)))
        for raw_form in raw_forms:
            surface = normalize(raw_form)
            if not surface:
                continue
            record = SurfaceForm(
                place_id=str(row["place_id"]),
                standard_name=str(row["standard_name"]),
                place_type=str(row["type"]),
                surface_form=surface,
            )
            previous = by_surface.get(surface)
            if previous and previous.place_id != record.place_id:
                raise ValueError(
                    f"Ambiguous gazetteer surface form {surface!r}: "
                    f"{previous.place_id} and {record.place_id}"
                )
            by_surface[surface] = record
    return sorted(
        by_surface.values(),
        key=lambda item: (-len(item.surface_form), item.surface_form, item.place_id),
    )


def match_places(
    text: str,
    surface_forms: list[SurfaceForm],
) -> tuple[list[PlaceMatch], list[ExcludedMatch]]:
    """Match complete phrases longest-first and retain non-overlapping spans only."""
    text_clean = normalize(text)
    candidates: list[PlaceMatch] = []
    for record in surface_forms:
        pattern = rf"(?<![a-z0-9]){re.escape(record.surface_form)}(?![a-z0-9])"
        for found in re.finditer(pattern, text_clean, flags=re.IGNORECASE):
            candidates.append(
                PlaceMatch(
                    place_id=record.place_id,
                    standard_name=record.standard_name,
                    place_type=record.place_type,
                    surface_form=record.surface_form,
                    start=found.start(),
                    end=found.end(),
                )
            )

    # Width is the controlling priority. The remaining keys make ties stable.
    candidates.sort(
        key=lambda item: (
            -(item.end - item.start), item.start, item.surface_form, item.place_id
        )
    )
    accepted: list[PlaceMatch] = []
    excluded: list[ExcludedMatch] = []
    for candidate in candidates:
        blockers = [
            retained
            for retained in accepted
            if candidate.start < retained.end and retained.start < candidate.end
        ]
        if blockers:
            blocker = sorted(
                blockers,
                key=lambda item: (-(item.end - item.start), item.start, item.surface_form),
            )[0]
            excluded.append(
                ExcludedMatch(
                    place_id=candidate.place_id,
                    standard_name=candidate.standard_name,
                    place_type=candidate.place_type,
                    surface_form=candidate.surface_form,
                    start=candidate.start,
                    end=candidate.end,
                    blocked_by_place_id=blocker.place_id,
                    blocked_by_standard_name=blocker.standard_name,
                    blocked_by_surface_form=blocker.surface_form,
                    blocked_by_start=blocker.start,
                    blocked_by_end=blocker.end,
                )
            )
        else:
            accepted.append(candidate)

    accepted.sort(key=lambda item: (item.start, item.end, item.surface_form))
    excluded.sort(key=lambda item: (item.start, item.end, item.surface_form))
    return accepted, excluded


def nested_surface_form_pairs(surface_forms: list[SurfaceForm]) -> list[dict[str, str]]:
    """Identify every complete short-form containment in a longer surface form."""
    rows: list[dict[str, str]] = []
    for short in surface_forms:
        for long in surface_forms:
            if len(short.surface_form) >= len(long.surface_form):
                continue
            pattern = rf"(?<![a-z0-9]){re.escape(short.surface_form)}(?![a-z0-9])"
            found = re.search(pattern, long.surface_form)
            if not found:
                continue
            if found.start() == 0 and found.end() == len(long.surface_form):
                overlap_type = "exact"  # unreachable after the length check
            elif found.start() == 0:
                overlap_type = "short_form_prefix_of_long_form"
            elif found.end() == len(long.surface_form):
                overlap_type = "short_form_suffix_of_long_form"
            else:
                overlap_type = "short_form_embedded_in_long_form"
            accepted, excluded = match_places(long.surface_form, surface_forms)
            status = (
                "PASS"
                if sum(m.surface_form == long.surface_form for m in accepted) == 1
                and sum(m.surface_form == short.surface_form for m in accepted) == 0
                and sum(m.surface_form == short.surface_form for m in excluded) >= 1
                else "FAIL"
            )
            rows.append(
                {
                    "short_form": short.surface_form,
                    "long_form": long.surface_form,
                    "overlap_type": overlap_type,
                    "handling_rule": "longest-match-first; reject any overlapping shorter span",
                    "test_status": status,
                    "short_standard_name": short.standard_name,
                    "long_standard_name": long.standard_name,
                }
            )
    return sorted(rows, key=lambda row: (row["short_form"], row["long_form"]))
