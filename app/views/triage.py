import streamlit as st
from common import ROOT,csv,choose,timeline,summary
from cyberflight.core import metrics
from cyberflight.llm.planner import CachedPlanner,GeminiPlanner
from cyberflight.llm.validator import validate_plan,simulate_events
st.title('Alert triage · proposal and simulation')
alerts=csv('alerts.csv','app_data')
alert_filter=st.radio('Alert filter',['Attacker alerts','False alarms','All'],horizontal=True)
if alert_filter=='Attacker alerts': alerts=alerts[alerts.is_attacker]
elif alert_filter=='False alarms':
    alerts=alerts[~alerts.is_attacker]
    st.caption('False alarms means alerts without labeled attack rows; ground-truth labels may be incomplete.')
if alerts.empty:
    st.info('No alerts match this filter.'); st.stop()
r=choose(alerts,preferred_cluster=14,preferred_computer='C17693',key_prefix='triage')
s=summary(r)
st.subheader('Structured alert summary')
st.json(s.model_dump())
if st.session_state.get('client'):
    st.caption('Live Gemini is configured. Click Review plan to request a proposal; generation can take up to a minute per attempt.')
else:
    st.caption('Cached/fixed mode is active. To request a live proposal, turn off Demo mode and check the sidebar connection status.')
if st.button('Review plan',type='primary'):
    client=st.session_state.get('client')
    planner=GeminiPlanner(client,st.session_state['model']) if client else CachedPlanner(ROOT/'app_data/llm_cache')
    with st.spinner('Preparing proposal…'): plan,source=planner.propose(s)
    events=timeline(r.cluster,r.computer)
    budget=int(csv('budgets.csv','app_data').set_index('cluster').loc[int(r.cluster),'extra_row_cap'])
    verdict=validate_plan(plan,events,budget)
    st.caption('Source: '+source)
    if source=='fallback':
        st.warning('No live Gemini plan was received. Showing the fixed policy instead. ' + plan.rationale)
    st.json(plan.model_dump())
    (st.success if verdict.accepted else st.warning)(verdict.reason)
    st.caption(f'Per-cluster simulation cap: {budget:,} extra rows over static. This isolated review assumes no prior reservations. Offline evaluation tracks cumulative reservations.')
    effective=verdict.effective_plan
    import pandas as pd
    comparison=pd.DataFrame([dict(policy='Proposed / effective fallback',**metrics(simulate_events(events,effective.escalation_minutes,effective.buffer_minutes))),dict(policy='Fixed policy',**metrics(simulate_events(events,480,90)))])
    display=comparison.copy()
    for column in ['kept','evidence_pct']:
        display[column]=display[column].astype(object)
        display.loc[display.attack_rows==0,column]='n/a'
    st.dataframe(display,hide_index=True)
    if (comparison.attack_rows==0).any(): st.caption('Attack evidence is n/a when there are no labeled attack rows; attack_rows remains the observed count.')
    if not verdict.accepted: st.caption('The fallback is the fixed baseline, reported even if that baseline exceeds the proposal cap; no collection is authorized.')
st.subheader('Offline LLM evaluation')
st.caption('This separate batch evaluation is not required for the live Review plan button above.')
if (ROOT/'results/llm_vs_fixed.csv').exists():
    evaluation=csv('llm_vs_fixed.csv');st.dataframe(evaluation,hide_index=True)
    st.info('Inspect cost and evidence together. No general improvement claim is made from this selected alert cohort.')
else: st.info('Not run. No precomputed Gemini plans were supplied. Run scripts/build_llm_cache.py locally with your key. LLM improvement is untested.')
