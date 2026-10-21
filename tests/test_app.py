"""Offline UI regressions: no credentials or live API requests."""
import json
import hashlib
from pathlib import Path
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest
from cyberflight.llm.qa import REFUSAL
from cyberflight.evaluation import pooled_held_out, equal_cluster_folds

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def app(monkeypatch):
    import dotenv
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *a, **k: None)
    monkeypatch.setattr(st, 'secrets', {})
    return AppTest.from_file(str(ROOT/'app/streamlit_app.py'), default_timeout=60).run()


@pytest.mark.parametrize('page', ['story','comparison','timeline','triage','ask','limitations'])
def test_six_pages(app, page):
    app.switch_page(f'views/{page}.py').run()
    assert not app.exception


def test_explicit_navigation_avoids_legacy_page_autodiscovery():
    # A fresh deep link must bootstrap the entrypoint before rendering a view.
    assert not (ROOT/'app/pages').exists()
    assert (ROOT/'app/views/story.py').exists()


def select(app, label):
    return next(w for w in app.selectbox if w.label == label)


def test_triage_default_filter_and_na(app):
    app.switch_page('views/triage.py').run()
    assert select(app, 'Cluster').value == 14
    assert select(app, 'Computer').value == 'C17693'
    assert app.radio[0].value == 'Attacker alerts'
    app.radio[0].set_value('False alarms').run()
    assert select(app, 'Computer').value != 'C17693'
    app.button[0].click().run()
    assert not app.exception
    assert any('No live Gemini plan was received' in item.value for item in app.warning)
    effect = app.dataframe[0].value
    assert (effect.attack_rows == 0).all()
    assert (effect.evidence_pct == 'n/a').all()
    assert (effect.kept == 'n/a').all()
    app.radio[0].set_value('All').run()
    assert not app.exception
    assert 'C17693' in select(app, 'Computer').options


def test_comparison_heatmap_variants_and_totals(app):
    app.switch_page('views/comparison.py').run()
    assert len(select(app, 'Static variant').options) == 3
    for option in select(app, 'Static variant').options:
        select(app, 'Static variant').set_value(option).run()
        assert not app.exception
    for metric in ['cost_pct','evidence_pct']:
        app.radio[0].set_value(metric).run()
        heatmap = json.loads(app.get('plotly_chart')[1].proto.spec)
        assert heatmap['layout']['yaxis']['type'] == 'category'
        assert heatmap['layout']['yaxis']['categoryarray'] == ['30','120','480','until end']
        assert heatmap['data'][0]['y'] == ['30','120','480','until end']
    for table, file in zip(app.dataframe[1:], ['held_out.csv','held_out_equal_cluster.csv']):
        original = pd.read_csv(ROOT/'results'/file)
        total = table.value.iloc[-1]
        assert total.held_out_cluster == 'Pooled total'
        for field in ['kept','attack_rows','stored','full']:
            assert total[field] == original[field].sum()
        assert total.evidence_pct == pytest.approx(100*original.kept.sum()/original.attack_rows.sum())


def test_timeline_cumulative_and_no_overlapping_annotations(app):
    app.switch_page('views/timeline.py').run()
    chart=json.loads(app.get('plotly_chart')[0].proto.spec)
    assert all(trace['type']=='scatter' and trace['mode']=='lines' for trace in chart['data'])
    assert not chart['layout'].get('annotations')
    assert chart['data'][1]['yaxis']=='y2'


def test_ask_results_refuses_unsupported_question(app):
    app.switch_page('views/ask.py').run()
    app.text_input[0].set_value('What is the price of a flight to Mars?').run()
    app.button[0].click().run()
    assert not app.exception
    assert any(w.value == REFUSAL for w in app.markdown)


def test_original_numbers_and_honest_pages_unchanged():
    original=json.loads((ROOT/'tests/original_results_sha256.json').read_text())
    for path, expected in original.items():
        # The baseline manifest was captured on Windows; resolve it on Linux too.
        portable_path = path.replace('\\', '/').replace('app/pages/', 'app/views/')
        assert hashlib.sha256((ROOT/portable_path).read_bytes()).hexdigest() == expected, path


def test_equal_rule_uses_cluster_means_and_cost_tiebreak():
    # Unequal cluster sizes make pooled evidence prefer A but equal weights prefer B.
    rows=[]
    for cluster, full, attacks, kept_a, kept_b in [(0,1000,100,100,80),(1,10,1,0,1),(2,10,1,0,1),(3,10,1,0,1)]:
        for n,kept,stored in [(30,kept_a,full//2),(120,kept_b,full//2),(480,kept_b,full//3)]:
            rows.append(dict(cluster=cluster,escalation_minutes=n,buffer_minutes=0,stored=stored,full=full,
                             kept=kept,attack_rows=attacks,evidence_pct=100*kept/attacks,cost_pct=100*stored/full))
    folds=equal_cluster_folds(pd.DataFrame(rows))
    assert (folds.escalation_minutes == 480).all()
    # Altering a held-out cluster's labels cannot influence its chosen parameters.
    changed=pd.DataFrame(rows)
    changed.loc[changed.cluster==0,'evidence_pct']=0
    altered=equal_cluster_folds(changed)
    assert folds.iloc[0].escalation_minutes == altered.iloc[0].escalation_minutes
