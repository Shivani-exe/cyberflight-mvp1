from pathlib import Path
import streamlit as st
ROOT = Path(__file__).resolve().parents[1]


@st.cache_data(show_spinner=False)
def csv(name, area='results'):
    import pandas as pd
    return pd.read_csv(ROOT / area / name)


@st.cache_data(show_spinner=False)
def records(name):
    import csv as csv_module
    with (ROOT/'results'/name).open(encoding='utf-8',newline='') as handle:
        return list(csv_module.DictReader(handle))


@st.cache_data(show_spinner=False)
def text(name): return (ROOT / 'results' / name).read_text(encoding='utf-8')


@st.cache_data(show_spinner=False)
def timeline(cluster, computer):
    import pandas as pd
    # Selectors only pass identifiers read from the pipeline index.
    path = ROOT / 'app_data/timelines' / f'{int(cluster)}_{computer}.parquet'
    if path.resolve().parent != (ROOT / 'app_data/timelines').resolve(): raise ValueError('Invalid computer')
    return pd.read_parquet(path)


def summary(row):
    from cyberflight.llm.planner import AlertSummary
    return AlertSummary(cluster=int(row.cluster),computer=str(row.computer),baseline_fanout=int(row.baseline_fanout),
        fanout_at_alert=int(row.fanout_at_alert),minutes_since_window_start=float(row.minutes_since_window_start),
        rows_so_far=int(row.rows_so_far),in_static_sample=bool(row.in_static_sample))


def choose(frame, preferred_cluster=None, preferred_computer=None, key_prefix='selection'):
    clusters = sorted(frame.cluster.unique())
    cluster_key, computer_key = key_prefix + '_cluster', key_prefix + '_computer'
    if st.session_state.get(cluster_key) not in clusters:
        st.session_state[cluster_key] = preferred_cluster if preferred_cluster in clusters else clusters[0]
    cluster = st.selectbox('Cluster', clusters, key=cluster_key)
    selected = frame[frame.cluster == cluster]
    computers = selected.computer.tolist()
    if st.session_state.get(computer_key) not in computers:
        st.session_state[computer_key] = preferred_computer if preferred_computer in computers else computers[0]
    computer = st.selectbox('Computer', computers, key=computer_key)
    return selected[selected.computer == computer].iloc[0]
