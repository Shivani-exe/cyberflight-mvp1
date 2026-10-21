from dataclasses import dataclass
from cyberflight.llm.planner import fixed_plan


def simulate_events(events, escalation_minutes, buffer_minutes):
    if events.empty: return dict(stored=0, full=0, kept=0, attack_rows=0)
    a = events.alert_time
    mask = events.in_static_sample | ((events.time >= a - buffer_minutes * 60) & (events.time <= a + escalation_minutes * 60))
    return dict(stored=int(events.loc[mask,'rows'].sum()), full=int(events.rows.sum()), kept=int(events.loc[mask,'attacks'].sum()), attack_rows=int(events.attacks.sum()))


@dataclass
class Verdict:
    accepted: bool
    reason: str
    effective_plan: object


def validate_plan(plan, events, cluster_extra_row_cap, already_reserved=0):
    reason = ''
    if not 15 <= plan.escalation_minutes <= 720: reason = 'Escalation must be in [15, 720] minutes.'
    elif not 0 <= plan.buffer_minutes <= 120: reason = 'Buffer must be in [0, 120] minutes.'
    else:
        proposed = simulate_events(events, plan.escalation_minutes, plan.buffer_minutes)['stored']
        baseline = int(events.loc[events.in_static_sample,'rows'].sum())
        if already_reserved + proposed - baseline > cluster_extra_row_cap:
            reason = 'Per-cluster extra-row budget exceeded.'
    if reason: return Verdict(False, reason + ' Fixed policy fallback; proposals never change collection.', fixed_plan(reason))
    return Verdict(True, 'Accepted for simulation only; no collection is changed.', plan)
