"""Run locally with GEMINI_API_KEY. Cache genuine responses, never fabricate plans."""
from pathlib import Path
import sys
import os
import json
import random
import pandas as pd
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from cyberflight.llm.planner import AlertSummary, GeminiPlanner, make_client, discover_model,cache_name
from cyberflight.llm.validator import validate_plan,simulate_events


def main():
    load_dotenv(ROOT/'.env')
    if not os.getenv('GEMINI_API_KEY'): raise SystemExit('Set GEMINI_API_KEY locally before running.')
    client=make_client(os.environ['GEMINI_API_KEY'])
    try: model=discover_model(client)
    except Exception: raise SystemExit('Model discovery failed. Check local credentials or set GEMINI_MODEL.') from None
    planner=GeminiPlanner(client,model)
    alerts=pd.read_csv(ROOT/'app_data/alerts.csv')
    apparent_false=alerts[~alerts.is_attacker]
    chosen=set(random.Random(42).sample(list(apparent_false.index), min(40,len(apparent_false))))
    cohort=alerts[alerts.is_attacker | alerts.index.isin(chosen)].sort_values(['cluster','alert_time','computer'])
    budgets=pd.read_csv(ROOT/'app_data/budgets.csv').set_index('cluster').extra_row_cap.to_dict()
    directory=ROOT/'app_data/llm_cache';directory.mkdir(parents=True,exist_ok=True)
    records=[]; reservations={}; failures=0
    for _,r in cohort.iterrows():
        summary=AlertSummary(cluster=int(r.cluster),computer=str(r.computer),baseline_fanout=int(r.baseline_fanout),
            fanout_at_alert=int(r.fanout_at_alert),minutes_since_window_start=float(r.minutes_since_window_start),
            rows_so_far=int(r.rows_so_far),in_static_sample=bool(r.in_static_sample))
        plan,source=planner.propose(summary)
        if source=='live Gemini':
            (directory/cache_name(summary)).write_text(json.dumps(dict(summary=summary.model_dump(),plan=plan.model_dump(),model=model),indent=2),encoding='utf-8')
        else: failures+=1
        events=pd.read_parquet(ROOT/'app_data/timelines'/f'{summary.cluster}_{summary.computer}.parquet')
        verdict=validate_plan(plan,events,budgets[summary.cluster],reservations.get(summary.cluster,0))
        effective=verdict.effective_plan
        proposed=simulate_events(events,effective.escalation_minutes,effective.buffer_minutes)
        static=int(events.loc[events.in_static_sample,'rows'].sum())
        # Fallback also consumes the simulated budget, even if it exceeds the cap.
        reservations[summary.cluster]=reservations.get(summary.cluster,0)+proposed['stored']-static
        fixed=simulate_events(events,480,90)
        records.append(dict(cluster=summary.cluster,computer=summary.computer,is_attacker=bool(r.is_attacker),source=source,
            accepted=verdict.accepted,reason=verdict.reason,llm_stored=proposed['stored'],fixed_stored=fixed['stored'],
            llm_kept=proposed['kept'],fixed_kept=fixed['kept'],full=proposed['full'],attack_rows=proposed['attack_rows']))
    evaluation=pd.DataFrame(records)
    evaluation.to_csv(ROOT/'results/llm_vs_fixed.csv',index=False)
    better=failures==0 and evaluation.llm_stored.sum()<evaluation.fixed_stored.sum() and evaluation.llm_kept.sum()>=evaluation.fixed_kept.sum()
    report = ('Lower storage with no evidence loss in this selected cohort only.' if better else 'No demonstrated improvement over fixed policy. Present LLM as a triage/explanation assistant only.')
    (ROOT/'results/LLM_EVALUATION.md').write_text(report+f'\nFailed live requests: {failures}. Cohort: attacker alerts plus up to 40 apparent false alarms; not all computers.\n',encoding='utf-8')
    print(report)
    client.close()

if __name__=='__main__': main()
