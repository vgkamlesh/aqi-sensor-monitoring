"""
Generates binary healthy(0) / unhealthy(1) labels per station per timestamp,
for the GAT+GRU MODEL TARGET ONLY -- stuck-value and outlier rules.

Dropout is deliberately NOT included here: a missing reading has no feature
vector to predict from and is trivially detectable without ML (the row is
empty). Dropout is handled separately as a direct rule check in the
alerting layer. See docs/health_definition.md for the reasoning.

Rules (from docs/health_definition.md):
  - stuck value: 6+ identical consecutive hourly readings -> unhealthy
  - outlier: |z-score| > 3 vs that station's own 7-day (168hr) rolling window -> unhealthy

Output: processed_data/labels_wide.csv -- same shape as combined_wide.csv.
        1 = unhealthy, 0 = healthy, NaN = no reading (dropout hour, excluded
        from model training -- filter these out when building sequences).

Usage:
    python src/generate_labels.py
"""

import pandas as pd
import numpy as np

WIDE_DATA_PATH = "processed_data/combined_wide.csv"
OUT_PATH = "processed_data/labels_wide.csv"

STUCK_THRESHOLD = 6
ZSCORE_THRESHOLD = 3.0
ROLLING_WINDOW = 24 * 7


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
    labels = pd.DataFrame(index=wide.index, columns=wide.columns, dtype=float)

    for station in wide.columns:
        series = wide[station]

        stuck = flag_stuck(series).fillna(False)
        outlier = flag_outlier(series).fillna(False)

        unhealthy = (stuck | outlier).astype(float)
        unhealthy[series.isna()] = np.nan  # no reading -> no label, excluded from training

        labels[station] = unhealthy

        n_unhealthy = int((labels[station] == 1).sum())
        n_total = int(labels[station].notna().sum())
        pct = 100 * n_unhealthy / n_total if n_total else 0
        print(f"{station:45s} unhealthy: {n_unhealthy:6d} / {n_total:6d} labeled hours ({pct:.1f}%)")

    labels.to_csv(OUT_PATH)
    print(f"\nSaved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
