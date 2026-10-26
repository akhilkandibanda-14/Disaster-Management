# SafeMap AI — Milestone 9: Operational Reliability and End-to-End Validation Report

## 1. Executive Summary

Milestone 9 hardened SafeMap AI's operational reliability, live-data resilience, facility verification truthfulness, security safeguards, and end-to-end flood evacuation workflows. The entire system strictly adheres to the **flood-only mandate**, ensuring that no unrelated disaster types (e.g., tsunamis, earthquakes, cyclones, wildfires, landslides, droughts) are introduced or accepted.

All validation runs succeeded:
- **Backend Test Suite:** 245 passing tests (`0 failed, 41 expected warnings, 130.76s runtime`).
- **Milestone 9 Dedicated Test Suite:** 20 passing end-to-end reliability tests (`0 failed, 47.96s runtime`).
- **Frontend Production Build:** Vite v8.2.2 completed in `253ms` (59 modules transformed, 0 errors).

---

## 2. Audit of Operational Reliability & Verified Issues

| Subsystem | Verified Reliability / Security Concern | Resolution Applied |
| :--- | :--- | :--- |
| **Weather Feed** | Unbounded timeouts could hang client connections; stale observations were indistinguishable from real-time conditions; simulated demo weather could be confused with live telemetry. | Added 5.0s timeout to `httpx.get`; extracted OpenWeather observation timestamp (`payload["dt"]`); flagged observations `> 3 hours` as `is_stale=True` with warning; explicitly flagged simulated demo responses with `is_simulated=True` and `is_stale=False`. |
| **Flood Hazard Ingestion** | NDMA SACHET and GloFAS feed network failures or timeouts were silent; consumers had no visibility into provider outages. | Added provider diagnostics capturing failure reasons into `last_provider_warnings`; exposed `provider_warnings: List[str]` in `HazardListResponse`; maintained `ALLOWED_FLOOD_DISASTER_TYPES` filter. |
| **Facility Verification** | Physical directory presence was conflated with live operational readiness and real-time bed capacity. | Separated verification into three distinct fields: `location_verified` (directory/address), `operational_status_verified` (live operations), and `capacity_verified` (bed availability). Added aggregate verification counters and a truth-in-data disclaimer. |
| **Evacuation Routing** | Routes traversing or terminating in active flood hazard zones lacked contextual awareness; roads blocked by inundation needed robust rerouting and `NO_SAFE_ROUTE` fallback. | Origin and destination coordinates are checked against published flood hazard polygons. Intersections trigger prominent warnings. Severed or inundated road segments are avoided; when no path exists, `NO_SAFE_ROUTE` is returned with status 200. Destinations with `operational_status` in (`CLOSED`, `FLOODED`, `UNSAFE`) are rejected with HTTP 409. |
| **Institutional Intake** | Upload endpoints could be susceptible to directory traversal (`../../`), null byte poisoning, or denial-of-service via massive payloads. | Enforced strict `10MB` payload limit, rejected null bytes (`\x00`), extracted basename via `Path(filename).name`, sanitized filename against `[^A-Za-z0-9_.-]`, and asserted that the resolved destination path strictly resides within the target directory. |
| **Error Sanitization** | Unhandled server crashes could leak database connection strings, passwords, or internal file paths in tracebacks. | Registered global FastAPI exception handler `@app.exception_handler(Exception)` that logs full traces internally while returning sanitized HTTP 500 error messages (`"An internal server error occurred."`). |

---

## 3. Facility Verification Audit Breakdown

SafeMap AI distinguishes **location verification** from **live operational status** and **bed availability**:
- **Identity & Location Verification (`location_verified`):** Verified against official government directories (Telangana Open Data Portal, GHMC, National Health Portal).
- **Live Emergency Status (`operational_status_verified`):** Marked `False` (unverified) because static directories do not provide live flood damage or telemetry.
- **Capacity / Bed Availability (`capacity_verified`):** Marked `False` (unverified) because hospital occupancy fluctuates dynamically and lacks a live hospital management system integration.

### Facility Audit Statistics (Hyderabad Municipal Area):
- Total Emergency Facilities: **19**
- Location & Identity Verified: **18** (Hospitals & Relief Centers)
- Live Operational Status Verified: **0** (19 Unverified — marked with caveat)
- Bed / Refuge Capacity Verified: **0** (19 Unverified — marked with caveat)
- Simulated Demo Facilities: **1** (`HYD-S-000`, Hyderabad Central Flood Relief HQ — explicitly flagged `DEMO_SIMULATED`)

---

## 4. Flood Evacuation Workflow Validation

### A. Shelter & Hospital Destination Selection
- Users can specify destination coordinates or select official facilities via `facility_id` (e.g., `HYD-H-002` Gandhi Hospital) or legacy `shelter_id`.
- If an emergency facility is marked `CLOSED`, `FLOODED`, or `UNSAFE`, the routing engine rejects the request with HTTP 409 Conflict.
- If a destination intersects an active documented flood hazard (such as Osmania General Hospital on the Musi Riverbank), the routing engine generates the route but attaches prominent safety warnings.

### B. Hazard Avoidance & Rerouting
- Active road blockages (e.g., road condition `FLOODED` or `WATERLOGGED`) trigger penalty weights in the graph routing engine, forcing routes through safe secondary arterials.
- When all outbound routes are cut off, the system returns `route_status: "NO_SAFE_ROUTE"`, preventing users from being guided onto unmonitored or compromised roads.

### C. Flood-Only Alert Scope & Hyderabad Guard Preservation
- The alert ingestion pipeline strictly admits flood categories (`FLOOD`, `URBAN_FLOOD`, `FLASH_FLOOD`, `HEAVY_RAIN`, `INUNDATION`).
- Non-flood categories (`EARTHQUAKE`, `TSUNAMI`, `CYCLONE`, `WILDFIRE`, `LANDSLIDE`, `DROUGHT`) are rejected by hazard APIs with HTTP 400.
- The 50 km Hyderabad coverage guard remains strictly enforced: requests within Hyderabad return `MODEL_UNSUPPORTED` / `INSUFFICIENT_LOCAL_DATA` rather than hallucinating predictions.

---

## 5. Verification Command Logs

### Backend Test Suite
```bash
python -m pytest -q
........................................................................ [ 29%]
........................................................................ [ 58%]
........................................................................ [ 88%]
.............................                                            [100%]
245 passed, 41 warnings in 130.76s (0:02:10)
```

### Dedicated Milestone 9 End-to-End Suite
```bash
python -m pytest test_operational_reliability_m9.py -v
20 passed, 1 warning in 47.96s
```

### Frontend Production Build
```bash
npm run build
vite v8.2.2 building client environment for production...
✓ 59 modules transformed.
dist/index.html                   0.62 kB │ gzip:   0.38 kB
dist/assets/index-BEI-jSOz.css   25.91 kB │ gzip:   9.04 kB
dist/assets/index-COD85HVL.js   415.87 kB │ gzip: 121.29 kB
✓ built in 253ms
```

---

## 6. Truth-in-Data Declaration

SafeMap AI adheres to the principle that **the absence of an alert is never presented as proof of safety**. Unmonitored roads, stale weather observations, and facilities without live telemetry are transparently labeled with caveats across API responses and frontend dashboards.
