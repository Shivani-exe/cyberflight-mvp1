"""Add equal-cluster held-out outputs; leave all existing result files untouched."""
from pathlib import Path
import sys
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cyberflight.core import static_sample, simulate, metrics
from cyberflight.evaluation import equal_cluster_folds


def main():
    rows = pd.read_parquet(ROOT / 'data/window_rows.parquet')
    alerts = pd.read_csv(ROOT / 'app_data/alerts.csv', usecols=['cluster', 'src', 'alert_time'])
    rows = rows.merge(alerts, on=['cluster', 'src'], how='left', validate='many_to_one')
    rows['in_static_sample'] = rows.src.isin(static_sample(rows.src))
    records = []
    for cluster, frame in rows.groupby('cluster'):
        for n in [30, 120, 480, 720]:
            for b in [0, 30, 90, 120]:
                records.append(dict(cluster=int(cluster), escalation_minutes=n, buffer_minutes=b,
                                    **metrics(simulate(frame, n, b))))
    grid = pd.DataFrame(records)
    grid.to_csv(ROOT / 'results/held_out_training_grid.csv', index=False)
    folds = equal_cluster_folds(grid)
    folds.to_csv(ROOT / 'results/held_out_equal_cluster.csv', index=False)
    print(folds.to_string(index=False), flush=True)


if __name__ == '__main__': main()
