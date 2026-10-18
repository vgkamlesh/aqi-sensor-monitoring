"""
Live dashboard backend. Replays the real hourly predictions in
processed_data/predictions.csv (output of your trained model) over a
WebSocket, running the same alert rules as AlertEngine.java.

Run (from backend/):  uvicorn app:app --reload --port 8000
"""

import asyncio
import os
from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = os.environ.get("PROJECT_ROOT", os.path.join(os.path.dirname(__file__), ".."))
PREDICTIONS_PATH = os.path.join(PROJECT_ROOT, "processed_data", "predictions.csv")
NODES_PATH = os.path.join(PROJECT_ROOT, "processed_data", "station_nodes.csv")

DEFAULT_START = "2023-11-01T00:00:00"
DROPOUT_THRESHOLD_HOURS = 4
SUSTAINED_THRESHOLD = 3

app = FastAPI(title="AQI Sensor Health - Live Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_nodes_df = None
_predictions = None


def load_data():
    global _nodes_df, _predictions
    if _nodes_df is None:
        _nodes_df = pd.read_csv(NODES_PATH)
    if _predictions is None:
        df = pd.read_csv(PREDICTIONS_PATH, parse_dates=["timestamp"])
        _predictions = df.set_index(["timestamp", "station"])["unhealthy"]
    return _nodes_df, _predictions


@app.get("/api/stations")
def get_stations():
    nodes, _ = load_data()
    return nodes.to_dict(orient="records")


class AlertState:
    def __init__(self):
        self.last_seen = {}
        self.streak = defaultdict(int)

    def process(self, station, ts, unhealthy):
        alerts = []
        prev = self.last_seen.get(station)
        if prev is not None:
            gap = (ts - prev).total_seconds() / 3600
            if gap >= DROPOUT_THRESHOLD_HOURS:
                alerts.append({
                    "type": "DROPOUT",
                    "station": station,
                    "timestamp": ts.isoformat(),
                    "message": f"No reading for {int(gap)} hours (last seen {prev.isoformat()})",
                })
        self.last_seen[station] = ts

        self.streak[station] = self.streak[station] + 1 if unhealthy else 0
        if self.streak[station] == SUSTAINED_THRESHOLD:
            alerts.append({
                "type": "SUSTAINED_UNHEALTHY",
                "station": station,
                "timestamp": ts.isoformat(),
                "message": f"{SUSTAINED_THRESHOLD} consecutive unhealthy readings",
            })
        return alerts


@app.websocket("/ws")
async def simulate(websocket: WebSocket):
    await websocket.accept()
    nodes, predictions = load_data()
    stations = nodes["station"].tolist()

    params = websocket.query_params
    current = datetime.fromisoformat(params.get("start", DEFAULT_START))
    tick = float(params.get("tick", 2))
    end = predictions.index.get_level_values("timestamp").max()
    state = AlertState()

    try:
        while current <= end:
            status = {}
            new_alerts = []
            for station in stations:
                try:
                    unhealthy = bool(predictions.loc[(current, station)])
                    status[station] = "unhealthy" if unhealthy else "healthy"
                    new_alerts.extend(state.process(station, current, unhealthy))
                except KeyError:
                    status[station] = "no-data"

            await websocket.send_json({
                "timestamp": current.isoformat(),
                "stations": status,
                "alerts": new_alerts,
            })
            current += timedelta(hours=1)
            await asyncio.sleep(tick)

        await websocket.send_json({"type": "simulation-complete"})
    except WebSocketDisconnect:
        pass
