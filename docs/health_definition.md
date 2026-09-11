# Sensor Health Definition

Defines what counts as a "faulty" or "unhealthy" sensor reading/station in this
project. This drives label generation for the GAT+GRU model and the alerting
thresholds in the Java component.

## Failure categories

### 1. Dropout (missing data)
A station reports no reading for one or more consecutive hours.
- **Short dropout**: 1-3 missing hours in a row — likely transient (network
  blip, maintenance window). Flag but don't alert.
- **Extended dropout**: 4+ consecutive missing hours — treat as a sensor
  health event, alert.

### 2. Chronic intermittent failure
A station has large gaps scattered across its entire operational history
rather than one clean outage window — e.g. sonia-vihar-dpcc, which has ~5,200
hourly readings spread across a 6-year span that should hold ~52,000+. This
is a station-level reliability flag, evaluated over a rolling window (e.g.
% of expected hours present in the last 30 days), not a single-timestamp
event.

### 3. Stuck value
A station reports the exact same value for N+ consecutive hours where
natural variation would be expected. Suggests a frozen/cached sensor rather
than a real reading.
- Threshold: [TODO — decide N, e.g. 6+ identical consecutive hourly values]

### 4. Drift
A station's readings diverge steadily from its own historical baseline or
from spatially correlated neighboring stations, without a plausible
environmental cause (e.g. a pollution event visible at all nearby stations).
Detected via comparison against a rolling baseline or neighbor correlation,
not a single-point rule.

### 5. Outlier spike
A single-hour reading is implausible given the station's own recent history
and/or neighboring stations' readings for the same hour — e.g. a physically
impossible jump or a value far outside plausible pollutant ranges.
- Threshold: [TODO — decide statistical rule, e.g. z-score against rolling
  window, or fixed physical bounds]

## What the GNN predicts
[TODO — decide once categories above are finalized: is this a binary
healthy/unhealthy classifier per station per timestamp, or per-category
multi-label? Binary is simpler and a safer scope given the timeline.]

## What the alerting component does with it
The Java alerting service consumes model output (or raw threshold checks,
for the simpler categories that don't need the GNN) and fires an alert when
a station crosses into "unhealthy" for a sustained period, not on a single
noisy timestamp — avoids alert flapping.
