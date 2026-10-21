import random
import numpy as np
import pandas as pd


def rule_fires(baseline, fanout):
    """Notebook rule uses add-one smoothing for the ratio."""
    return (fanout >= 5) & (((fanout + 1) / (baseline + 1) >= 5) | (fanout - baseline >= 6))


def static_sample(computers, seed=42):
    computers = sorted(set(computers))
    return set(random.Random(seed).sample(computers, round(.2 * len(computers))))


def streaming_alerts(rows, baselines):
    running, alerts = {}, {}
    for row in rows.itertuples(index=False):
        key = (row.cluster, row.src)
        running.setdefault(key, set()).add(row.dst)
        if key not in alerts and rule_fires(baselines.get(key, 0), len(running[key])):
            alerts[key] = row.time
    return alerts


def batch_alerts(rows, baselines):
    # First appearances of each destination reproduce streaming cumulative fanout.
    first = rows.sort_values('time', kind='stable').drop_duplicates(['cluster', 'src', 'dst']).copy()
    first['fanout_at_alert'] = first.groupby(['cluster', 'src'], observed=True).cumcount() + 1
    first['baseline_fanout'] = [baselines.get(k, 0) for k in zip(first.cluster, first.src)]
    fired = first[rule_fires(first.baseline_fanout, first.fanout_at_alert)]
    return fired.drop_duplicates(['cluster', 'src'])[['cluster', 'src', 'time', 'baseline_fanout', 'fanout_at_alert']]


def keep_mask(times, alert_times, sampled, escalation_minutes=480, buffer_minutes=90):
    return sampled | ((times >= alert_times - buffer_minutes * 60) & (times <= alert_times + escalation_minutes * 60))


def simulate(frame, escalation_minutes=480, buffer_minutes=90):
    keep = keep_mask(frame.time.to_numpy(), frame.alert_time.to_numpy(), frame.in_static_sample.to_numpy(), escalation_minutes, buffer_minutes)
    attack = frame.is_attack.to_numpy(dtype=bool)
    return {'stored': int(keep.sum()), 'full': len(frame), 'kept': int((keep & attack).sum()), 'attack_rows': int(attack.sum())}


def metrics(counts):
    return dict(counts, cost_pct=100 * counts['stored'] / max(counts['full'], 1), evidence_pct=100 * counts['kept'] / max(counts['attack_rows'], 1))
