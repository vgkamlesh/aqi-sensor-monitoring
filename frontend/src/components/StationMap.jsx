import React, { useMemo, useState } from "react";

const STATUS_COLOR = {
  healthy: "var(--accent)",
  unhealthy: "var(--danger)",
  "no-data": "var(--dropout)",
};

export default function StationMap({ stations, statuses }) {
  const [hover, setHover] = useState(null);
  const W = 620, H = 460, PAD = 30;

  const bounds = useMemo(() => {
    if (stations.length === 0) return null;
    const lats = stations.map((s) => s.lat);
    const lons = stations.map((s) => s.lon);
    return {
      minLat: Math.min(...lats), maxLat: Math.max(...lats),
      minLon: Math.min(...lons), maxLon: Math.max(...lons),
    };
  }, [stations]);

  if (!bounds) {
    return <p className="panel-sub">Waiting for station data from backend...</p>;
  }

  const x = (lon) => PAD + ((lon - bounds.minLon) / (bounds.maxLon - bounds.minLon)) * (W - PAD * 2);
  const y = (lat) => PAD + (1 - (lat - bounds.minLat) / (bounds.maxLat - bounds.minLat)) * (H - PAD * 2);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto", display: "block" }}>
        {stations.map((s) => {
          const status = statuses[s.station] || "no-data";
          return (
            <circle
              key={s.station}
              className="station-dot"
              cx={x(s.lon)} cy={y(s.lat)}
              r={status === "unhealthy" ? 6 : 4}
              fill={STATUS_COLOR[status]}
              fillOpacity={status === "no-data" ? 0.35 : 0.9}
              onMouseEnter={() => setHover({ ...s, status })}
              onMouseLeave={() => setHover(null)}
            />
          );
        })}
        {hover && (
          <g>
            <rect
              x={Math.min(x(hover.lon) + 10, W - 190)} y={y(hover.lat) - 14}
              width={180} height={20} fill="var(--panel)" stroke="var(--border)" rx="2"
            />
            <text
              x={Math.min(x(hover.lon) + 16, W - 184)} y={y(hover.lat)}
              className="map-tooltip" dominantBaseline="middle"
            >
              {hover.station} - {hover.status}
            </text>
          </g>
        )}
      </svg>
      <div className="map-legend">
        <span className="legend-item"><span className="legend-dot" style={{ background: "var(--accent)" }}></span>healthy</span>
        <span className="legend-item"><span className="legend-dot" style={{ background: "var(--danger)" }}></span>unhealthy</span>
        <span className="legend-item"><span className="legend-dot" style={{ background: "var(--dropout)" }}></span>no data this hour</span>
      </div>
    </div>
  );
}
