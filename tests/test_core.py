import json
from pathlib import Path
import pandas as pd
import pytest
from cyberflight.core import rule_fires,streaming_alerts,batch_alerts,keep_mask


@pytest.mark.parametrize('b,w,expected',[(0,4,False),(0,5,True),(1,5,False),(1,7,True),(10,15,False),(10,16,True)])
def test_rule(b,w,expected): assert bool(rule_fires(b,w)) is expected


def test_streaming_matches_batch():
    rows=pd.DataFrame([dict(cluster=0,src='A',dst=f'D{i}',time=i) for i in range(8)]+[dict(cluster=0,src='B',dst='D',time=9)])
    baselines={(0,'A'):1}
    alerts=batch_alerts(rows,baselines)
    assert streaming_alerts(rows,baselines)=={(int(r.cluster),r.src):r.time for r in alerts.itertuples()}
    assert streaming_alerts(rows,baselines)=={(0,'A'):6}


def test_inclusive_window():
    import numpy as np
    assert keep_mask(np.array([0,1,2,3]),np.array([1,1,1,1]),np.array([False]*4),1/60,1/60).tolist()==[True,True,True,False]


def test_reference_reproduction():
    root=Path(__file__).resolve().parents[1]/'results'
    counts=pd.read_csv(root/'alert_counts.csv')
    assert counts.set_index('cluster').alerted_computers.to_dict()=={0:5,14:1252,21:45,28:385}
    p=pd.read_csv(root/'policy_pooled.csv').set_index('policy')
    assert round(p.loc['Adaptive','cost_pct'],1)==25.6
    assert (p.loc['Adaptive','kept'],p.loc['Adaptive','attack_rows'])==(164,168)
    assert round(p.loc['Static seed 42','cost_pct'],1)==21.4
    assert p.loc['Static seed 42','kept']==1
    assert all(json.loads((root/'reference_check.json').read_text()).values())
