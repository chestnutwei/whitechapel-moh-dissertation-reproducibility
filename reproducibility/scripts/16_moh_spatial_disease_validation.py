"""Build and validate place-disease co-occurrence candidates from source-valid spatial passages."""
from __future__ import annotations
from pathlib import Path
import sys
import pandas as pd

PROJECT_ROOT=Path(__file__).resolve().parents[1]
TABLES=PROJECT_ROOT/'outputs'/'tables'
TECH=TABLES/'technical'
PASSAGES=TABLES/'moh_narrative_passages.csv'
SPATIAL=PROJECT_ROOT/'analysis'/'chapter3'/'spatial_review_log.csv'
MANUAL=PROJECT_ROOT/'analysis'/'technical'/'spatial_disease_manual_validation.csv'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from moh_keyword_dictionary import clean_text, matched_canonical_terms_nonoverlapping

def main():
    p=pd.read_csv(PASSAGES).set_index('passage_id')
    s=pd.read_csv(SPATIAL)
    valid=s[~s.review_status.astype(str).str.startswith('exclude')].copy()
    rows=[]
    for _,r in valid.iterrows():
        pid=r.passage_id
        text=p.loc[pid,'passage_text']
        matched=matched_canonical_terms_nonoverlapping(clean_text(text))
        disease=sorted(term for term,cat in matched if cat=='disease')
        if not disease:
            continue
        for place in str(r.matched_places).split(';'):
            rows.append({'report_year':int(r.report_year),'passage_id':pid,'place':place.strip(),'disease_terms':'; '.join(disease),'passage_text':text})
    candidates=pd.DataFrame(rows)
    manual=pd.read_csv(MANUAL)
    out=candidates.merge(manual,on=['passage_id','place'],how='left',validate='one_to_one')
    if out.validation_status.isna().any():
        missing=out[out.validation_status.isna()][['passage_id','place']]
        raise ValueError(f'Missing manual validation rows:\n{missing}')
    TECH.mkdir(parents=True,exist_ok=True)
    candidates.to_csv(TECH/'spatial_disease_candidate_pairs.csv',index=False)
    out.to_csv(TECH/'spatial_disease_validation.csv',index=False)
    summary=(out.groupby('validation_status').size().rename('place_passage_pairs').reset_index().sort_values('place_passage_pairs',ascending=False))
    summary.to_csv(TECH/'spatial_disease_validation_summary.csv',index=False)
    print('Source-valid spatial passage records:',len(valid))
    print('Distinct source-valid places:',len({x.strip() for v in valid.matched_places for x in str(v).split(';')}))
    print('Raw place-disease candidate pairs:',len(out))
    print(summary.to_string(index=False))
if __name__=='__main__': main()
