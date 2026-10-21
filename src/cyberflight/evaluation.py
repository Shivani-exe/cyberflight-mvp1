"""Additional held-out evaluation without changing the original rule or results."""
import pandas as pd
from cyberflight.core import metrics


def equal_cluster_folds(grid):
    folds = []
    for held in sorted(grid.cluster.unique()):
        train = grid[grid.cluster != held]
        scores = train.groupby(['escalation_minutes', 'buffer_minutes'], as_index=False).agg(
            mean_evidence=('evidence_pct', 'mean'), mean_cost=('cost_pct', 'mean'))
        best = scores.sort_values(['mean_evidence', 'mean_cost', 'escalation_minutes', 'buffer_minutes'],
                                  ascending=[False, True, True, True], kind='stable').iloc[0]
        test = grid[(grid.cluster == held) & (grid.escalation_minutes == best.escalation_minutes)
                    & (grid.buffer_minutes == best.buffer_minutes)].iloc[0]
        folds.append(dict(held_out_cluster=int(held), escalation_minutes=int(best.escalation_minutes),
                          buffer_minutes=int(best.buffer_minutes), **metrics({
                              k: int(test[k]) for k in ['stored', 'full', 'kept', 'attack_rows']})))
    return pd.DataFrame(folds)


def pooled_held_out(frame):
    """Pool counts first; percentages use pooled denominators, never averaged rates."""
    counts = {k: int(frame[k].sum()) for k in ['stored', 'full', 'kept', 'attack_rows']}
    total = dict(held_out_cluster='Pooled total', escalation_minutes=None, buffer_minutes=None, **metrics(counts))
    result = frame.copy()
    result['held_out_cluster'] = result.held_out_cluster.astype(str)
    return pd.concat([result, pd.DataFrame([total])], ignore_index=True)
