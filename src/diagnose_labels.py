"""
Diagnostic: shows how much EACH rule (dropout / stuck / outlier) contributes
to the unhealthy label, per station, so we can see which threshold is
miscalibrated before trusting the combined label.

Usage:
    python src/diagnose_labels.py
"""

import pandas as pd
import numpy as np

WIDE_DATA_PATH = "processed_data/combined_wide.csv"

STUCK_THRESHOLD = 6
DROPOUT_THRESHOLD = 4
ZSCORE_THRESHOLD = 3.0
ROLLING_WINDOW = 24 * 7


def flag_dropout(series):
    is_missing = series.isna()
    streak = is_missing.groupby((~is_missing).cumsum()).cumsum()
    return (streak >= DROPOUT_THRESHOLD) & is_missing


def flag_stuck(series):
    same_as_prev = series.eq(series.shift())
    streak = same_as_prev.groupby((~same_as_prev).cumsum()).cumsum()
    return streak >= (STUCK_THRESHOLD - 1)


def flag_outlier(series):
    rolling_mean = series.rolling(ROLLING_WINDOW, min_periods=24).mean()
    rolling_std = series.rolling(ROLLING_WINDOW, min_periods=24).std()
    z = (series - rolling_mean) / rolling_std.replace(0, np.nan)
    return z.abs() > ZSCORE_THRESHOLD


def main():
    wide = pd.read_csv(WIDE_DATA_PATH, index_col=0)

    print(f"{'station':45s} {'dropout%':>9s} {'stuck%':>8s} {'outlier%':>9s}  longest_stuck_run")
    for station in wide.columns:
        series = wide[station]
        n = len(series)

        dropout = flag_dropout(series)
        stuck = flag_stuck(series).fillna(False)
        outlier = flag_outlier(series).fillna(False)

        # longest run of identical consecutive values, for context
        same_as_prev = series.eq(series.shift())
        run_lengths = same_as_prev.groupby((~same_as_prev).cumsum()).cumsum()
        longest_run = int(run_lengths.max()) + 1 if len(run_lengths) else 0

        print(f"{station:45s} {100*dropout.sum()/n:8.1f}% {100*stuck.sum()/n:7.1f}% "
              f"{100*outlier.sum()/n:8.1f}%  {longest_run}")


if __name__ == "__main__":
    main()
