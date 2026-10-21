"""Build compact app assets exclusively from the four supplied exports."""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cyberflight.core import batch_alerts, static_sample, simulate, metrics, keep_mask
from cyberflight.evaluation import equal_cluster_folds


def main():
    results, app = ROOT / 'results', ROOT / 'app_data'
    results.mkdir(exist_ok=True); app.mkdir(exist_ok=True)
    rows = pd.read_parquet(ROOT / 'data/window_rows.parquet')
    baseline = pd.read_parquet(ROOT / 'data/baseline_fanout.parquet')
    clusters = pd.read_csv(ROOT / 'data/clusters.csv').set_index('cluster')
    b = dict(zip(zip(baseline.cluster, baseline.src), baseline.baseline_fanout))
    alerts = batch_alerts(rows, b).rename(columns={'time': 'alert_time'})
    counts = alerts.groupby('cluster').size().to_dict()
    sample = static_sample(rows.src)
    rows = rows.merge(alerts[['cluster', 'src', 'alert_time']], on=['cluster', 'src'], how='left', validate='many_to_one')
    rows['in_static_sample'] = rows.src.isin(sample)
    comparisons = []
    for cluster, frame in rows.groupby('cluster', sort=True):
        total, attacks = len(frame), int(frame.is_attack.sum())
        static = frame.in_static_sample.to_numpy()
        comparisons += [dict(cluster=int(cluster), policy='Full', **metrics(dict(stored=total, full=total, kept=attacks, attack_rows=attacks))),
                        dict(cluster=int(cluster), policy='Static seed 42', **metrics(dict(stored=int(static.sum()), full=total, kept=int((static & frame.is_attack.to_numpy()).sum()), attack_rows=attacks))),
                        dict(cluster=int(cluster), policy='Adaptive', **metrics(simulate(frame))) ]
    per = pd.DataFrame(comparisons)
    pooled = per.groupby('policy', sort=False)[['stored','full','kept','attack_rows']].sum().reset_index()
    pooled['cost_pct'] = 100 * pooled.stored / pooled.full
    pooled['evidence_pct'] = 100 * pooled.kept / pooled.attack_rows
    per.to_csv(results / 'policy_by_cluster.csv', index=False)
    pooled.to_csv(results / 'policy_pooled.csv', index=False)
    alert_counts = pd.DataFrame([{'cluster': int(c), 'alerted_computers': int(n)} for c,n in counts.items()])
    alert_counts.to_csv(results / 'alert_counts.csv', index=False)
    adaptive = pooled.set_index('policy').loc['Adaptive']
    static = pooled.set_index('policy').loc['Static seed 42']
    checks = {'alert_counts': counts == {0:5,14:1252,21:45,28:385},
              'adaptive_cost': round(adaptive.cost_pct,1) == 25.6,
              'adaptive_kept': int(adaptive.kept) == 164,
              'attack_rows': int(adaptive.attack_rows) == 168,
              'static_cost': round(static.cost_pct,1) == 21.4,
              'static_kept': int(static.kept) == 1}
    checks = {key: bool(value) for key,value in checks.items()}
    (results / 'reference_check.json').write_text(json.dumps(checks, indent=2))
    print(pooled.to_string(index=False), flush=True)
    print('Reference checks:', checks, flush=True)
    if not all(checks.values()):
        raise SystemExit('STOP: supplied exports do not reproduce all reference numbers. See results/.')
    alerts['minutes_since_window_start'] = [(t-clusters.loc[c,'w_start'])/60 for c,t in zip(alerts.cluster, alerts.alert_time)]
    alerts['computer'] = alerts.src.astype(str)
    alerts['in_static_sample'] = alerts.src.isin(sample)
    # Counts at the exact first alert time, including simultaneous rows.
    prior = rows[rows.time <= rows.alert_time].groupby(['cluster','src'], observed=True).size()
    alerts['rows_so_far'] = [int(prior.get(k,0)) for k in zip(alerts.cluster, alerts.src)]
    attackers = set(zip(rows.loc[rows.is_attack,'cluster'], rows.loc[rows.is_attack,'src']))
    alerts['is_attacker'] = [k in attackers for k in zip(alerts.cluster, alerts.src)]
    alerts.to_csv(app / 'alerts.csv', index=False)
    # Aggregated per-second counts allow exact simulation without any log identifiers or destinations.
    events = rows.groupby(['cluster','src','time'], observed=True).agg(rows=('is_attack','size'), attacks=('is_attack','sum')).reset_index()
    events = events.merge(alerts[['cluster','src','alert_time','in_static_sample']], on=['cluster','src'], how='left')
    events['in_static_sample'] = events.src.isin(sample)
    timeline_dir = app / 'timelines'
    timeline_dir.mkdir(exist_ok=True)
    relevant = set(zip(alerts.cluster,alerts.src)) | attackers
    for (cluster,src), frame in events.groupby(['cluster','src'], observed=True):
        if (cluster,src) in relevant:
            frame = frame.copy()
            frame['src'] = frame.src.astype(str)
            frame.to_parquet(timeline_dir / f'{int(cluster)}_{src}.parquet', index=False)
    attacker_index = []
    for cluster,src in sorted(attackers):
        f = events[(events.cluster == cluster) & (events.src == src)]
        attack_times = f.loc[f.attacks > 0,'time']
        a = f.alert_time.iloc[0]
        attacker_index.append(dict(cluster=int(cluster),computer=str(src), attack_rows=int(f.attacks.sum()),
            first_attack=int(attack_times.min()),last_attack=int(attack_times.max()),alert_time=a,
            alert_delay_minutes=(a-attack_times.min())/60 if pd.notna(a) else None))
    pd.DataFrame(attacker_index).to_csv(app / 'attackers.csv', index=False)
    # An explicit simulation budget: 10% of the cluster's rows beyond static storage.
    pd.DataFrame([dict(cluster=int(c),extra_row_cap=int(len(f)*.1)) for c,f in rows.groupby('cluster')]).to_csv(app / 'budgets.csv',index=False)
    grid = []
    for n in [30,120,480,720,100000]:
        for buf in [0,30,90,120]:
            grid.append(dict(escalation_minutes=n, buffer_minutes=buf, **metrics(simulate(rows,n,buf))))
    pd.DataFrame(grid).to_csv(results / 'policy_grid.csv', index=False)
    # Computer-level multi-seed distribution, evaluated on the same windows.
    by_src = rows.groupby('src', observed=True).agg(full=('is_attack','size'), attack_rows=('is_attack','sum'))
    seeds = []
    for seed in range(40):
        chosen = by_src.loc[by_src.index.isin(static_sample(by_src.index,seed))]
        seeds.append(dict(seed=seed, **metrics(dict(stored=int(chosen.full.sum()), full=len(rows), kept=int(chosen.attack_rows.sum()), attack_rows=int(rows.is_attack.sum())))))
    pd.DataFrame(seeds).to_csv(results / 'static_seeds.csv', index=False)
    rng = np.random.default_rng(42)
    row_sample = rng.random(len(rows)) < .2
    pd.DataFrame([metrics(dict(stored=int(row_sample.sum()), full=len(rows), kept=int((row_sample & rows.is_attack.to_numpy()).sum()), attack_rows=int(rows.is_attack.sum()))) ]).to_csv(results / 'static_row_level.csv', index=False)
    # Choose on three clusters; evaluate the selected policy on the held-out fourth only.
    folds = []
    for held in clusters.index:
        train, test = rows[rows.cluster != held], rows[rows.cluster == held]
        candidates = []
        for n in [30,120,480,720]:
            for buf in [0,30,90,120]:
                m = metrics(simulate(train,n,buf)); candidates.append((m['evidence_pct'] >= 95, -m['cost_pct'] if m['evidence_pct'] >= 95 else m['evidence_pct'],n,buf))
        _,_,n,buf = max(candidates)
        folds.append(dict(held_out_cluster=int(held), escalation_minutes=n, buffer_minutes=buf, **metrics(simulate(test,n,buf))))
    pd.DataFrame(folds).to_csv(results / 'held_out.csv', index=False)
    # Add the equal-cluster rule separately; keep the original held-out selection unchanged.
    training_grid = []
    for cluster, frame in rows.groupby('cluster'):
        for n in [30,120,480,720]:
            for buf in [0,30,90,120]:
                training_grid.append(dict(cluster=int(cluster), escalation_minutes=n, buffer_minutes=buf,
                                          **metrics(simulate(frame,n,buf))))
    training_grid = pd.DataFrame(training_grid)
    training_grid.to_csv(results / 'held_out_training_grid.csv', index=False)
    equal_cluster_folds(training_grid).to_csv(results / 'held_out_equal_cluster.csv', index=False)
    (results / 'LIMITATIONS.md').write_text('''# Limitations

These are four selected, baseline-clean attack windows, not a prospective production trial. Costs count stored rows, not bytes or money. The static seed 42 result is one computer sample; see the multi-seed distribution and separate row-level sampling result.

The fanout ratio is add-one smoothed: (window + 1) / (baseline + 1). It misses repeated use of an existing edge, including the documented cluster 21 attack. Alert counts include many computers without labeled attack rows. Labels are incomplete ground truth, so these are apparent false alarms.

The fixed policy was selected using these windows. Held-out results select parameters on the other three clusters, then evaluate on the named held-out cluster; this small retrospective split does not establish deployment performance. Clusters may share computers.

The pre-alert buffer assumes a temporary local recorder exists. Resource limits, alert delivery delays, privacy, and recorder loss are not modeled. LLM plans are proposals only; deterministic validation and simulation do not authorize real collection. No evidence of LLM improvement is claimed before a live evaluation.
''', encoding='utf-8')
    print('Compact assets built.', flush=True)

if __name__ == '__main__': main()
