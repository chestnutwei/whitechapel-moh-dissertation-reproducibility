# Analytical workflow

This directory reproduces the quantitative, text-analysis and cartographic
outputs for *Sanitary Governance and Urban Inequality in Whitechapel,
1890–1899*. It does not contain the dissertation, student declaration,
supervisor material or private examiner audits.

## Canonical and supported environment

The canonical verified environment uses Python 3.12.13, pinned in
`.python-version`, with the complete dependency lock in
`requirements-lock.txt`. The supported runtime is Python 3.12.x. The public
regression test checks the major and minor version; 3.12.13 remains the exact
release environment recorded for comparison.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip==25.0.1
python -m pip install -r requirements-lock.txt
```

## Reproduce the analysis

From this directory, run:

```bash
python run_all.py --clean
python tests/test_public_release.py
```

The runner executes 21 dependency-ordered stages, stops at the first failure,
and records stage status under `audit/`. A clean verified run takes about one
minute on a recent Apple-silicon laptop; other machines can take longer.

## Frozen analytical scope

- 10 Medical Officer of Health reports, 121,057 source words.
- 657 passages: 275 narrative and 382 table-context passages.
- 51,428 words in the narrative subset.
- A frozen 55-entry controlled dictionary and 804 candidate rows representing
  250 distinct candidate passages.
- A primary NMF model on 269 included passages, with `k=7`, `nndsvda`
  initialisation and `random_state=0`; five components are retained for the
  reported interpretation, with component assignment 3/4/1/2/6.
- 24 workplace proceedings, 23 distinct textual addresses, 20 workshop and 4
  bakehouse records.
- 38 raw spatial records, 32 source-valid retained records, 16 named places,
  15 in-sheet coordinates and one explicit out-of-sheet reference.
- 12 place-disease validation pairs: 9 false structural/list adjacency, 2
  direct place-institution-disease links and 1 management-context-only pair.

The controlled dictionary is defined in `scripts/moh_keyword_dictionary.py`.
The whole-corpus keyword stage is an earlier feasibility check and is not the
final narrative dictionary analysis.

The deterministic primary NMF solution is the canonical result. The recorded
platform comparison retains 11–12 of the top 12 terms for every primary
component. Random-start sensitivity outputs are INFO-only, non-blocking
diagnostics: exact random-start cosine values may differ across numerical
environments and are not a release gate.

## Legacy raw-text encoding

The ten frozen files in `data/raw/moh/` are legacy transcriptions and are not
valid UTF-8 byte streams. The first pipeline stage reads them as UTF-8 with
`errors="replace"`, yielding exactly 5,993 U+FFFD replacement characters in
total. Do not transcode the raw files or change this decoding rule: both are
part of the frozen analytical input. The resulting character noise is a
source limitation, while dissertation quotations have separate source-text
or original-page checks in `../references/quotation_audit_FINAL.csv`.

## Directory guide

- `data/raw/moh/`: frozen report transcriptions.
- `data/metadata/`: source identifiers and active frozen classifications.
- `data/gazetteer/`: controlled place vocabulary and exclusions.
- `maps/background_map/`: Booth Sheet 63 image used for Figures 5 and 7.
- `maps/coordinates/`: active scan-pixel coordinate tables.
- `analysis/`: active manual review inputs and verification evidence.
- `scripts/`: the 21 public analytical stages and shared modules.
- `outputs/`: reproducible tables, figures and technical diagnostics.
- `notebooks/`: editable and executed map walkthroughs.
- `audit/`: public analytical checks; run logs are regenerated locally.

The map coordinates are positions on the supplied 10,059 × 6,746 pixel scan,
not longitude/latitude, British National Grid coordinates, GIS geocodes or
doorway positions. Do not apply them to another or resized image.

The workflow checks nine final figure files. PNG or PDF bytes can vary with
platform fonts and encoders. The checks rely on analytical tables and decoded
content rather than claiming cross-platform byte identity for every rendered
figure.

The top-30 place-term context export is presentation-only. Ties in
`cooccurrence_count` are resolved deterministically by `standard_name` and
then `term`. This ordering does not change the complete co-occurrence table,
the parent pair table or any dissertation result.

Source provenance and rights boundaries are in the repository-level README,
`RIGHTS_AND_LICENSING.md`, the repository-root
`audit_bundle/PUBLIC_SOURCE_AND_RIGHTS_AUDIT_FINAL.csv` in the full GitHub
companion tree, and the
bibliography files under `../references/`.
