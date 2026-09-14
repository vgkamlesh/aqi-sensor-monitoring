"""
Runs the trained GAT+GRU checkpoint over the data and exports predictions
as a plain CSV the Java alerting service can read -- this is the ONLY
handoff between the two halves of the pipeline. The Java side never
touches PyTorch; it just reads timestamp,station,unhealthy rows.

IMPORTANT: this runs at true HOURLY cadence (not the training STRIDE=24),
and skips writing a row whenever the station's RAW reading that hour was
missing (dropout). Two earlier versions of this script got this wrong:
  v1 exported one row every 24h (matching training stride) -- meant every
     consecutive row was ~24h apart by construction, so Java's dropout
     detector (fires on 4+ hour gaps) fired on almost every single row,
     regardless of whether the station was actually offline.
  v2 would have used the FILLED (ffill/bfill-imputed) values for every
     hour -- meaning a row would ALWAYS be emitted even during a real
     dropout, so the dropout rule could never fire at all.
This version fixes both: dense hourly rows, but only where real data
existed, so gaps in the CSV correspond to genuine dropouts.

Usage:
    python src/export_predictions.py
"""

import pandas as pd
import torch

from train_models import GATGRU, load_data, SEQ_LEN

CHECKPOINT_PATH = "processed_data/gat_gru_model.pt"
RAW_WIDE_PATH = "processed_data/combined_wide.csv"
OUT_PATH = "processed_data/predictions.csv"


def main():
    print("Loading data and checkpoint...")
    station_order, edge_index, wide_normalized, labels = load_data()
    # Raw (unfilled) data -- needed to know which hours were REAL vs imputed.
    raw_wide = pd.read_csv(RAW_WIDE_PATH, index_col=0)[station_order]

    checkpoint = torch.load(CHECKPOINT_PATH, weights_only=False)
    model = GATGRU()
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    print(f"Loaded checkpoint (best val F1 during training: {checkpoint.get('best_val_f1', 'n/a')})")

    timestamps = wide_normalized.index.tolist()
    n = len(timestamps)
    rows = []

    print(f"Running hourly inference over {n - SEQ_LEN + 1} timestamps "
          f"(this is denser than training -- may take a few minutes)...")

    with torch.no_grad():
        for i, end in enumerate(range(SEQ_LEN - 1, n)):
            start = end - SEQ_LEN + 1
            x_window = wide_normalized.values[start:end + 1]
            x_seq = torch.tensor(x_window, dtype=torch.float).unsqueeze(-1)
            logits = model(x_seq, edge_index)
            preds = (torch.sigmoid(logits) > 0.5).int().tolist()

            ts = timestamps[end]
            raw_row = raw_wide.iloc[end]
            for station, pred in zip(station_order, preds):
                if pd.isna(raw_row[station]):
                    continue  # real dropout hour -- skip the row entirely, let the gap show
                rows.append({"timestamp": ts, "station": station, "unhealthy": pred})

            if (i + 1) % 5000 == 0:
                print(f"  {i + 1}/{n - SEQ_LEN + 1} timestamps processed")

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(out_df)} predictions -> {OUT_PATH}")
    print(f"Predicted unhealthy rate: {out_df['unhealthy'].mean()*100:.2f}%")


if __name__ == "__main__":
    main()
