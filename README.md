# Sanitary Governance and Urban Inequality in Whitechapel, 1890–1899

## A Computational and Spatial Analysis of Medical Officer of Health Reports

Public reproducibility repository for Jiang Jie’s CASA0010 MSc dissertation,
supervised by Duncan Hay.

This release contains the data, code, frozen manual inputs, analytical outputs
and public audit evidence needed to reproduce the reported computational and
spatial analysis. It does **not** contain the dissertation, declaration,
student number, supervisor correspondence, private examiner notes or signed
submission material.

## Quick start

```bash
cd reproducibility
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip==25.0.1
python -m pip install -r requirements-lock.txt
python run_all.py --clean
python tests/test_public_release.py
```

The verified public workflow has 21 analytical stages. Full stage descriptions,
expected counts and platform caveats are in
`reproducibility/README.md` and `reproducibility/RUN_ORDER.md`.
The canonical clean-room verification used Python 3.12.13, as pinned in
`reproducibility/.python-version`. The supported runtime is Python 3.12.x;
the regression test checks the major and minor version so another 3.12 patch
release can run the public workflow without weakening the canonical record.
On a recent Apple-silicon laptop the clean run takes about one minute; allow
longer on other machines. Principal outputs are the nine final figure files,
the controlled-retrieval tables, NMF tables, workplace summary and spatial
validation tables under `reproducibility/outputs/`.

## Evidence and provenance

- `references/bibliography_verified_FINAL.csv`: final public bibliography
  verification table. It records all 26 bibliography entries and both
  legislation entries extracted from the dissertation (28/28 verified).
- `references/citation_bidirectional_audit_FINAL.csv`: bidirectional citation
  audit for the same 26 bibliography and two legislation entries (28/28).
  The 1892 report (B18, b19883663) has an explicit annual citation in §3.3
  and is recorded as PASS.
- `references/quotation_audit_FINAL.csv`: full occurrence-level audit of all
  34 primary-source quotations in Chapters 1–7. Analytical labels are not
  counted as primary-source quotations.
- `references/source_urls.csv`: official source and archive links.

The forensic audit bundle is distributed alongside the analytical release in
the full GitHub repository under `audit_bundle/`. It is intentionally outside
`Whitechapel_Dissertation_Reproducibility_PUBLIC_FINAL_CITATIONFIX_CLEAN.zip`, so the
manifest can describe the analytical archive without a self-referential hash.
The following repository-relative paths resolve in the GitHub tree; they are
companion material and are not claimed to be inside the analytical ZIP:

### Distribution and path convention

`Whitechapel_Dissertation_Reproducibility_PUBLIC_FINAL_CITATIONFIX_CLEAN.zip` is distributed as a GitHub Release asset rather than tracked inside the normal repository tree. In `audit_bundle/PUBLIC_SHA256_MANIFEST_FINAL.csv`, paths beginning with `Whitechapel_Dissertation_Reproducibility_PUBLIC_FINAL_CITATIONFIX/` refer to the internal root folder of that clean release ZIP. In the GitHub repository itself, the same files appear directly from the repository root (for example, `reproducibility/...`), so that wrapper folder name is not part of Git paths.


- `audit_bundle/PUBLIC_FILE_INVENTORY_FINAL.csv`
- `audit_bundle/PUBLIC_SOURCE_AND_RIGHTS_AUDIT_FINAL.csv`
- `audit_bundle/PUBLIC_DISSERTATION_OUTPUT_CROSSCHECK_FINAL.csv`
- `audit_bundle/PUBLIC_PASSAGE_TRACEABILITY_AUDIT_FINAL.csv`
- `audit_bundle/PUBLIC_BIBLIOGRAPHY_VERIFICATION_FINAL.csv`
- `audit_bundle/PUBLIC_CITATION_BIDIRECTIONAL_AUDIT_FINAL.csv`
- `audit_bundle/PUBLIC_QUOTATION_AUDIT_FINAL.csv`
- `audit_bundle/PUBLIC_REPOSITORY_READINESS_REPORT_FINAL.md`
- `audit_bundle/PUBLIC_SHA256_MANIFEST_FINAL.csv`

## Legacy transcription encoding

The ten frozen raw TXT files are legacy transcriptions and are not valid
UTF-8 byte streams. The pipeline deliberately reads them as UTF-8 with
`errors="replace"`, producing exactly 5,993 U+FFFD replacement characters
across the corpus. The public release does not transcode the files or change
that established decoding rule because either change would alter the frozen
analytical input. This character noise is a source limitation. Quotations
used in the dissertation were separately checked against the source text or
the original report page image, as recorded in the quotation audit.

## NMF reproducibility boundary

The canonical primary NMF result is the deterministic `k=7`, `nndsvda`,
`random_state=0` solution. Its retained component assignment is 3/4/1/2/6,
and all seven primary components retain 11–12 of their top 12 terms in the
recorded platform comparison. Random-start sensitivity results are INFO-only,
non-blocking diagnostics. Their exact cosine values can vary with the
numerical environment and are not a release gate.

The top-30 place-term context export is presentation-only. Tied
`cooccurrence_count` values are ordered deterministically by
`standard_name` and then `term`; this does not alter the complete
co-occurrence table, the parent pair table or any dissertation result.

Spatial points are manual positions on one historical scan, not GIS
coordinates. Place–disease co-occurrence records documentary proximity in the
reports; it does not measure disease prevalence, incidence, risk or an
epidemiological distribution.

## Citation

Suggested repository citation:

> Jiang, Jie (2026). *Sanitary Governance and Urban Inequality in
> Whitechapel, 1890–1899: Reproducibility Repository*.

Add the final public repository URL and release identifier after publication.

## Licence and source rights

Project code is MIT-licensed. Researcher-created documentation and derivative
annotations are offered under CC BY 4.0 where the author owns the rights.
Historical transcription data, map imagery and external sources have separate
conditions. Read `RIGHTS_AND_LICENSING.md` before reuse.

For reproducibility questions, use the issue tracker of the final public
repository after it is published. No files have been uploaded or pushed by
this audit.
