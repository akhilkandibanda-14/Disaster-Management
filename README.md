# AI-Based Disaster Management and Safe Evacuation System

A modular flood-disaster decision-support prototype for risk prediction, safe shelter recommendation, and evacuation routing.

## Current status: Phase 2 complete

This first phase establishes the application boundaries:

- `frontend/`: React + Vite citizen dashboard shell
- `backend/`: FastAPI service boundary and configuration
- `ml/`: dataset, training, and saved-model workspace
- `database/`: PostgreSQL/PostGIS schema and seed workspace
- `docs/`: architecture and development notes

Phase 2 adds SQLAlchemy/PostgreSQL boundaries, PostGIS-compatible shelter
storage, road conditions, disaster alerts, typed API schemas, and deterministic
demo records. With `DEMO_MODE=true`, the read APIs work without a running
database after the backend dependencies are installed.

The application will distinguish live, latest-available, predicted, and demo/simulated data. No emergency claim is made by this prototype; official authorities remain authoritative.

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ with PostGIS for later phases

## Run the current scaffold

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/health`.

Useful Phase 2 endpoints:

- `GET /shelters`
- `GET /shelters/nearby?latitude=17.385&longitude=78.486&radius_km=10`
- `GET /shelters/recommended?latitude=17.385&longitude=78.486`
- `GET /road-conditions`
- `GET /disaster-alerts`
- `GET /weather?latitude=17.385&longitude=78.486`
- `GET /risk-map`
- `GET /danger-zones`
- `GET /safe-zones`
- `POST /evacuation-route`
- `POST /predict`

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

The prediction request requires `latitude`, `longitude`, `rainfall`,
`temperature`, `humidity`, `water_level`, and `elevation`. It returns a
probability, configurable risk level, timestamp, and data-source label. Until
the supplied dataset has been used to train a model, `/predict` returns `503`
with an actionable message instead of fabricating a result.

`/weather` uses OpenWeather when `WEATHER_API_KEY` is configured. With
`DEMO_MODE=true` and no key, it returns clearly labelled simulated weather so
the development workflow remains usable. With demo mode disabled and no key or
an unavailable provider, it returns `503` instead of silently presenting fake
live observations.

Risk endpoints currently return a fixed 3×3 demo grid bounded to the sample
Hyderabad region, labelled `DEMO / SIMULATED DATA`. The polygons are regular
demo cells, not authoritative flood boundaries. Once the supplied dataset and
spatial feature source are available, the production path will replace these
cells with model-backed geographic zones.

The recommended-shelter endpoint does not select by distance alone. Its score
uses 40% disaster safety, 25% road safety, 15% capacity availability, 10%
accessibility, and 10% distance. Closed, full, and high-risk shelters are
excluded; the response includes alternatives, score components, distance, ETA,
and the reason for the recommendation.

`POST /evacuation-route` accepts the user coordinates and optionally a shelter
ID. Without an ID it uses the safest available shelter. The current demo
router returns transparent simulated geometry, detours around known demo road
hazards, and includes warnings. It is not a replacement for Google Routes or
official road-closure instructions; a production routing provider can be
added behind the routing service later.

### Database setup

Start PostgreSQL/PostGIS with `docker compose up -d postgres`, then apply
`database/schema.sql`. To insert the labelled development shelters, run
`python database/seed.py` from the repository root after installing the backend
requirements. Set `DEMO_MODE=false` to read from PostgreSQL instead of the
in-memory demo records.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

The frontend expects the API at `http://127.0.0.1:8000` by default.

## Configuration

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env`. Secrets are intentionally excluded from source control.

## Adding the flood dataset later

The project is ready for the required dataset to be uploaded later. Place the
CSV at `ml/data/flood_dataset.csv`, or set `FLOOD_DATASET_PATH` in
`backend/.env`. The training pipeline will validate the file before use and
will not silently replace it with synthetic data.

The expected minimum columns are:

`latitude`, `longitude`, `rainfall`, `temperature`, `humidity`, `water_level`,
`elevation`, and a target column named `flood_occurrence` or `flood_risk`.

After uploading and reviewing the dataset, train and evaluate the model from
the repository root:

```powershell
python -m ml.train --dataset ml/data/flood_dataset.csv --model ml/models/flood_risk_model.joblib
python -m ml.evaluate --dataset ml/data/flood_dataset.csv --model ml/models/flood_risk_model.joblib
```

Training is intentionally blocked with a clear error when the dataset is
missing or invalid. No accuracy or scientific validity is claimed until the
actual dataset has been evaluated.

When you provide the dataset, we will inspect its actual column names, missing
values, units, geographic coverage, and target distribution before running
training. Until then, `ml/data/` intentionally contains no fake training
dataset.

## Planned implementation order

1. Foundation and local health checks
2. Database schema, typed resources, APIs, and demo seed data **(complete)**
3. Flood dataset validation and Random Forest pipeline **(pipeline complete; dataset pending)**
4. Prediction API **(complete; requires uploaded/trained model)**
5. Weather API **(complete)**
6. Risk-zone API **(demo grid complete; trained geographic source pending)**
7. Shelter recommendation API **(complete; route geometry pending)**
8. Evacuation route API **(demo geometry complete; provider integration pending)**
9. Map-first React dashboard **(API-connected demo workflow complete; Google Maps provider pending)**
10. Authority and emergency-response views
11. Tests, observability, and deployment documentation

## Limitations

The first release will use clearly labelled demo data when external credentials or authoritative feeds are unavailable. ML output is a decision-support signal, not a guarantee of safety. Google Maps and weather providers do not automatically know every newly flooded or blocked road.
