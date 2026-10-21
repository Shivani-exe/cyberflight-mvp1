from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'app'))
import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title='CyberFlight', page_icon='✈️', layout='wide')
load_dotenv(ROOT / '.env')
import os
st.sidebar.title('✈ CyberFlight')
st.sidebar.caption('Keep the evidence. Control the cost.')
try: key = os.getenv('GEMINI_API_KEY') or st.secrets.get('GEMINI_API_KEY')
except Exception: key = os.getenv('GEMINI_API_KEY')
demo = st.sidebar.toggle('Demo mode (cached LLM)', value=not bool(key))
st.session_state['demo'] = demo
st.session_state['client'] = None
if key and not demo:
    @st.cache_resource(show_spinner=False)
    def connection(api_key):
        from cyberflight.llm.planner import make_client, discover_model
        client = make_client(api_key)
        return client, discover_model(client)
    try:
        client, default_model = connection(key)
        model = st.sidebar.text_input('Gemini model override', value=default_model)
        st.session_state['client'], st.session_state['model'] = client, model
    except Exception:
        st.sidebar.warning('Gemini unavailable. Cached/fixed fallback is active.')
elif not demo:
    st.sidebar.warning('Set GEMINI_API_KEY in the environment or local secrets.')
st.sidebar.caption('Proposals are simulated; collection is never changed.')
pages = [st.Page('pages/story.py',title='Story',default=True),
         st.Page('pages/comparison.py',title='Policy comparison'),
         st.Page('pages/timeline.py',title='Computer timeline'),
         st.Page('pages/triage.py',title='Alert triage'),
         st.Page('pages/ask.py',title='Ask the results'),
         st.Page('pages/limitations.py',title='Limitations')]
st.navigation(pages).run()
