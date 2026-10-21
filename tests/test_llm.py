from types import SimpleNamespace
from unittest.mock import Mock
import pandas as pd
import pytest
from pydantic import ValidationError
from cyberflight.llm.planner import Plan,AlertSummary,GeminiPlanner,CachedPlanner,fixed_plan
from cyberflight.llm.validator import validate_plan
from cyberflight.llm.qa import Selection,Citation,render_selection,answer,REFUSAL
from cyberflight.llm.planner import provider_schema, failure_reason


def events():
    return pd.DataFrame(dict(time=[0,60,120],alert_time=[60]*3,in_static_sample=[False]*3,rows=[10]*3,attacks=[0,1,0]))


@pytest.mark.parametrize('n,b,accepted',[(15,0,True),(720,120,True),(14,0,False),(721,0,False),(15,-1,False),(15,121,False)])
def test_validator_bounds(n,b,accepted):
    p=Plan(escalation_minutes=n,buffer_minutes=b,risk_level='low',rationale='test')
    assert validate_plan(p,events(),100).accepted is accepted


def test_budget_and_reservations():
    assert not validate_plan(fixed_plan(),events(),29).accepted
    assert not validate_plan(fixed_plan(),events(),40,already_reserved=11).accepted


def summary(): return AlertSummary(cluster=0,computer='A',baseline_fanout=0,fanout_at_alert=5,minutes_since_window_start=1.,rows_so_far=5,in_static_sample=False)


def test_schema_mocked_planner():
    client=Mock()
    client.models.generate_content.return_value=SimpleNamespace(text=fixed_plan().model_dump_json())
    plan,source=GeminiPlanner(client,'test-model').propose(summary())
    assert source=='live Gemini' and plan.escalation_minutes==480
    config=client.models.generate_content.call_args.kwargs['config']
    assert config.response_mime_type=='application/json'
    client.models.generate_content.side_effect=RuntimeError('provider error')
    assert GeminiPlanner(client,'test-model').propose(summary())[1]=='fallback'
    assert client.models.generate_content.call_count==3
    with pytest.raises(ValidationError): Plan(escalation_minutes='15',buffer_minutes=0,risk_level='high',rationale='x')


def test_cache_fallback(tmp_path): assert CachedPlanner(tmp_path).propose(summary())[1]=='fallback'


def test_provider_schema_preserves_local_strictness():
    import json
    assert 'additionalProperties' not in json.dumps(provider_schema(Plan))
    assert 'additionalProperties' not in json.dumps(provider_schema(Selection))
    assert provider_schema(Plan)['properties']['risk_level']['enum'] == ['low','medium','high']
    with pytest.raises(ValidationError):
        Plan.model_validate(dict(escalation_minutes=30,buffer_minutes=0,risk_level='low',rationale='test',unexpected=True))


def test_safe_provider_errors():
    assert 'overloaded' in failure_reason(SimpleNamespace(code=503))
    assert 'deadline' in failure_reason(SimpleNamespace(code=504))


def test_grounded_qa_refuses_unknown():
    tables={'policy_pooled.csv':pd.DataFrame([dict(policy='Adaptive',kept=164)])}
    assert answer('What is the price of a flight?',tables,'')==REFUSAL
    assert answer('Predict adaptive cost next year',tables,'')==REFUSAL
    assert answer('What is static cost in 2028?',tables,'')==REFUSAL
    assert render_selection(Selection(supported=True,citations=[Citation(table='invented.csv',row=0,columns=['kept'])]),tables)==REFUSAL
    assert render_selection(Selection(supported=True,citations=[Citation(table='policy_pooled.csv',row=9,columns=['kept'])]),tables)==REFUSAL
    assert render_selection(Selection(supported=True,citations=[Citation(table='policy_pooled.csv',row=0,columns=['made_up'])]),tables)==REFUSAL
    result=render_selection(Selection(supported=True,citations=[Citation(table='policy_pooled.csv',row=0,columns=['kept'])]),tables)
    assert 'policy_pooled.csv' in result and '164' in result
