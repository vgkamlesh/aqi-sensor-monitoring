import React, { useState } from "react";
import { useStations, useLiveFeed } from "./api.js";
import StationMap from "./components/StationMap.jsx";
import AlertFeed from "./components/AlertFeed.jsx";

const DEFAULT_START = "2023-11-01T00:00:00";

export default function App() {
  const { stations, error: stationsError } = useStations();
  const [tick, setTick] = useState(2);
  const { statuses, alerts, simTime, connected, done, error: feedError } =
    useLiveFeed({ start: DEFAULT_START, tick });

  const unhealthyCount = Object.values(statuses).filter((s) => s === "unhealthy").length;
  const noDataCount = Object.values(statuses).filter((s) => s === "no-data").length;

  return (
    <React.Fragment>
      <div className="topbar">
        <div className="wrap topbar-row">
          <div className="brand">
            <span className="brand-mark">LIVE</span>
            <span className="brand-name">AQI Sensor Health Monitoring</span>
          </div>
          <span className="topbar-meta">
            {connected ? (done ? "simulation complete" : "connected") : "connecting..."}
          </span>
        </div>
      </div>

      <div className="hero">
        <div className="wrap">
          <h1>Real-time replay of real model predictions.</h1>
          <p>
            The backend replays your trained GAT+GRU model's hourly output in
            timestamp order, running the same dropout and sustained-unhealthy
            rules as the Java alerting service, starting from Nov 1, 2023.
          </p>

          {(stationsError || feedError) && (
            <p style={{ color: "var(--danger)", fontFamily: "var(--mono)", fontSize: 13 }}>
              {stationsError || feedError}
            </p>
          )}

          <div className="stat-strip">
            <div className="stat">
              <div className="stat-num">{simTime ? simTime.replace("T", " ").slice(0, 16) : "--"}</div>
              <div className="stat-label">simulated clock</div>
            </div>
            <div className="stat">
              <div className="stat-num">{stations.length}</div>
              <div className="stat-label">stations tracked</div>
            </div>
            <div className="stat">
              <div className="stat-num">{unhealthyCount}</div>
              <div className="stat-label">unhealthy this hour</div>
            </div>
            <div className="stat">
              <div className="stat-num">{noDataCount}</div>
              <div className="stat-label">no data this hour</div>
            </div>
            <div className="stat">
              <div className="stat-num">{alerts.length}</div>
              <div className="stat-label">alerts fired so far</div>
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            <label style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text-muted)" }}>
              simulation speed:&nbsp;
              <select value={tick} onChange={(e) => setTick(Number(e.target.value))}>
                <option value={4}>slow (4s / hour)</option>
                <option value={2}>normal (2s / hour)</option>
                <option value={0.5}>fast (0.5s / hour)</option>
              </select>
              &nbsp;(reconnects on change)
            </label>
          </div>
        </div>
      </div>

      <div className="wrap main-grid">
        <div className="panel">
          <h2>Live station map</h2>
          <p className="panel-sub">
            Real geocoded coordinates. Dot color is this simulated hour's model prediction.
          </p>
          <StationMap stations={stations} statuses={statuses} />
        </div>

        <div className="panel">
          <h2>Live alert feed</h2>
          <p className="panel-sub">Same rules as AlertEngine.java.</p>
          <AlertFeed alerts={alerts} />
        </div>
      </div>

      <footer>
        <div className="wrap footer-row">
          <span className="footer-note">FastAPI + WebSocket, replaying processed_data/predictions.csv</span>
        </div>
      </footer>
    </React.Fragment>
  );
}
