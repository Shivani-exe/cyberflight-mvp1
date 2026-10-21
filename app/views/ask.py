import streamlit as st
from common import ROOT,csv,text
from cyberflight.llm.qa import answer
st.title('Ask the results')
st.write('Answers cite table names and return source cells. Unsupported numbers are refused; raw authentication rows are never sent.')
q=st.text_input('Question',placeholder='Compare adaptive and static storage cost and evidence')
if st.button('Find evidence') and q:
    tables={p.name:csv(p.name) for p in sorted((ROOT/'results').glob('*.csv'))}
    with st.spinner('Retrieving evidence…'):
        response=answer(q,tables,text('LIMITATIONS.md'),st.session_state.get('client'),st.session_state.get('model'))
    st.write(response)
    if not st.session_state.get('client'): st.caption('Offline table retrieval; no Gemini call was made.')
