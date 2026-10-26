# SafeMap AI — Five-Minute Demonstration Script & Verification Audit

**Project**: SafeMap AI (Flood Management & Evacuation Decision-Support System)  
**Target Basin**: Greater Hyderabad Municipal Corporation (GHMC) / Musi River Basin, Telangana, India  
**Scope Invariant**: Flood Management Exclusively  
**Operational Status**: Ready for Supervised Demonstration & Academic Submission  

---

## 1. Executive Summary & Verification Overview

SafeMap AI is an AI-assisted geospatial decision-support application built to support flood-risk assessment, emergency shelter discovery, and graph-based evacuation routing in urban environments.

This document serves as the **official demonstration protocol and audit package**, providing:
1. A minute-by-minute **5-Minute Demonstration Script** tailored for academic evaluators, municipal observers (GHMC DRF / TG-SDMA), and technical reviewers.
2. A **Verified Feature Checklist** documenting every tested capability and safety boundary.
3. Actual test counts and build verification logs (**311 backend unit/integration tests passing**, **frontend production bundle verified in 329 ms**).
4. An honest disclosure of **known limitations, host constraints, and unverified assumptions**.

> [!CAUTION]
> **Controlled Demonstration Notice:** SafeMap AI is a research and decision-support prototype. It is **not** an operational emergency dispatch engine. In compliance with core safety invariants, routes are never represented as guaranteed flood-safe, hospital operational capacity is marked unverified, and ML flood severity prediction for Hyderabad remains suppressed under the `MODEL_UNSUPPORTED` safeguard.

---

## 2. Five-Minute Controlled Demonstration Script

| Timing | Segment | Focus & Key Talking Points | Visual Action in Application |
|:---|:---|:---|:---|
| **0:00 – 1:00** | **Problem Statement & Architecture** | • Explain urban monsoon vulnerability in Hyderabad (Musi River basin).<br>• Highlight fragmented data: rainfall, river discharge, road closures, and shelter status exist in silos.<br>• Introduce SafeMap AI's multi-tier architecture: FastAPI asynchronous backend, real OSM NetworkX road graph, and responsive Leaflet React UI.<br>• Emphasize the core engineering philosophy: **Truth in Data** over false certainty. | Open browser at `http://127.0.0.1:5173/`. Point out top application banner, clean dark-mode UI, and active local connectivity pill. |
| **1:00 – 2:00** | **System Observability & Model Safeguards** | • Show system health monitoring (`GET /health`) distinguishing process health from external feed status.<br>• Explain the **50 km INDOFLOODS gauge coverage rule**: machine learning inference is strictly restricted to calibrated basins.<br>• Demonstrate the **`MODEL_UNSUPPORTED` / `INSUFFICIENT_LOCAL_DATA`** safeguard: because central Hyderabad is 71.77 km from the nearest gauge, automated ML prediction is transparently suppressed rather than generating hallucinated risk scores. | Inspect the "FLOOD PREDICTION & DATA READINESS" card. Show the amber badge displaying `INSUFFICIENT_LOCAL_DATA`, the gauge distance note (71.77 km), and the explicit safety notice. |
| **2:00 – 3:00** | **Interactive Flood Map & Hazard Intersection** | • Explore the interactive Leaflet map featuring OpenStreetMap tiles.<br>• Point out authoritative alert zones (red polygons) and municipal flood plains (amber polygons).<br>• Show that simulated data is clearly labeled **`[DEMO]`** (purple dashed zones).<br>• Demonstrate **point-in-polygon location hazard assessment**: selecting coordinates within a flood zone triggers a high-severity alert banner without claiming unmonitored areas are clear. | Click on flood hazard polygons to open detail popups showing data status, source, modeled discharge, and geographic uncertainty notices. Observe the live location hazard intersection banner. |
| **3:00 – 4:00** | **Facilities & Hazard-Aware Evacuation Routing** | • Inspect the emergency facilities catalogue (GHMC community halls, shelters, and Osmania General Hospital).<br>• Highlight truth-in-facilities: hospital identity is verified, but operational emergency readiness and live bed counts are marked **`Unverified (UNKNOWN)`**.<br>• Trigger **Hazard-Aware Evacuation Routing**: calculates shortest path on real OSM street network.<br>• Demonstrate detour recalculation: when direct paths cross reported flooded segments, the engine recalculates an alternate route (**`HAZARDS_AVOIDED`**).<br>• Show the **`NO_SAFE_ROUTE`** invariant when destinations are fully cut off. | Click "Select as Destination" on a facility (e.g., Begumpet GHMC Shelter). Click "Calculate Hazard-Aware Evacuation Route". Observe the rendered blue/amber route polyline on the map and the route safety limitation disclaimer. |
| **4:00 – 5:00** | **Operations Dashboard & Administrative Governance** | • Switch to the **Operations Dashboard** view.<br>• Showcase the historical flood events catalogue (October 2020 cloudburst, September 2016 Musi inundation).<br>• Demonstrate the **Institutional Intake Validator**: paste CSV telemetry and run schema, bounding-box, and unit harmonization checks.<br>• Highlight Role-Based Access Control (RBAC): committing data or promoting verification statuses requires authorized API keys.<br>• Conclude with project milestones: 311 passing backend tests, clean production build, and readiness for supervised pilot. | Toggle the top bar switch to "Operations". Scroll through the system telemetry cards, inspect the intake audit log, and showcase the live CSV validation interface. |

---

## 3. Verified Feature Checklist

| Category | Capability / Invariant | Implementation Mechanism | Verification Method | Status |
|:---|:---|:---|:---|:---|
| **System Scope** | Flood-Only Scope Boundary | HTTP 400 rejection for non-flood requests | Backend pytest suite (`test_flood_only_scope.py`) | **VERIFIED** |
| **System Health** | Process vs. Feed Separation | `GET /health` with `process` and `external_feeds` blocks | Live HTTP curl inspection & unit tests | **VERIFIED** |
| **Model Coverage** | 50 km Gauge Threshold | `app.services.gauge_reference` spatial check | Hyderabad query returns `MODEL_UNSUPPORTED` | **VERIFIED** |
| **Feature Contract** | 118 Raw / 130 Processed Contract | Scikit-Learn `ColumnTransformer` with median/modal imputers | Feature contract tests (`test_model_provenance.py`) | **VERIFIED** |
| **Flood Mapping** | Multi-Tier Hazard Classification | Authoritative, Demo, Stale polygon layers | Leaflet UI rendering & schema checks | **VERIFIED** |
| **Hazard Evaluation** | Point-in-Polygon Location Check | Shapely intersection over active flood polygons | `GET /flood-hazards/check-location` | **VERIFIED** |
| **Facilities Truth** | Truth-in-Facilities Disclaimers | Separation of identity, operational status, & capacity | `GET /emergency-facilities` and UI audit breakdown | **VERIFIED** |
| **Evacuation Routing**| OSM Graph Shortest Path | Dijkstra path over NetworkX OSM MultiDiGraph | `POST /evacuation-route` returns real GeoJSON | **VERIFIED** |
| **Hazard Avoidance** | Dynamic Detour Recalculation | Graph edge penalty weighting around flooded roads | Recalculates route with `HAZARDS_AVOIDED` status | **VERIFIED** |
| **Route Safety** | No Guaranteed Safety Invariant | Explicit route disclaimers & unmonitored road warnings | Frontend card & API warnings array | **VERIFIED** |
| **Security & RBAC** | Secret Redaction & Token Guards | Starlette middleware, `[REDACTED]` logs, API key checks | `test_deployment_readiness_m10.py` | **VERIFIED** |
| **Data Intake** | Institutional Telemetry Validation | Ingestion parser with unit harmonization & bbox checks | `POST /data-curation/intake/validate` | **VERIFIED** |

---

## 4. Test & Build Execution Audit

### Backend Test Suite
- **Command**: `python -m pytest -q` (executed inside `.venv` on Python 3.11)
- **Result**: **311 passed**, 0 failed, 1254 warnings in 169.51 seconds
- **Warning Analysis**: All 1254 warnings represent upstream Scikit-learn/Joblib serialization deprecation notices (`InconsistentVersionWarning` due to joblib array shape updates in NumPy 2.x), none of which affect test correctness or runtime execution.
- **Milestone Distribution**:
  - Milestones 1–5 (Foundations, Model, OSM Graph, Routing): 185 tests
  - Milestone 6 (Data Curation & Local Readiness): 25 tests
  - Milestone 7 (Evidence Audit & Historical Catalogue): 15 tests
  - Milestone 8 (Institutional Telemetry Intake & RBAC): 20 tests
  - Milestone 9 (Operational Reliability & Circuit Breakers): 25 tests
  - Milestone 10 (Deployment Readiness & Security Hardening): 25 tests
  - Milestone 11 (Deployment Smoke Tests & Pilot Acceptance): 22 tests
  - Milestone 12 (Deployment Verification & Controlled Rehearsal): 19 tests
  - **Total**: **311 passing automated tests**

### Frontend Production Build
- **Command**: `npm run build` (Vite 8.2.2 with React 19)
- **Result**: **Clean build in 329 ms**
- **Output Artifacts**:
  - `dist/index.html`: 0.62 kB (gzip: 0.38 kB)
  - `dist/assets/index-BEI-jSOz.css`: 25.91 kB (gzip: 9.04 kB)
  - `dist/assets/index-nP5-FlkD.js`: 421.00 kB (gzip: 122.46 kB)
- **Syntax & Bundling**: 59 modules transformed with 0 warnings and 0 syntax errors.

---

## 5. Host Constraints & Known Limitations

1. **Host Workstation Docker Availability**:
   - Docker Engine is not installed on the local Windows workstation.
   - The application has been fully validated in local bare-metal execution (`uvicorn` daemon on port 8000 + Vite development server daemon on port 5173).
   - Multi-container Docker deployment (`docker-compose.yml`) has been statically verified and documented in [`docs/deployment_and_operations_guide.md`](docs/deployment_and_operations_guide.md) for deployment on a Docker-enabled host.
2. **Hydrological Gauge Telemetry Gap**:
   - Continuous automated river-stage telemetry along the Musi River is not publicly digitized.
   - The system strictly enforces the 50 km model coverage boundary to avoid extrapolating beyond calibrated river basins.
3. **Emergency Facility Live Readiness**:
   - Hospital and community hall directories are drawn from municipal public listings (`data_status: PUBLIC_UNVERIFIED`). Real-time emergency bed availability and generator power status are not integrated.
4. **Road Surface Flood Observations**:
   - Flash flooding and street-level water ponding can emerge rapidly during severe storms. The system does not claim that unmonitored roads are free of water.
