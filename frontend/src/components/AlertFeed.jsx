import React from "react";

export default function AlertFeed({ alerts }) {
  if (alerts.length === 0) {
    return <p className="panel-sub">No alerts fired yet. Waiting on the simulation.</p>;
  }

  return (
    <div className="log">
      {alerts.map((a, i) => (
        <div className="log-row" key={`${a.station}-${a.timestamp}-${i}`}>
          <span className={"log-type " + (a.type === "DROPOUT" ? "dropout" : "danger")}>
            {a.type === "DROPOUT" ? "DROPOUT" : "SUSTAINED"}
          </span>
          <span className="log-station">{a.station}</span>
          <span className="log-ts">{a.timestamp.replace("T", " ").slice(0, 16)}</span>
        </div>
      ))}
    </div>
  );
}
