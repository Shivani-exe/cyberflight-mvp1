import streamlit as st
import pandas as pd
import plotly.express as px
from common import csv
from cyberflight.evaluation import pooled_held_out
st.title('Cost versus evidence')
p = csv('policy_pooled.csv').copy()
variant = st.selectbox('Static variant',['Computer sample · seed 42','Computer sample · 40-seed mean','Row sample · seed 42'])
if 'mean' in variant:
    seeds=csv('static_seeds.csv'); r=seeds.mean(numeric_only=True)
    p.loc[p.policy=='Static seed 42', ['cost_pct','evidence_pct']] = [r.cost_pct,r.evidence_pct]
    p.loc[p.policy=='Static seed 42','policy']='Static 40-seed mean'
    st.caption(f'Computer-sample evidence range: {seeds.evidence_pct.min():.1f}%–{seeds.evidence_pct.max():.1f}%. Same retrospective windows.')
    st.caption(f'Computer-sample storage range: {seeds.cost_pct.min():.1f}%–{seeds.cost_pct.max():.1f}%.')
elif variant.startswith('Row'):
    r=csv('static_row_level.csv').iloc[0]
    p.loc[p.policy=='Static seed 42', ['cost_pct','evidence_pct']] = [r.cost_pct,r.evidence_pct]
    p.loc[p.policy=='Static seed 42','policy']='Static row-level'
st.plotly_chart(px.scatter(p,x='cost_pct',y='evidence_pct',color='policy',text='policy',range_x=[0,105],range_y=[0,105],labels={'cost_pct':'Rows stored (%)','evidence_pct':'Attack rows kept (%)'}),width='stretch')
st.dataframe(p[['policy','cost_pct','evidence_pct']],hide_index=True)
st.subheader('Escalation duration × pre-alert buffer')
grid=csv('policy_grid.csv')
metric=st.radio('Heatmap metric',['cost_pct','evidence_pct'],horizontal=True)
heatmap = grid.pivot(index='escalation_minutes',columns='buffer_minutes',values=metric).reindex([30,120,480,100000]).astype(float)
heatmap.index = ['30','120','480','until end']
fig = px.imshow(heatmap,text_auto='.1f',aspect='auto',labels={'x':'Buffer minutes','y':'Escalation minutes','color':metric})
fig.update_yaxes(type='category',categoryorder='array',categoryarray=['30','120','480','until end'],autorange='reversed')
st.plotly_chart(fig,width='stretch')
st.subheader('Held-out cluster evaluation')
st.caption('Each rule selects on three clusters and evaluates once on the named held-out cluster. This is a small retrospective split. Pooled totals sum counts before calculating percentages.')
left,right=st.columns(2)
with left:
    st.markdown('**Original pooled-training rule**')
    st.caption('Choose the cheapest policy reaching at least 95% pooled training evidence; if none qualify, maximize pooled training evidence. Existing tie-breaking is unchanged.')
    st.dataframe(pooled_held_out(csv('held_out.csv')),hide_index=True)
with right:
    st.markdown('**Equal training-cluster weights**')
    st.caption('Maximize mean per-cluster training evidence, then minimize mean per-cluster storage cost. Remaining ties use shorter escalation, then smaller buffer. Same candidate grid as the original rule.')
    st.dataframe(pooled_held_out(csv('held_out_equal_cluster.csv')),hide_index=True)
st.caption('C17693 is an attacker in every cluster, so these folds do not hold out attacker identity; cluster 21 also contains C19932.')
