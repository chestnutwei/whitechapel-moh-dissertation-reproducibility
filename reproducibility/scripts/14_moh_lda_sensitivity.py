"""LDA baseline sensitivity check for the reduced topic-model corpus."""
from __future__ import annotations
import re
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT=Path(__file__).resolve().parents[1]
TECH=PROJECT_ROOT/'outputs'/'tables'/'technical'
INPUT=TECH/'topic_model_input.csv'
K_VALUES=[4,5,6,7,8]
SEEDS=[1,21,42,84,100]
TOP_N=12

def norm(a):
    n=np.linalg.norm(a,axis=1,keepdims=True); n[n==0]=1; return a/n

def match(a,b):
    sim=cosine_similarity(norm(a),norm(b)); r,c=linear_sum_assignment(-sim); o=np.argsort(r); r,c=r[o],c[o]; return c,sim[r,c]

def tops(h,features):
    return [features[np.argsort(x)[::-1][:TOP_N]].tolist() for x in h]

def jac(a,b):
    a,b=set(a),set(b); return len(a&b)/len(a|b) if a|b else 1

def main():
    d=pd.read_csv(INPUT)
    d=d[~d.topic_model_excluded.astype(bool)].copy()
    vec=CountVectorizer(stop_words='english',min_df=2,max_df=.90,ngram_range=(1,2),max_features=2500)
    X=vec.fit_transform(d.topic_model_text.fillna(''))
    feats=np.array(vec.get_feature_names_out())
    summaries=[]
    for k in K_VALUES:
        ms={}
        for seed in SEEDS:
            m=LatentDirichletAllocation(n_components=k,random_state=seed,learning_method='online',max_iter=25,evaluate_every=-1)
            W=m.fit_transform(X); H=m.components_
            ms[seed]=(W,H,tops(H,feats))
        rows=[]
        for i,a in enumerate(SEEDS):
            for b in SEEDS[i+1:]:
                cols,scores=match(ms[a][1],ms[b][1]); js=[jac(ms[a][2][t],ms[b][2][cols[t]]) for t in range(k)]
                rows.append({'k':k,'seed_a':a,'seed_b':b,'mean_cosine':np.mean(scores),'median_cosine':np.median(scores),'min_cosine':np.min(scores),'mean_top12_jaccard':np.mean(js),'min_top12_jaccard':np.min(js)})
        pdf=pd.DataFrame(rows); pdf.to_csv(TECH/f'lda_pairwise_stability_k{k}.csv',index=False)
        summaries.append({'k':k,'pairwise_mean_cosine':pdf.mean_cosine.mean(),'pairwise_median_cosine':pdf.median_cosine.median(),'worst_pair_min_cosine':pdf.min_cosine.min(),'pairwise_mean_top12_jaccard':pdf.mean_top12_jaccard.mean(),'worst_pair_min_top12_jaccard':pdf.min_top12_jaccard.min()})
    s=pd.DataFrame(summaries); s.to_csv(TECH/'lda_stability_summary.csv',index=False); print(s.to_string(index=False))
if __name__=='__main__': main()
