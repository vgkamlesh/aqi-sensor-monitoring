"""
Runs the trained GAT+GRU checkpoint over the data and exports predictions
as a plain CSV the Java alerting service can read -- this is the ONLY
handoff between the two halves of the pipeline. The Java side never
touches PyTorch; it just reads timestamp,station,unhealthy rows.

Usage:
    python src/export_predictions.py
"""

import pandas as pd
import torch

from train_models import GATGRU, load_data, SEQ_LEN, STRIDE

CHECKPOINT_PATH = "processed_data/gat_gru_model.pt"
OUT_PATH = "processed_data/predictions.csv"


def main():
    print("Loading data and checkpoint...")
    station_order, edge_index, wide_normalized, labels = load_data()
    checkpoint = torch.load(CHECKPOINT_PATH, weights_only=False)

    model = GATGRU()
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    print(f"Loaded checkpoint (best val F1 during training: {checkpoint.get('best_val_f1', 'n/a')})")

    timestamps = wide_normalized.index.tolist()
    rows = []

    with torch.no_grad():
        for end in range(SEQ_LEN - 1, len(wide_normalized), STRIDE):
            start = end - SEQ_LEN + 1
            x_window = wide_normalized.values[start:end + 1]
            x_seq = torch.tensor(x_window, dtype=torch.float).unsqueeze(-1)
            logits = model(x_seq, edge_index)
            preds = (torch.sigmoid(logits) > 0.5).int().tolist()
            ts = timestamps[end]
            for station, pred in zip(station_order, preds):
                rows.append({"timestamp": ts, "station": station, "unhealthy": pred})

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(out_df)} predictions -> {OUT_PATH}")
    print(f"Predicted unhealthy rate: {out_df['unhealthy'].mean()*100:.2f}%")


if __name__ == "__main__":
    main()
