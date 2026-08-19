"""Create technical-analysis figures from the frozen NMF and spatial-validation outputs."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from portable_fonts import load_pillow_font

PROJECT_ROOT=Path(__file__).resolve().parents[1]
TECH=PROJECT_ROOT/'outputs'/'tables'/'technical'
FIG=PROJECT_ROOT/'outputs'/'figures'
OUTPUT_AUDIT=PROJECT_ROOT/'outputs'/'audit'
FIG.mkdir(parents=True,exist_ok=True)

INTERPRETATIONS = [
    ("Address-specific enforcement proceedings", "Address-specific\nenforcement\nproceedings", ("street", "summons", "withdrawn", "workshop")),
    ("Sanitary authority, statutory penalties and legal powers", "Sanitary authority,\nstatutory penalties\nand legal powers", ("authority", "sanitary authority", "section", "notice")),
    ("Housing reform and metropolitan governance", "Housing reform\nand metropolitan\ngovernance", ("houses", "district", "council", "county council")),
    ("Sanitary construction regulations", "Sanitary construction\nregulations", ("construct", "receptacle", "watercloset", "privy")),
    ("Penalty and by-law clauses", "Penalty and\nby-law clauses", ("penalty", "offence", "bye laws", "foregoing bye")),
]


def identify_interpreted_topics(terms: pd.DataFrame) -> list[tuple[int, str, str]]:
    """Globally assign one unique primary component to each semantic label."""
    from scipy.optimize import linear_sum_assignment

    topic_ids = terms["topic"].astype(int).tolist()
    term_sets = [set(str(value).split("; ")) for value in terms["top_terms"]]
    score_matrix = np.array([
        [sum(term in words for term in required) for words in term_sets]
        for _label, _display, required in INTERPRETATIONS
    ], dtype=float)
    rows, cols = linear_sum_assignment(-score_matrix)
    assigned = dict(zip(rows.tolist(), cols.tolist()))
    audit_rows = []
    matches = []
    for label_idx, (label, display, required) in enumerate(INTERPRETATIONS):
        chosen_col = assigned[label_idx]
        topic = topic_ids[chosen_col]
        score = float(score_matrix[label_idx, chosen_col])
        alternatives = sorted(
            ((float(score_matrix[label_idx, col]), topic_ids[col]) for col in range(len(topic_ids)) if col != chosen_col),
            reverse=True,
        )
        second_score, second_topic = alternatives[0]
        margin = score - second_score
        status = "assigned" if score >= 3 and margin >= 1 else "ambiguous"
        audit_rows.append({
            "interpretive_label": label,
            "topic_id": topic,
            "score": score,
            "top_terms": terms.loc[terms.topic == topic, "top_terms"].iloc[0],
            "second_best_topic": second_topic,
            "second_best_score": second_score,
            "assignment_margin": margin,
            "status": status,
            "notes": "Global one-to-one assignment using scipy.optimize.linear_sum_assignment.",
        })
        if status != "assigned":
            pd.DataFrame(audit_rows).to_csv(TECH / "nmf_component_assignment.csv", index=False)
            raise ValueError(f"Ambiguous primary NMF component assignment: {label}")
        matches.append((topic, label, display))
    assignment_df=pd.DataFrame(audit_rows)
    assignment_df.to_csv(TECH / "nmf_component_assignment.csv", index=False)
    OUTPUT_AUDIT.mkdir(parents=True,exist_ok=True)
    assignment_df.to_csv(OUTPUT_AUDIT / "nmf_component_assignment.csv", index=False)
    return matches

def font(size,bold=False):
    return load_pillow_font(size, bold=bold)

def mix(f):
    a=np.array([244,247,250]); b=np.array([52,112,153]); c=np.round(a+(b-a)*max(0,min(1,f))).astype(int); return tuple(c)

def fig4():
    d=pd.read_csv(TECH/'nmf_primary_document_topics_k7.csv')
    terms=pd.read_csv(TECH/'nmf_primary_topics_k7.csv')
    interpreted=identify_interpreted_topics(terms)
    primary_topics=[topic for topic,_label,_display in interpreted]
    display_labels={topic:display for topic,_label,display in interpreted}
    cols=[f'topic_{i}' for i in range(1,8)]
    denom=d[cols].sum(axis=1).replace(0,np.nan)
    for i in range(1,8): d[f'norm_{i}']=d[f'topic_{i}']/denom
    rows=[]
    for year,g in d.groupby('report_year'):
        row={'report_year':int(year)}
        for i in primary_topics: row[f'topic_{i}']=g[f'norm_{i}'].mean()
        rows.append(row)
    out=pd.DataFrame(rows).sort_values('report_year')

    W,H=2300,1500; im=Image.new('RGB',(W,H),'white'); dr=ImageDraw.Draw(im)
    left,top=250,120; cw,ch=360,110
    vals=out[[f'topic_{i}' for i in primary_topics]].to_numpy(); mx=float(vals.max())
    for ri,(_,r) in enumerate(out.iterrows()):
        y0=top+ri*ch; dr.text((left-25,y0+ch/2),str(int(r.report_year)),font=font(34),fill='#444',anchor='rm')
        for ci,i in enumerate(primary_topics):
            x0=left+ci*cw; v=float(r[f'topic_{i}']); col=mix(v/mx if mx else 0)
            dr.rectangle((x0,y0,x0+cw,y0+ch),fill=col,outline='white',width=4)
            lum=.2126*col[0]+.7152*col[1]+.0722*col[2]; tc='white' if lum<145 else '#111'
            dr.text((x0+cw/2,y0+ch/2),f'{v:.3f}',font=font(30,True),fill=tc,anchor='mm')
    bottom=top+len(out)*ch
    for ci,i in enumerate(primary_topics):
        label=display_labels[i]
        x=left+ci*cw+cw/2; dr.multiline_text((x,bottom+30),label,font=font(29),fill='#333',anchor='ma',align='center',spacing=5)
    dr.text((left+len(primary_topics)*cw/2,H-70),'Primary NMF component (mean normalised passage weight)',font=font(36),fill='#111',anchor='mm')
    out.to_csv(TECH/'nmf_primary_topics_by_year.csv',index=False)
    im.save(FIG/'figure_04_nmf_primary_topics_by_year.png',dpi=(300,300))
    return interpreted,terms


def write_random_sensitivity_diagnostic(interpreted, primary_terms):
    """Record, but never enforce, random-start recovery of primary topics."""
    from scipy.optimize import linear_sum_assignment
    from sklearn.metrics.pairwise import cosine_similarity

    OUTPUT_AUDIT.mkdir(parents=True,exist_ok=True)
    seeds=[1,21,42,84,100]
    primary_h=np.load(TECH/'nmf_primary_components_k7.npy')
    primary_sets={int(r.topic):set(str(r.top_terms).split('; ')) for r in primary_terms.itertuples(index=False)}
    labels={int(topic):label for topic,label,_display in interpreted}
    rows=[]
    for seed in seeds:
        try:
            random_h=np.load(TECH/f'nmf_random_components_k7_seed{seed}.npy')
            random_terms=pd.read_csv(TECH/f'nmf_random_topics_k7_seed{seed}.csv')
            random_sets={int(r.topic):set(str(r.top_terms).split('; ')) for r in random_terms.itertuples(index=False)}
            similarity=cosine_similarity(primary_h,random_h)
            pidx,ridx=linear_sum_assignment(-similarity)
            matched={int(p)+1:int(r)+1 for p,r in zip(pidx,ridx)}
            for primary_topic,label in labels.items():
                random_topic=matched[primary_topic]
                cosine=float(similarity[primary_topic-1,random_topic-1])
                overlap=len(primary_sets[primary_topic]&random_sets[random_topic])
                if cosine>=0.90 and overlap>=8:
                    status='recovered'
                elif cosine>=0.50 or overlap>=4:
                    status='weakly_recovered'
                else:
                    status='unstable'
                rows.append({'primary_topic_id':primary_topic,'interpretive_label':label,
                    'random_seed':seed,'best_random_topic':random_topic,
                    'cosine_similarity':cosine,'top_term_overlap':overlap,'status':status,
                    'notes':'Sensitivity diagnostic only; this status is not a prerequisite for Table 4.1 or Figure 4.'})
        except Exception as exc:
            for primary_topic,label in labels.items():
                rows.append({'primary_topic_id':primary_topic,'interpretive_label':label,
                    'random_seed':seed,'best_random_topic':'','cosine_similarity':'','top_term_overlap':'',
                    'status':'not_available','notes':f'Sensitivity diagnostic unavailable: {type(exc).__name__}: {exc}. Main primary outputs remain independent.'})
    pd.DataFrame(rows).to_csv(OUTPUT_AUDIT/'nmf_random_sensitivity_by_primary_component.csv',index=False)

def fig6():
    s=pd.read_csv(TECH/'spatial_disease_validation_summary.csv')
    counts=dict(zip(s.validation_status,s.place_passage_pairs))
    raw=sum(counts.values())
    W,H=2100,900; im=Image.new('RGB',(W,H),'white'); dr=ImageDraw.Draw(im)
    ftitle=font(44,True); fbig=font(52,True); flab=font(33); fsmall=font(28)
    # left raw-candidate box
    dr.rounded_rectangle((120,250,650,610),radius=30,fill='#ECEFF2',outline='#56616B',width=4)
    dr.text((385,340),str(raw),font=fbig,fill='#111',anchor='mm')
    dr.multiline_text((385,455),'passage-level place–disease\ncandidate pairs',font=flab,fill='#222',anchor='mm',align='center',spacing=8)
    # arrow
    dr.line((680,430,920,430),fill='#555',width=8); dr.polygon([(920,430),(875,400),(875,460)],fill='#555')
    # right outcomes
    boxes=[
        ('direct_place_institution_disease','Direct place–institution–disease\nassociation','#DDE8EF'),
        ('management_context_only','Disease-management context only','#E9ECEF'),
        ('false_structural_adjacency','False structural / list adjacency','#F0F0F0'),
    ]
    ys=[120,345,570]
    for (key,label,fill),y in zip(boxes,ys):
        dr.rounded_rectangle((990,y,1960,y+170),radius=24,fill=fill,outline='#56616B',width=3)
        dr.text((1090,y+85),str(int(counts.get(key,0))),font=fbig,fill='#111',anchor='mm')
        dr.multiline_text((1510,y+85),label,font=flab,fill='#222',anchor='mm',align='center',spacing=7)
    dr.text((1050,55),'Contextual validation of automated place–disease co-occurrence',font=ftitle,fill='#111',anchor='mm')
    dr.text((1050,835),'Only source-valid place references were included; co-occurrence was not treated as epidemiological evidence.',font=fsmall,fill='#444',anchor='mm')
    im.save(FIG/'figure_06_spatial_disease_validation.png',dpi=(300,300))

if __name__=='__main__':
    interpreted,terms=fig4()
    fig6()
    write_random_sensitivity_diagnostic(interpreted,terms)
    print('Wrote deterministic-primary Figure 4, independent Figure 6, and non-blocking random-start diagnostics.')
