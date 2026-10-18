import { useEffect, useState } from "react";

const BACKEND_HTTP = "http://localhost:8000";
const BACKEND_WS = "ws://localhost:8000";

export function useStations() {
  const [stations, setStations] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${BACKEND_HTTP}/api/stations`)
      .then((res) => {
        if (!res.ok) throw new Error(`Backend returned ${res.status}`);
        return res.json();
      })
      .then(setStations)
      .catch((err) => setError(err.message));
  }, []);

  return { stations, error };
}

export function useLiveFeed({ start, tick = 2 } = {}) {
  const [statuses, setStatuses] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [simTime, setSimTime] = useState(null);
  const [connected, setConnected] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams();
    if (start) params.set("start", start);
    params.set("tick", String(tick));

    const socket = new WebSocket(`${BACKEND_WS}/ws?${params.toString()}`);
    socket.onopen = () => { setConnected(true); setError(null); };
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setError("WebSocket failed - is the backend running on port 8000?");
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "simulation-complete") {
        setDone(true);
        return;
      }
      setSimTime(data.timestamp);
      setStatuses(data.stations);
      if (data.alerts && data.alerts.length > 0) {
        setAlerts((prev) => [...data.alerts.slice().reverse(), ...prev].slice(0, 200));
      }
    };

    return () => socket.close();
  }, [start, tick]);

  return { statuses, alerts, simTime, connected, done, error };
}
