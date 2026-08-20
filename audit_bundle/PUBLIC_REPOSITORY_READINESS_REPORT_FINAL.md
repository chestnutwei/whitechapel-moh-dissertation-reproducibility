# Public Repository Readiness Report — Polished Final Candidate

Audit date: 20 August 2026

## Final verdict

Repository published at https://github.com/chestnutwei/whitechapel-moh-dissertation-reproducibility;
Release v1.0.0 issued 19 August 2026. Dissertation Word/PDF source-check,
final-polish and five-meeting supervision-log QA are complete.

Frozen release:
https://github.com/chestnutwei/whitechapel-moh-dissertation-reproducibility/releases/tag/v1.0.0

Release asset:
`Whitechapel_Dissertation_Reproducibility_PUBLIC_FINAL_CITATIONFIX_CLEAN.zip`

SHA-256:
`83145cf726f34cd3baa5842cd9dd945a28b169b2b9289e3a866f5ccc0c41c4bd`

The repository and frozen v1.0.0 release are public. No dissertation Word or PDF file is included in the public repository or release asset. All frozen analytical results remain unchanged.

## Dissertation administrative QA

- Final private DOCX: `JiangJie_CASA0010_Dissertation_FINAL.docx`
- Final private DOCX SHA-256: `c6037301b26c32915a8aba5ac0c4d5bca44d5ca645837fe8218c8eac7f17f270`
- Final private PDF: `JiangJie_CASA0010_Dissertation_FINAL.pdf`
- Final private PDF SHA-256: `c3d339db1a002bece2506dec94e7d21b744f1b290da89c417182a026f4a7db8a`
- Microsoft Word body word count: **11,423 — PASS**
- Abstract word count: **224 — PASS**
- PDF pages / page size: **58 / A4 — PASS**
- Word/PDF visual render: **58 / 58 pages PASS**
- PDF Producer: **macOS 版本15.3.2（版号24D81） Quartz PDFContext — RECORDED**
- Embedded PDF fonts: **Times New Roman and Calibri — PASS**
- Tagged PDF: **No — RECORDED**
- PDF link annotations: **2; both target the repository URL — PASS**
- PDF bookmarks: **0 — RECORDED**
- PDF non-link annotations: **0 — PASS**
- Contents, chapter, figure, table and appendix pagination: **PASS**
- Figure 7 image and complete caption kept together on page 34: **PASS**
- Appendix B.2 heading and complete audit-trail table kept together on page 58: **PASS**
- Close-reading selection: **23 passages; 15 core; 8 supporting — PASS**
- Private dissertation, signature, audio or supervision files in public package: **0**

The final submission version differs from FINAL_POLISHED only through
presentation-level changes, including repository hyperlink activation and
shortened List of Figures entries. No analytical outputs, datasets, scripts,
figures or frozen results were changed.

The final private dissertation incorporates the source-checked model-dwellings
interpretation in Section 1.1, saved NMF/LDA sensitivity disclosures in Section
4.3, the Figure 7 passage-count clarification, the 12–14 August coordinate-review
milestone, and the linked 1897/1899 Bell Lane reading in Section 6.2. Appendix
B.1 still records the five supervision dates: 3 June, 8 July, 24 July, 7 August
and 17 August 2026. Final local polish strengthened the Section 2.7 research
gap, documented the 15-core/eight-supporting close-reading set in Section 6.1,
connected Section 7.5 to the NMF/LDA limitation and repaired the final contents,
figure-list and appendix pagination. Frozen analytical data and results, scripts,
CSV, JSON, PNG, model outputs and release assets were not changed.

## Citation compliance correction

- §3.3 RANGE CITATION REMOVED: **PASS**
- WHITECHAPEL BOARD OF WORKS 1892: **PASS**
- BIBLIOGRAPHY: **26 / 26 PASS**
- LEGISLATION: **2 / 2 PASS**
- TOTAL BIDIRECTIONAL COVERAGE: **28 / 28 PASS**
- Previous series-coverage status remaining: **0**
- MICROSOFT WORD COUNT: **11,423 — PASS**
- GITHUB UPLOAD: **PUBLISHED — REPOSITORY AND v1.0.0 RELEASE AVAILABLE**

The synthetic range citation in §3.3 was replaced by the explicit annual list
for 1891 through 1900. B18, Whitechapel Board of Works (1892), b19883663, now
has an explicit §3.3 citation and a PASS bidirectional status. The ten existing
annual-report bibliography entries and their verification metadata were not
changed.

## Deterministic top-30 correction

- DETERMINISTIC TOP-30 SORT: **PASS**
- AFFECTED OUTPUT IDENTIFIED: **PASS**
- AFFECTED TOP-30 OUTPUT: `reproducibility/outputs/tables/moh_top_place_term_pairs_contexts.csv`
- DOWNSTREAM DEPENDENCY: **NONE**
- DISSERTATION DEPENDENCY: **NO**
- PARENT COOCCURRENCE TABLE UNCHANGED: **PASS**
- PARENT PLACE-TERM TABLE UNCHANGED: **PASS**

The selection now sorts by descending `cooccurrence_count`, then ascending
`standard_name` and `term`, before taking 30 pairs. The affected stage was run
twice from identical inputs. Both parsed outputs contained 150 context rows in
the same 30-pair order, and both files had SHA-256
`5827b5403cfb61d0705b2479ca3a0199e6f6d04612fac56a742922b9e51e6de2`.
The same hash was produced by the final canonical workflow.

The complete co-occurrence table and its parent place-term pair table remained
byte-identical. The correction changes only the presentation-level membership
at the tied rank-30 boundary. No downstream active script, dissertation table,
figure, passage, claim or audit decision consumes this top-30 context file.

## Canonical reproduction

- CANONICAL PYTHON 3.12.13 RUN: **PASS**
- PUBLIC TEST: **PASS**
- Analytical stages: **21 / 21 PASS**
- Hash verification: **164 / 164 files; 0 mismatches — PASS**
- Second Python 3.12.x patch environment: **NOT AVAILABLE**

The normal documented workflow was used with a local `.venv`: first
`python run_all.py --clean`, followed by `python tests/test_public_release.py`.
The regression result was `public release regression checks: PASS`. The final
release does not contain the environment, bytecode or test caches.

## Frozen analytical results

- FROZEN DISSERTATION RESULTS: **UNCHANGED**
- Reports / cleaned words: **10 / 121,057**
- Passages: **657 total; 275 narrative; 382 table-context; 51,428 narrative words**
- Dictionary: **55 canonical entries**
- Close-reading candidates: **804 records; 250 passages**
- Candidate categories: **264 governance; 249 sanitary; 158 housing; 86 disease; 47 inequality**
- NMF: **275 before exclusions; 6 exclusions; 269 model passages; 50,303 words; k=7; nndsvda; random_state=0; retained components 3/4/1/2/6**
- Workplace: **24 proceedings; 23 unique textual addresses; 20 workshops; 4 bakehouses**
- Spatial: **38 raw candidates; 32 source-valid records; 16 named places; 15 in-sheet points**
- Place-disease: **12 pairs; 9 false structural/list adjacency; 2 direct; 1 management context**
- Legacy replacement characters under the frozen decoding workflow: **5,993**
- Random-start NMF: **INFO-only and non-blocking**

## Legacy verification clarification

The root README now identifies
`reproducibility/analysis/chapter5/verification/` as a provenance-preserving
intermediate verification area. Its legacy `chapter5` name predates the final
dissertation chapter numbering and largely corresponds to final Chapter 6.
The superseded `chapter5_category_count_check.csv` is not a final category-count
source. The authoritative frozen totals are in
`reproducibility/outputs/tables/chapter3/fig2_theme_distribution_data.csv`:
264 governance, 249 sanitary, 158 housing, 86 disease and 47 inequality.

## Source and traceability audits

- QUOTATION AUDIT: **34 / 34 PASS**
- Verification levels: **27 PAGE_IMAGE_VERIFIED; 7 SOURCE_TEXT_VERIFIED**
- BIBLIOGRAPHY: **26 / 26 PASS**
- LEGISLATION: **2 / 2 PASS**
- TOTAL SOURCE COVERAGE: **28 / 28 PASS**
- B18: **PASS**
- Passage traceability: **12 / 12 supported**
- Dissertation-output cross-check: **65 / 65 PASS**
- Cross-check mismatches: **0**

Passage `1890_0032` is explicitly traced and cross-checked as a structural or
list-adjacency example, not as a disease-location claim. The dissertation's
statement that four of the 24 workplace proceedings recorded separate female
accommodation is cross-checked against the four frozen source records: 29 Old
Montague Street, 9 Shepherd Street, 5 Cox Square and 12 Duncan Street.

## Audit bundle and README paths

- AUDIT BUNDLE FINAL FILENAMES: **PASS**
- Exact audit-bundle file count: **9**
- BROKEN README PATHS: **0**
- Obsolete audit filename references: **0**
- GITHUB PRIVATE FILE SCAN: **PASS**
- Repository/public analytical files: **173**
- Companion audit-bundle files: **9**
- Total public file members: **182**
- Transfer archive: `Whitechapel_GitHub_Upload_FINAL_FIVE_MEETINGS_CLEAN.zip`
- Transfer archive CRC / integrity: **PASS**
- Final public regression check: **PASS**
- Final audit update pushed to `main`: **20 AUGUST 2026**

The repository README identifies all nine companion forensic files under
`audit_bundle/`. These files are outside the clean analytical ZIP, so the
inventory and manifest can describe that archive without a self-referential
hash.

## Clean analytical release

- CLEAN RELEASE ZIP: **PASS**
- Archive: `Whitechapel_Dissertation_Reproducibility_PUBLIC_FINAL_CITATIONFIX_CLEAN.zip`
- Analytical files: **173**
- ZIP file members: **173**
- CRC / integrity: **PASS**
- Forbidden absolute paths: **0**
- Packaging debris: **0** for macOS metadata, AppleDouble files, Finder
  metadata, bytecode, notebook checkpoints, test caches and `.venv`
- NEW RELEASE SHA-256:
  `83145cf726f34cd3baa5842cd9dd945a28b169b2b9289e3a866f5ccc0c41c4bd`

The final inventory and manifest were regenerated from the actual analytical
release tree and independently byte-matched to every file member in the clean
ZIP. The clean ZIP is distributed as a GitHub Release asset, not as a tracked
repository file. Manifest paths prefixed with
`Whitechapel_Dissertation_Reproducibility_PUBLIC_FINAL_CITATIONFIX/` refer to the archive's
internal root; ordinary GitHub repository paths omit that wrapper.
