"""Audit the frozen limited lexical-normalisation rules against the narrative corpus."""
from __future__ import annotations
import re
from pathlib import Path
import sys
import pandas as pd

PROJECT_ROOT=Path(__file__).resolve().parents[1]
TABLES=PROJECT_ROOT/'outputs'/'tables'
OUT=TABLES/'technical'/'lexical_normalisation_audit.csv'
PASSAGES=TABLES/'moh_narrative_passages.csv'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from moh_keyword_dictionary import TERM_GROUPS, LEXICAL_VARIANTS, OCR_EXCLUSIONS

def count_exact(text,form):
    pattern=rf'(?<![a-z0-9]){re.escape(form.lower())}(?![a-z0-9])'
    return len(re.findall(pattern,text.lower()))

def main():
    d=pd.read_csv(PASSAGES); d=d[d.likely_narrative==True].copy()
    rows=[]
    cat_by={t:c for c,ts in TERM_GROUPS.items() for t in ts}
    for canonical,variants in LEXICAL_VARIANTS.items():
        for form in [canonical,*variants]:
            counts=d.passage_text.fillna('').map(lambda x: count_exact(x,form))
            rows.append({'canonical_entry':canonical,'category':cat_by[canonical],'surface_form':form,'surface_type':'canonical' if form==canonical else 'source_verified_variant','raw_occurrences':int(counts.sum()),'distinct_passages':int((counts>0).sum()),'included_in_alias_layer':True})
    for form,reason in OCR_EXCLUSIONS.items():
        counts=d.passage_text.fillna('').map(lambda x: count_exact(x,form))
        rows.append({'canonical_entry':'lodging house','category':'housing','surface_form':form,'surface_type':'OCR_error','raw_occurrences':int(counts.sum()),'distinct_passages':int((counts>0).sum()),'included_in_alias_layer':False,'note':reason})
    out=pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True,exist_ok=True); out.to_csv(OUT,index=False)
    print(out.to_string(index=False))
if __name__=='__main__': main()
