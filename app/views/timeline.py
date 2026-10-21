import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from common import csv, choose, timeline
st.title('Computer timeline')
r=choose(csv('attackers.csv','app_data'),key_prefix='timeline')
f=timeline(r.cluster,r.computer)
origin=float(f.time.min())
fig=go.Figure()
f=f.sort_values('time')
fig.add_trace(go.Scatter(x=(f.time-origin)/60,y=f.rows.cumsum(),name='All rows (cumulative)',mode='lines'))
fig.add_trace(go.Scatter(x=(f.time-origin)/60,y=f.attacks.cumsum(),name='Attack rows (cumulative)',mode='lines',yaxis='y2'))
if pd.notna(r.alert_time):
    a=(r.alert_time-origin)/60
    fig.add_vrect(x0=a-90,x1=a,fillcolor='orange',opacity=.15,line_width=0)
    fig.add_vrect(x0=a,x1=a+480,fillcolor='teal',opacity=.1,line_width=0)
    fig.add_vline(x=a,line_dash='dash')
    st.caption('Orange shading: pre-alert buffer · Teal shading: escalation · Dashed line: first alert')
    st.metric('Alert relative to first attack',f'{r.alert_delay_minutes:.2f} minutes')
else: st.warning('No fanout alert for this attacker. Only the static sample can retain its evidence.')
fig.update_layout(xaxis_title='Minutes since this computer’s first exported row',yaxis_title='Cumulative rows',
    yaxis2=dict(title='Cumulative attack rows',overlaying='y',side='right',rangemode='tozero'),
    legend=dict(orientation='h',y=1.12,x=0),margin=dict(t=80,r=70))
st.plotly_chart(fig,width='stretch')
st.caption('Attack labels are used only for retrospective evaluation and are never included in planner input.')
