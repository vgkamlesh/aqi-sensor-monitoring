# AQI Sensor Network Health Monitoring

Detects faulty air quality sensors (not just bad air quality) across Delhi-NCR's
CPCB monitoring network, using a graph neural network over real station data,
with a decoupled Java alerting layer and a fully containerized pipeline.

## The problem

CPCB's 39 monitoring stations across Delhi report pollutant readings hourly.
Stations themselves can fail in ways that have nothing to do with air quality:
they can freeze on a stuck value, drift from their neighbors, or go offline
entirely. This project builds a pipeline that distinguishes **sensor health**
from **air quality** -- a genuinely different problem from most AQI projects,
which model pollution levels rather than the sensors reporting them.

## Architecture

```
raw CPCB CSVs (39 stations, 2017-2023, messy pivoted format)
        |
   preprocess.py            --> tidy long/wide format
        |
   build_graph.py            --> K-nearest-neighbor station graph (38 nodes,
        |                          sonia-vihar-dpcc excluded -- see below)
   generate_labels.py        --> stuck-value / outlier labels (dropout
        |                          deliberately excluded -- see below)
   train_model.py             --> GAT+GRU model, trained + checkpointed
        |
   export_predictions.py      --> hourly predictions.csv (Python/PyTorch
        |                          stops here -- Java never touches it)
        v
   Java alerting service (Maven) --> DROPOUT + SUSTAINED_UNHEALTHY alerts
```

Both the model-export step and the alerting service are containerized
(`docker-compose.yml`) and wired with a completion dependency so the
alerting container only starts once fresh predictions exist.

## Key design decisions (and why)

- **Dropout is not modeled.** A missing reading is trivially detectable --
  the row is empty -- so folding it into the same binary target as
  stuck/outlier diluted the label to 25-90% "unhealthy" per station,
  destroying the signal. Dropout is instead a direct rule check in the
  Java alerting layer (gap between consecutive readings). The model only
  predicts stuck-value/outlier among readings that actually exist, giving
  a realistic ~1.8% base rate.
- **`sonia-vihar-dpcc` is excluded from the graph.** It has ~5,200 hourly
  readings scattered across a 6-year span that should hold ~52,000+ --
  chronic intermittent failure, not a clean outage. Too sparse to be a
  useful GAT node; kept as a real-world example of sensor unreliability
  in `docs/health_definition.md` instead.
- **Station coordinates are geocoded, not sourced from an official list.**
  CPCB/DPCC don't publish exact station lat/long publicly (confirmed via
  RTI requests in journalism on the topic). Station names are real Delhi
  place names, so coordinates were resolved via OpenStreetMap Nominatim
  and spot-checked.
- **Train/val split is by time, not random.** Standard practice for time
  series -- prevents future data leaking into training.
- **Alerts require 3 consecutive unhealthy readings**, not one, to avoid
  flapping on single noisy timestamps.

## Results

- Graph: 38 stations, 126 edges (K=5 nearest neighbors by geographic distance)
- Model: GAT+GRU, best validation F1 = 0.130 (modest but genuine, given a
  ~1.8% positive class and hourly-AQI-only features -- see Future Work)
- End-to-end run: 18,752 alerts fired across ~1.7M hourly readings (~1.1%)
- Sanity check: alerts cluster around Nov 6-10, 2023, matching Delhi's
  well-documented post-Diwali/stubble-burning winter smog event --
  independent stations flagging simultaneously on a real event is a good
  signal the pipeline is picking up something real, not fitting noise.

## Running it

```bash
# 1. Get the data
python download_dataset.py          # -> raw_data/

# 2. Build the pipeline
python src/preprocess.py            # -> processed_data/combined_*.csv
python src/geocode_stations.py      # -> station_coordinates.csv
python src/build_graph.py           # -> processed_data/station_*.csv
python src/generate_labels.py       # -> processed_data/labels_wide.csv

# 3. Train
python src/train_model.py           # -> processed_data/gat_gru_model.pt

# 4. Run the full containerized pipeline
docker compose up --build
```

## Future work

- F1 of 0.130 leaves real room to improve: additional features (weather
  covariates -- temperature, humidity, wind), longer training, and
  hyperparameter tuning were all out of scope given the project timeline.
- A live data feed instead of the static historical CSVs, so the alerting
  service tails real-time readings rather than replaying a file.
- Jenkins CI/CD pipeline is written (`Jenkinsfile`: Maven test, Docker
  builds, compose smoke test) but not deployed/run for this submission.

## Project structure

```
raw_data/            downloaded CPCB station CSVs (not committed -- see download_dataset.py)
processed_data/       cleaned data, graph, labels, model checkpoint, predictions
src/                  Python pipeline (preprocessing, graph, labels, model, export)
alerting/             Java/Maven alerting service
docker/               predictor Dockerfile
docs/                 health_definition.md -- the design doc everything else builds on
Jenkinsfile           CI/CD pipeline definition
docker-compose.yml    wires predictor + alerting together
```# aqi-sensor-monitoring
