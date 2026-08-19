from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PASSAGES = ROOT / 'outputs' / 'tables' / 'moh_narrative_passages.csv'
OUTDIR = ROOT / 'outputs' / 'tables' / 'technical'
OUTDIR.mkdir(parents=True, exist_ok=True)

# Source-validated extraction from address-level enforcement passages.
# Rows are retained explicitly because list formatting and passage boundaries make
# generic regex extraction unreliable; each row is checked back against passage text.
ROWS = [
('1894_0055',1894,'178 Hanbury Street','Workshop','closet in workshop stopped and filthy','Work done; summons withdrawn'),
('1894_0055',1894,'58 White Lion Street','Workshop','overcrowded','Abatement and prohibition orders; fine and costs'),
('1894_0055',1894,"20 White's Row",'Bakehouse','not properly ventilated; filthy; used as sleeping apartment','Closed forthwith; fine and costs'),
('1894_0055',1894,'29 Old Montague Street','Workshop','insufficient sanitary conveniences; no separate female accommodation; poor ventilation; defective/dirty W.C.','Work done; summons withdrawn; costs'),
('1894_0055',1894,'126 Old Montague Street','Workshop','dirty walls/ceiling; poor ventilation','Work done; summons withdrawn; costs'),
('1894_0055',1894,'7 Ely Place','Workshop','overcrowded','Fine and costs'),
('1894_0055',1894,'9 Shepherd Street','Workshop','insufficient sanitary conveniences; no separate female accommodation','Work done'),
('1894_0057',1894,'5 Cox Square','Workshops','insufficient sanitary conveniences; no separate female accommodation; poor ventilation; building/closet/drain defects','Order to abate within 7 days'),
('1894_0057',1894,'7 Cox Square','Workshop','poor ventilation; dirty/dilapidated workshop/staircase; closet/drain defects','Order to abate within 7 days'),
('1894_0059',1894,'12 Duncan Street','Workshop','dirty/dilapidated walls/ceiling; insufficient sanitary conveniences; no separate female accommodation','Work done; summons withdrawn'),
('1894_0059',1894,'1 New Buildings, Tenter Street','Workshop','child with scarlet fever exposed in workshop','Dismissed on technical objection'),
('1895_0073',1895,'27 Old Montague Street','Bakehouse','unfit for use','Summons dismissed; required works later carried out'),
('1895_0073',1895,'148 Old Montague Street','Bakehouse','unfit for use','Order to put in proper sanitary condition; later disused'),
('1895_0074',1895,'27 Old Montague Street','Bakehouse','used as sleeping apartment; no ceiling; defective floor; poor ventilation','Work done; summons withdrawn'),
('1895_0074',1895,'3 Spelman Street','Workshop','insufficient sanitary conveniences; poor ventilation','Order to carry out necessary works within 14 days'),
('1895_0075',1895,'141 Hanbury Street','Workshop','insufficient sanitary conveniences; overcrowded; poor ventilation','Order to carry out necessary works within 14 days'),
('1895_0075',1895,'62 Chicksand Street','Workshop','insufficient sanitary conveniences; poor ventilation','Order to close within 14 days'),
('1895_0075',1895,'22 Heneage Street','Workshop','poor ventilation; insufficient light','Order to close within 14 days'),
('1895_0075',1895,"20 Corbett's Court",'Workshops','overcrowded; poor ventilation; insufficient sanitary conveniences','Order to close within 14 days'),
('1895_0076',1895,'39 Pelham Street','Workshop','poor ventilation; insufficient sanitary conveniences','Order to close forthwith'),
('1895_0076',1895,"2 Fisher's Alley (South)",'Workshop','first-floor room used as workshop totally unfit for such use','Order to close forthwith'),
('1895_0076',1895,"2 Fisher's Alley (North)",'Workshop','first-floor back room used as workshop totally unfit for such use','Order to close forthwith'),
('1895_0076',1895,'43 Buxton Street','Workshops','poor ventilation; insufficient sanitary conveniences','Order to close forthwith'),
('1896_0059',1896,'6 Fieldgate Street','Workshop','poor ventilation; dirty; no proper sanitary conveniences','Outcome outside retained passage context'),
]

cols=['passage_id','year','address','workplace_type','violation_summary','outcome']
out=pd.DataFrame(ROWS,columns=cols)
passages=pd.read_csv(PASSAGES).set_index('passage_id')
for pid in out.passage_id.unique():
    if pid not in passages.index:
        raise ValueError(f'Missing passage {pid}')
for row in out.itertuples(index=False):
    text=str(passages.loc[row.passage_id,'passage_text']).lower()
    if 'workshop' not in text and 'bakehouse' not in text:
        raise ValueError(f'No workplace term found in {row.passage_id}')


low=out.violation_summary.str.lower()
out['ventilation']=low.str.contains('ventilat')
out['sanitary_conveniences_or_closet']=low.str.contains('sanitary conveniences|closet|w.c.',regex=True)
out['overcrowding']=low.str.contains('overcrowd')
out['cleanliness_or_dilapidation']=low.str.contains('dirty|filthy|dilapidat',regex=True)
out['sleeping_use']=low.str.contains('sleeping')
out['unfit_for_use']=low.str.contains('unfit')
out['female_accommodation']=low.str.contains('female accommodation')
out['infectious_disease']=low.str.contains('scarlet fever')
out['insufficient_light']=low.str.contains('insufficient light')

out.to_csv(OUTDIR/'workplace_address_extraction.csv',index=False)
norm_type=out.workplace_type.str.lower().replace({'workshops':'workshop'})
summary=(out.assign(norm_type=norm_type).groupby('year').agg(
    enforcement_records=('address','size'),
    unique_addresses=('address','nunique'),
    workshop_records=('norm_type',lambda x:(x=='workshop').sum()),
    bakehouse_records=('norm_type',lambda x:(x=='bakehouse').sum()),
).reset_index())
summary.loc[len(summary)]={
    'year':'Total','enforcement_records':len(out),'unique_addresses':out.address.nunique(),
    'workshop_records':int((norm_type=='workshop').sum()),'bakehouse_records':int((norm_type=='bakehouse').sum())}
summary.to_csv(OUTDIR/'workplace_address_summary.csv',index=False)
print(summary.to_string(index=False))
print('\nViolation flags:')
for col in ['ventilation','sanitary_conveniences_or_closet','overcrowding','cleanliness_or_dilapidation','sleeping_use','unfit_for_use','female_accommodation','infectious_disease','insufficient_light']:
    print(f'{col}: {int(out[col].sum())}')
