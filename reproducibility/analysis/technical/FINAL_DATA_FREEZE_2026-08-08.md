WHITECHAPEL DISSERTATION — DATA/METHOD FREEZE
Date: 8 August 2026

FINAL CONTROLLED RETRIEVAL
- Narrative corpus: 275 passages / 51,428 words
- Canonical dictionary entries: 55
- Candidate records: 804
- Distinct candidate passages: 250
- Governance: 264 records
- Sanitation: 249 records
- Housing: 158 records
- Disease: 86 records
- Inequality: 47 records

LEXICAL NORMALISATION
- Limited lexical normalisation only; no open-ended OCR correction.
- Added source-verified variants common lodginghouse and common lodginghouses to the common lodging house canonical entry.
- Final raw allocation: lodging house = 33 hits; common lodging house = 15 hits.
- LodingHouses remains excluded as an OCR-induced misreading.

INEQUALITY SENSITIVITY CHECK
- Full retrieval layer (direct + indirect markers): 47 candidate records / 41 distinct passages / 57 raw hits.
- Direct socioeconomic entries only: 33 candidate records / 29 distinct passages / 36 raw hits.
- lodgers and infirmary remain in candidate retrieval but are not treated as automatic inequality evidence.
- Figure 2 retains the full inequality retrieval count (47).
- Figure 3 uses direct socioeconomic entries only for inequality because the indirect markers materially alter the descriptive year-by-year series.

TOPIC MODELLING
- Topic-model input: 269 passages / 50,303 original words after fixed exclusion of 6 recurrent front-matter passages.
- NMF sensitivity uses init=random, k=4–8, seeds 1/21/42/84/100.
- Only five recurrent/interpretable k=7 components are retained; two unstable components are excluded.

SPATIAL–DISEASE VALIDATION
- 12 automated place–disease candidate pairs.
- 2 direct place–institution–disease associations.
- 1 disease-management-context association.
- 9 false structural/list-adjacency associations.
- The spatial layer is documentary/contextual, not epidemiological.

FILES
- dissertation_docs/: revised Chapters 3–7 + Appendix A
- figures/: Figures 1–5 used in revised chapters
- key_data_tables/: frozen output tables and sensitivity/audit files
- technical_project/: complete reproducible project copy with updated scripts and outputs
