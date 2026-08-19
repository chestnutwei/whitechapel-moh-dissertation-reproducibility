"""Compare direct inequality vocabulary with direct + indirect retrieval markers.

The controlled dictionary retains lodgers and infirmary as context-dependent indirect
markers for candidate retrieval. This sensitivity check quantifies how much those
markers affect the descriptive inequality counts. It does not reclassify passages.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

PROJECT_ROOT=Path(__file__).resolve().parents[1]
TABLES=PROJECT_ROOT/'outputs'/'tables'
TECH=TABLES/'technical'
COUNTS=TABLES/'moh_narrative_keyword_counts.csv'
CANDIDATES=TABLES/'moh_close_reading_candidates.csv'
INDIRECT={'lodgers','infirmary'}

def main():
    TECH.mkdir(parents=True,exist_ok=True)
    counts=pd.read_csv(COUNTS)
    cands=pd.read_csv(CANDIDATES)
    ineq_counts=counts[counts.category.eq('inequality')].copy()
    ineq_cands=cands[cands.category.eq('inequality')].copy()

    summaries=[]
    for scope,term_filter in [
        ('all',pd.Series(True,index=ineq_counts.index)),
        ('direct_only',~ineq_counts.term.isin(INDIRECT)),
    ]:
        sub=ineq_counts[term_filter]
        cand_terms=set(sub.term.unique())
        sc=ineq_cands[ineq_cands.term.isin(cand_terms)]
        summaries.append({
            'scope':scope,
            'candidate_records':int(len(sc)),
            'distinct_passages':int(sc.passage_id.nunique()),
            'raw_hits':int(sub.raw_count.sum()),
        })
    pd.DataFrame(summaries).to_csv(TECH/'inequality_marker_sensitivity_summary.csv',index=False)

    rows=[]
    for year,g in ineq_counts.groupby('report_year'):
        words=int(g.narrative_word_count.iloc[0])
        all_hits=int(g.raw_count.sum())
        direct_hits=int(g.loc[~g.term.isin(INDIRECT),'raw_count'].sum())
        rows.append({
            'report_year':int(year),
            'all_raw_hits':all_hits,
            'direct_raw_hits':direct_hits,
            'all_per_10000':all_hits/words*10000 if words else 0,
            'direct_per_10000':direct_hits/words*10000 if words else 0,
        })
    pd.DataFrame(rows).sort_values('report_year').to_csv(TECH/'inequality_marker_sensitivity_by_year.csv',index=False)
    print(pd.DataFrame(summaries).to_string(index=False))

if __name__=='__main__':
    main()
