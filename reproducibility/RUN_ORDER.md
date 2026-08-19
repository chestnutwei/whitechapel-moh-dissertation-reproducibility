# Public run order

`python run_all.py --clean` executes these stages in order:

1. Corpus quality check
2. Whole-corpus feasibility keyword retrieval
3. Gazetteer place retrieval
4. Place-term co-occurrence
5. Basic diagnostic figures
6. Co-occurrence contexts
7. Narrative/table-context passage classification
8. Frozen 55-entry narrative dictionary analysis
9. Close-reading candidate generation
10. Spatial-reference candidate generation
11. Corpus-workflow Figure 1
12. Chapter 3 Figures 2 and 3
13. Dictionary appendix
14. Primary NMF and seed sensitivity
15. LDA sensitivity
16. Lexical-normalisation audit
17. Spatial-disease validation
18. Figures 4 and 6
19. Inequality-marker sensitivity
20. Workplace-address extraction
21. Figures 5 and 7

The public workflow ends at the analytical outputs. Submission-specific DOCX,
PDF, word-count, examiner and packaging checks are intentionally private and
are not dependencies of this repository.
