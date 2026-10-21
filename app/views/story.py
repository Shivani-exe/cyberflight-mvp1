import streamlit as st
from common import records
st.title('A flight recorder for authentication logs')
st.write('Storing every authentication event is expensive. A fixed sample saves space but can discard the very events an investigator needs. CyberFlight keeps a baseline sample, then temporarily stores all events for a suspicious computer, including a pre-alert buffer.')
p = {r['policy']:r for r in records('policy_pooled.csv')}
a = p['Adaptive']
c1,c2,c3 = st.columns(3)
c1.metric('Adaptive storage',f"{float(a['cost_pct']):.1f}% of rows")
c2.metric('Attack evidence kept',f"{a['kept']} / {a['attack_rows']} rows")
c3.metric('Static sample evidence',f"{p['Static seed 42']['kept']} rows")
st.warning('Retrospective results from four selected attack windows. The fixed policy was tuned on these windows. This is row retention, not measured dollar savings or production detection performance.')
st.subheader('What triggers the recorder?')
st.write('A computer reaches at least five unique destinations, and either its add-one-smoothed fanout ratio reaches five or it reaches six more destinations than its baseline. On its first alert, full collection lasts eight hours, with a ninety-minute buffer.')
st.code('Exported windows → fanout alerts → retention simulation → result tables → Streamlit\nStructured alert → Gemini proposal → independent validator → comparison only',language=None)
st.info('The LLM is an explanation and triage assistant. No demonstrated improvement over the fixed policy is claimed. Missing cached responses are clearly labeled fixed-policy fallbacks.')
