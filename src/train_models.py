"""
GAT+GRU model: for each 24-hour window, a shared GAT layer encodes the
station graph at every hour in the window, then a GRU consumes each
station's sequence of embeddings over time and predicts whether that
station is unhealthy (stuck/outlier) at the final hour of the window.

Train/val split is by TIME (last 20% of timestamps held out), not random,
to avoid leaking future info into training -- standard for time series.

Usage:
    python src/train_model.py
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch_geometric.nn import GATConv

WIDE_DATA_PATH = "processed_data/combined_wide.csv"
LABELS_PATH = "processed_data/labels_wide.csv"
NODES_PATH = "processed_data/station_nodes.csv"
EDGES_PATH = "processed_data/station_graph.csv"
CHECKPOINT_PATH = "processed_data/gat_gru_model.pt"

SEQ_LEN = 24       # hours of history per window
STRIDE = 24        # step between windows (non-overlapping -- cuts window count ~4x vs STRIDE=6)
GAT_OUT = 8
GAT_HEADS = 4
GRU_HIDDEN = 32
EPOCHS = 3
LR = 1e-3
VAL_FRACTION = 0.2
POS_WEIGHT = 20.0  # pos_weight=50 overcorrected (precision collapsed); 20 is a middle ground -- tune further based on results


class GATGRU(nn.Module):
    def __init__(self, gat_out=GAT_OUT, gat_heads=GAT_HEADS, gru_hidden=GRU_HIDDEN):
        super().__init__()
        self.gat = GATConv(in_channels=1, out_channels=gat_out, heads=gat_heads)
        self.gru = nn.GRU(input_size=gat_out * gat_heads, hidden_size=gru_hidden, batch_first=True)
        self.classifier = nn.Linear(gru_hidden, 1)

    def forward(self, x_seq, edge_index):
        # x_seq: (SEQ_LEN, n_stations, 1)
        # Instead of looping SEQ_LEN times (slow: 24 separate Python-level GAT
        # calls per window), batch all SEQ_LEN hourly graphs into one big
        # disconnected graph (block-diagonal adjacency) and call GAT ONCE.
        # Each hour's nodes only connect to that same hour's nodes (offset
        # index ranges), so this is mathematically identical to the loop
        # version -- just one tensor op instead of 24.
        seq_len, n_stations, _ = x_seq.shape
        x_flat = x_seq.reshape(seq_len * n_stations, 1)

        offsets = (torch.arange(seq_len, device=x_seq.device) * n_stations).view(-1, 1, 1)
        batched_edges = edge_index.unsqueeze(0) + offsets          # (seq_len, 2, E)
        batched_edge_index = batched_edges.permute(1, 0, 2).reshape(2, -1)  # (2, seq_len*E)

        emb_flat = self.gat(x_flat, batched_edge_index)            # (seq_len*n_stations, gat_out*heads)
        emb = emb_flat.view(seq_len, n_stations, -1)
        seq = emb.permute(1, 0, 2)             # (n_stations, seq_len, gat_out*heads)
        _, h = self.gru(seq)                   # h: (1, n_stations, gru_hidden)
        h = h.squeeze(0)                       # (n_stations, gru_hidden)
        logits = self.classifier(h).squeeze(-1)  # (n_stations,)
        return logits


def load_data():
    nodes = pd.read_csv(NODES_PATH)
    station_order = nodes["station"].tolist()

    edges = pd.read_csv(EDGES_PATH)
    station_to_idx = {s: i for i, s in enumerate(station_order)}
    src = edges["source"].map(station_to_idx).tolist()
    dst = edges["target"].map(station_to_idx).tolist()
    edge_index = torch.tensor([src + dst, dst + src], dtype=torch.long)

    wide = pd.read_csv(WIDE_DATA_PATH, index_col=0)[station_order]
    labels = pd.read_csv(LABELS_PATH, index_col=0)[station_order]

    # Model INPUT: fill gaps so the GAT always has a feature to work with.
    # ffill/bfill handles short gaps; remaining (start-of-series) gaps get column mean.
    wide_filled = wide.ffill().bfill()
    wide_filled = wide_filled.fillna(wide_filled.mean())

    # Normalize (z-score) per station, using stats from the TRAIN portion only
    # (first (1-VAL_FRACTION) of the timeline) to avoid leaking validation
    # stats into training. Raw AQI values (0-500+) fed unnormalized caused
    # the model to collapse to predicting the majority class every time.
    split_point = int(len(wide_filled) * (1 - VAL_FRACTION))
    train_mean = wide_filled.iloc[:split_point].mean()
    train_std = wide_filled.iloc[:split_point].std().replace(0, 1.0)
    wide_normalized = (wide_filled - train_mean) / train_std

    return station_order, edge_index, wide_normalized, labels


def make_windows(wide_filled, labels, seq_len=SEQ_LEN, stride=STRIDE):
    """Yields (x_seq, y, mask) for each window.
    x_seq: (seq_len, n_stations, 1) float tensor
    y:     (n_stations,) float tensor, target at the LAST hour of the window
    mask:  (n_stations,) bool tensor, True where y is a valid (non-NaN) label
    """
    values = wide_filled.values  # (T, n_stations)
    label_values = labels.values  # (T, n_stations)
    T = values.shape[0]

    for end in range(seq_len - 1, T, stride):
        start = end - seq_len + 1
        x_window = values[start:end + 1]  # (seq_len, n_stations)
        y = label_values[end]             # (n_stations,)
        mask = ~np.isnan(y)
        if not mask.any():
            continue  # entire timestep is dropout across all stations, skip
        x_seq = torch.tensor(x_window, dtype=torch.float).unsqueeze(-1)  # (seq_len, n_stations, 1)
        y_t = torch.tensor(np.nan_to_num(y), dtype=torch.float)
        mask_t = torch.tensor(mask, dtype=torch.bool)
        yield x_seq, y_t, mask_t


def evaluate(model, edge_index, windows):
    model.eval()
    tp = fp = fn = tn = 0
    with torch.no_grad():
        for x_seq, y, mask in windows:
            logits = model(x_seq, edge_index)
            preds = (torch.sigmoid(logits) > 0.5).float()
            p, t, m = preds[mask], y[mask], mask
            tp += ((p == 1) & (t == 1)).sum().item()
            fp += ((p == 1) & (t == 0)).sum().item()
            fn += ((p == 0) & (t == 1)).sum().item()
            tn += ((p == 0) & (t == 0)).sum().item()
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    acc = (tp + tn) / max(tp + fp + fn + tn, 1)
    return {"precision": precision, "recall": recall, "f1": f1, "accuracy": acc, "n_positive": tp + fn}


def main():
    print("Loading data...")
    station_order, edge_index, wide_filled, labels = load_data()
    print(f"{len(station_order)} stations, {len(wide_filled)} timestamps")

    print("Building windows...")
    all_windows = list(make_windows(wide_filled, labels))
    print(f"{len(all_windows)} windows total")

    split_idx = int(len(all_windows) * (1 - VAL_FRACTION))
    train_windows = all_windows[:split_idx]
    val_windows = all_windows[split_idx:]
    print(f"Train: {len(train_windows)} windows | Val: {len(val_windows)} windows")

    model = GATGRU()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    pos_weight = torch.tensor(POS_WEIGHT)
    criterion = nn.BCEWithLogitsLoss(reduction="none")

    best_f1 = -1.0
    best_state = None

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        for i, (x_seq, y, mask) in enumerate(train_windows):
            optimizer.zero_grad()
            logits = model(x_seq, edge_index)
            loss_per_station = criterion(logits, y)
            weight = torch.where(y == 1, pos_weight, torch.tensor(1.0))
            loss = (loss_per_station * weight * mask.float()).sum() / mask.float().sum().clamp(min=1)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            if (i + 1) % 1000 == 0:
                print(f"  epoch {epoch}: {i + 1}/{len(train_windows)} windows processed")

        avg_loss = total_loss / max(len(train_windows), 1)
        val_metrics = evaluate(model, edge_index, val_windows)
        print(f"Epoch {epoch}/{EPOCHS}  train_loss={avg_loss:.4f}  "
              f"val_precision={val_metrics['precision']:.3f}  val_recall={val_metrics['recall']:.3f}  "
              f"val_f1={val_metrics['f1']:.3f}  val_acc={val_metrics['accuracy']:.3f}")

        if val_metrics["f1"] > best_f1:
            best_f1 = val_metrics["f1"]
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            print(f"  -> new best (f1={best_f1:.3f}), checkpoint updated")

    torch.save({"model_state": best_state, "station_order": station_order, "best_val_f1": best_f1}, CHECKPOINT_PATH)
    print(f"\nSaved BEST checkpoint (val_f1={best_f1:.3f}) -> {CHECKPOINT_PATH}")


if __name__ == "__main__":
    main()
