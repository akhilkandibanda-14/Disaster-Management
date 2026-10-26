# SafeMap AI — Final Viva Examination Questions & Answers
## Comprehensive Viva Voce Preparation Guide for Evaluators & Candidates

---

### Candidate & Examination Metadata
- **Project Title**: SafeMap AI — Flood Management & Hazard-Aware Evacuation Support System
- **Student Name**: `[Student Name]`
- **Roll / Student ID**: `[Roll / Hall Ticket Number]`
- **Department**: `[Department of Computer Science and Engineering / Information Technology]`
- **College / University**: `[College / University Name]`
- **Project Supervisor**: `[Project Guide / Supervisor Name]`
- **Academic Year**: `[Academic Year, e.g., 2025–2026]`

---

### Category 1: Project Choice, Motivation & Problem Statement

#### Q1. Why did you choose this project for your final year capstone?
**Answer**:  
Urban flash floods are one of the most frequent and deadly natural disasters in modern Indian cities, particularly in Hyderabad along the Musi River basin. During heavy monsoons, roadways and causeways submerge in minutes. Commercial navigation systems like Google Maps optimize strictly for travel time and traffic density, not flood hazard zones. When a low-lying causeway floods and ordinary traffic clears, standard GPS algorithms interpret it as a fast shortcut, directly endangering evacuees. I chose this project to engineer an explainable, hazard-aware routing system that bridges municipal hydrological data with spatial pathfinding to prevent people from being routed into submerged roads.

#### Q2. What exact problem does SafeMap AI solve that existing map platforms do not?
**Answer**:  
Existing consumer mapping platforms suffer from three critical blind spots during flood emergencies:
1. **Hazard Blindness**: They lack integration with spatial flood hazard boundaries (e.g., river overflow corridors, submerged underpasses).
2. **False Safety Signals**: They treat absence of traffic data as an open road, routing drivers directly onto flooded causeways.
3. **Black-Box AI Extrapolation**: Many academic disaster prototypes make uncalibrated predictions in regions without physical stream gauge data.  
SafeMap AI solves this by checking road graph edges against active flood polygons, applying dynamic penalties ($10^6\times$) to compute verifiable detours, and strictly suppressing uncalibrated AI predictions when local gauge data is absent.

#### Q3. Is SafeMap AI an operational civil defense tool or an academic prototype?
**Answer**:  
SafeMap AI is an **academic decision-support prototype**. It is designed to demonstrate architectural, spatial, and algorithmic principles of responsible disaster informatics. It must **not** be used as the sole basis for real-world life-safety or emergency rescue dispatch. In any actual disaster, citizens must follow instructions issued by official civil defense authorities (NDRF, GHMC, and police).

#### Q4. Why is your project limited strictly to flood management rather than a multi-disaster system?
**Answer**:  
Many student projects attempt to cover earthquakes, fires, cyclones, and floods simultaneously. However, each disaster type operates on fundamentally different physical phenomena, temporal scales, and data models. Floods require catchment hydrology, rainfall records, digital elevation models, and road inundation polygons. Attempting to build a multi-disaster system would dilute the domain rigor and result in superficial placeholders. By focusing strictly on urban floods, we implemented genuine spatial point-in-polygon checks, OpenStreetMap graph routing, and defensible model boundary enforcement.

---

### Category 2: Technology Stack & Architectural Decisions

#### Q5. What is the overall architecture of SafeMap AI?
**Answer**:  
SafeMap AI uses a decoupled three-tier architecture:
1. **Frontend Presentation Tier**: React 19 and Leaflet 1.9 wrapped with Vite 8, featuring dark-mode tile rendering and a `ResizeObserver` lifecycle resizer.
2. **Backend Services Tier**: FastAPI (Python 3.13) asynchronous gateway providing REST endpoints, Pydantic schema validation, and RBAC authentication.
3. **Graph & Spatial Computation Engine**: In-memory NetworkX directed graph extracted from OpenStreetMap, backed by a cached SciPy `cKDTree` for sub-millisecond coordinate snapping, and Shapely for Point-in-Polygon evaluations.

#### Q6. Why did you choose FastAPI over Flask or Django?
**Answer**:  
We chose FastAPI for three distinct reasons:
1. **Asynchronous Throughput**: Evacuation routing during disaster scenarios requires handling concurrent requests without thread blocking. FastAPI’s native `async`/`await` support handles high concurrency efficiently.
2. **Strict Type Safety**: Automatic request and response validation via Pydantic v2 ensures malformed coordinates or invalid facility IDs are rejected before reaching business logic.
3. **Interactive Documentation**: FastAPI automatically generates interactive OpenAPI/Swagger documentation (`/docs`), which accelerated testing and API verification.

#### Q7. Why did you choose React and Leaflet for the frontend rather than Google Maps API?
**Answer**:  
1. **Independence & Vendor Neutrality**: Leaflet is open-source and integrates natively with OpenStreetMap (OSM) tiles without API key quotas, proprietary billing, or telemetry leakage.
2. **Custom Spatial Rendering**: Leaflet allows direct manipulation of GeoJSON feature layers, custom dark-mode CSS filters, and custom polyline styling for detours and flood polygons.
3. **Offline & Staging Compatibility**: Leaflet can render locally cached tiles and offline GeoJSON datasets, which is vital for disaster applications where cloud connectivity may be impaired.

#### Q8. How did you resolve the Leaflet map grey rendering artifact observed during testing?
**Answer**:  
During development, when asynchronous API cards (hazards, hospitals, shelters) loaded in the sidebar, the CSS Grid stretched the parent `.map-panel` downward. Because Leaflet has no native `ResizeObserver`, its internal viewport size (`map.getSize()`) remained fixed at its initial mount height, leaving the newly expanded bottom canvas unpopulated and exposing Leaflet's default grey `#ddd` background.  
We resolved this by:
1. Developing a `MapAutoResizer` React-Leaflet component using a native `ResizeObserver` that calls `map.invalidateSize()` whenever container dimensions change.
2. Implementing symmetric viewport heights in CSS (`height: min(calc(100vh - 48px), 820px)` with `position: sticky; top: 24px;`).
3. Setting `.leaflet-container { background: #0d1522 !important; }` so unrendered areas match the dark design system.

---

### Category 3: Graph Routing Engine, Dijkstra & Detours

#### Q9. How is the road network represented and stored in the system?
**Answer**:  
The road network is modeled as a directed multi-graph (`MultiDiGraph`) in NetworkX, constructed from an OpenStreetMap GraphML export of the Hyderabad urban area (`hyderabad_road_network.graphml`). It contains over 100,000 nodes (intersections) and 200,000 directed edges (road segments). Each edge stores topological length in meters, one-way constraints, and highway classifications.

#### Q10. How does the system snap user coordinates to the road graph?
**Answer**:  
When a user provides coordinates (e.g., latitude 17.3850, longitude 78.4860), the backend snaps them to the nearest physical road network node. Initially, standard OSMnx `nearest_nodes` converted the entire graph into a GeoPandas GeoDataFrame on every query, causing heavy memory allocations and `MemoryError` during large test runs.  
We optimized this by extracting node coordinates once at startup into a SciPy `cKDTree`. The spatial tree queries nearest neighbors using Euclidean distance in sub-millisecond time ($< 0.1\text{ ms}$), followed by exact Haversine distance calculation.

#### Q11. How does the routing algorithm avoid flooded roadways?
**Answer**:  
We use Dijkstra’s shortest path algorithm with dynamic edge weighting:
1. Before pathfinding, the routing service checks which graph edges intersect active flood hazard polygons.
2. Intersecting edges are assigned an extreme penalty weight ($w_{\text{flood}} = 10^6 \times \text{length}$).
3. Dijkstra’s algorithm finds the path of minimum total weight. Because traveling across a flooded edge costs millions of equivalent meters, the algorithm naturally seeks unpenalized detour corridors (e.g., elevated flyovers instead of low-level causeways).
4. The system compares the result against the unpenalized shortest path. If the paths differ, it sets `rerouted: true` and logs the detour reason.

#### Q12. What is `NO_SAFE_ROUTE` and why is it essential?
**Answer**:  
`NO_SAFE_ROUTE` is a safety fail-safe state. If a citizen is in an area where every surrounding exit road is severed by flood polygons, forcing a route would require traversing flooded edges. Instead of outputting an unsafe path or crashing silently with `NetworkXNoPath`, SafeMap AI catches the exception, flags status `NO_SAFE_ROUTE`, and provides clear life-safety guidance: advising the citizen not to enter floodwaters and to seek immediate elevated vertical shelter (upper floors of sturdy buildings).

#### Q13. Are the evacuation routes calculated by SafeMap AI guaranteed to be safe?
**Answer**:  
**No**. The routes avoid *documented, modeled, and reported* flood hazards present in the system's database. They are **not guaranteed safe** because unmonitored roads may suffer localized drain clogs, flash flooding, or tree falls that have not yet been reported to municipal databases. The application explicitly displays a disclaimer: *"Routes avoid known blocked road segments, but unmonitored roads are not guaranteed clear."*

---

### Category 4: Spatial Analysis, Point-in-Polygon & Hazard Mapping

#### Q14. What algorithm is used to determine if a citizen is inside a flood zone?
**Answer**:  
We use the **Ray-Casting Point-in-Polygon (PIP)** algorithm implemented via Shapely:
- A conceptual horizontal semi-infinite ray is cast from the query point $(x, y)$ in the positive X-direction.
- The algorithm counts how many times the ray intersects the polygon's boundary edges.
- If the intersection count is odd, the point is strictly inside the polygon. If even or zero, it is outside.
- For point hazards (e.g., a reported flooded underpass), we apply the **Haversine formula** with a 150-meter proximity buffer.

#### Q15. Where do the flood hazard zones in your system come from?
**Answer**:  
The flood hazard zones in SafeMap AI are derived from two primary sources:
1. **Historical Authoritative Corridors**: Modeled after historical high-water events along the Musi River (e.g., the 2000 and 2020 floods where reservoir discharges inundated the Moosarambagh and Chaderghat causeways).
2. **Municipal Drainage & Hotspot Listings**: Low-lying waterlogging hotspots compiled from GHMC monsoon advisories.
3. **Demonstration Scenarios**: Explicitly labeled synthetic hazard polygons (`[DEMO]`) used for algorithm validation and interactive testing.

#### Q16. How does the system handle point hazards vs. polygon hazards?
**Answer**:  
- **Polygon Hazards**: Represent continuous spatial inundation zones (e.g., river overflow corridors, low-lying lake margins). Evaluated using Ray-casting PIP.
- **Point Hazards**: Represent localized obstructions (e.g., a submerged underpass, manhole overflow, fallen tree). Evaluated by calculating the great-circle Haversine distance between the user/road node and the hazard point; if distance $\le 150\text{ meters}$, the road is marked obstructed.

#### Q17. How does the application prevent claiming an unmonitored road is "safe"?
**Answer**:  
In early iterations, the UI displayed a green badge reading "Road Conditions: CLEAR" when no alerts existed. This was identified as a dangerous false assurance, because absence of evidence is not evidence of absence. We replaced that language with an honest, defensible phrase:  
`NO KNOWN HAZARD INTERSECTS THIS LOCATION (Unmonitored segments not guaranteed clear)`.

---

### Category 5: Machine Learning Safeguards & The 50km Boundary Guard

#### Q18. What machine learning model is included in the project?
**Answer**:  
The project integrates a Random Forest severity classification model trained on the national **INDOFLOODS** hydrological dataset, which pairs CWC catchment characteristics (area, slope, stream order) with 10-day antecedent rainfall to predict flood severity classes.

#### Q19. Why is automated flood prediction currently marked `MODEL_UNSUPPORTED` for Hyderabad?
**Answer**:  
The INDOFLOODS dataset is calibrated on specific river basins with active, continuous Central Water Commission (CWC) stream gauges. Hyderabad’s Musi River catchment does not have an active CWC hydrological gauge in the training dataset. The nearest calibrated reference gauge (Gauge 916) is **71.71 km away**. Because the model has never been calibrated on the urban Musi catchment, extrapolating predictions would be scientifically invalid and dangerous.

#### Q20. What is the 50 km Geographic Boundary Guard?
**Answer**:  
The 50 km boundary guard is an algorithmic policy enforced in `backend/app/services/recommendation.py` and `backend/app/services/risk_map.py`:
- When a prediction request is received for coordinates $(lat, lon)$, the service calculates the Haversine distance to the nearest calibrated INDOFLOODS gauge.
- If $distance \le 50.0\text{ km}$, model inference proceeds.
- If $distance > 50.0\text{ km}$, the system hard-blocks the model, returns HTTP 200 with status `INSUFFICIENT_LOCAL_DATA` / `MODEL_UNSUPPORTED`, and displays an explanatory banner.
- For Hyderabad, $71.71\text{ km} > 50.0\text{ km}$, so the model is suppressed.

#### Q21. Why is suppressing the model better than letting it output a prediction?
**Answer**:  
In safety-critical systems, **an uncalibrated prediction is worse than no prediction**. If an uncalibrated model outputs "Low Risk" during a torrential cloudburst, citizens might delay evacuation and drown. Conversely, if it outputs "High Risk" during light rain, it induces panic and erodes institutional trust. By honestly returning `INSUFFICIENT_LOCAL_DATA`, the system alerts citizens to seek local ground reports and civil defense bulletins, upholding the ethics of responsible AI.

---

### Category 6: Data Quality, Provenance & Facility Verification

#### Q22. How are hospitals and emergency shelters curated in SafeMap AI?
**Answer**:  
- **Hospitals**: Curated from public directories of the Telangana Directorate of Medical Education (DME) and Telangana Vaidya Vidhana Parishad (TVVP), including major centers like Osmania General Hospital, Gandhi Hospital, and Area Hospital Malakpet.
- **Shelters**: Curated from GHMC community halls, indoor stadiums, and school relief shelters identified in district disaster plans.
- Coordinates were verified using official municipal gazettes and OpenStreetMap geographic coordinates.

#### Q23. Why are hospital bed capacities and shelter occupancies left as `null` or `UNKNOWN`?
**Answer**:  
SafeMap AI enforces a strict **Truth-in-Data** standard. Because our prototype is not connected to a live, authoritative hospital bed telemetry API, fabricating synthetic bed numbers (e.g., claiming Osmania Hospital has 42 open ICU beds) would be fraudulent and dangerous during an emergency. We leave dynamic fields `null`, display `Unverified (UNKNOWN) — Operational status not confirmed`, and advise citizens to contact facilities directly.

#### Q24. What are the four data classification tiers used in SafeMap AI?
**Answer**:  
1. **AUTHORITATIVE**: Records originating directly from verified government bodies (e.g., CWC, IMD, Irrigation Department).
2. **PUBLIC_UNVERIFIED**: Data collected from public municipal directories or unvetted community listings.
3. **DEMO**: Synthetic scenarios clearly labeled for training, testing, or evaluative demonstrations.
4. **STALE**: Authoritative records that have passed their temporal validity window (e.g., an alert older than 24 hours).

#### Q25. How do you ensure cryptographic data provenance in the curation pipeline?
**Answer**:  
Every raw dataset in `data/raw/` is ingested through our automated curation pipeline (`curation_pipeline.py`). The importer calculates the **SHA-256 cryptographic hash** of the raw file and stores it in the curated JSON record. An immutable `audit_trail` dictionary tracks any normalization or correction. If a raw file is modified or corrupted, the checksum mismatch is immediately flagged by automated tests.

---

### Category 7: Security, Testing & Deployment Realities

#### Q26. How is Role-Based Access Control (RBAC) implemented?
**Answer**:  
SafeMap AI segregates public safety access from administrative operations:
- **Public Endpoints**: `/health`, `/flood-hazards`, `/emergency-facilities`, `/evacuation-route`, and `/weather` require **zero authentication**, ensuring citizens in distress have instant access.
- **Administrative Endpoints**: Data ingestion, manual hazard injection, and manifest curation require API keys passed via `X-Admin-API-Key` or `X-Analyst-API-Key` headers, enforced via FastAPI dependency injection.

#### Q27. How does the system handle security credentials and secret redaction?
**Answer**:  
1. All real secrets and `.env` files are strictly excluded from version control via `.gitignore` and `.dockerignore`.
2. Template files (`.env.example`) contain only placeholder strings.
3. A structured logging utility (`observability.py`) automatically scrubs API keys, passwords, and database connection strings, replacing them with `[REDACTED]` before emitting JSON logs.
4. An automated test (`test_no_developer_specific_absolute_paths_in_repository`) ensures no absolute local paths or credentials appear in project documentation.

#### Q28. What are your actual test results?
**Answer**:  
The backend test suite consists of **311 automated tests** executed with `pytest`:
- **Result**: **311 passed, 0 failed, 41 warnings** in **158.59 seconds**.
- Coverage spans Dijkstra routing, detour generation, `NO_SAFE_ROUTE` fallback, Ray-casting PIP checks, emergency facility filtering, RBAC authentication, secret redaction, and curation idempotency.
- The frontend production bundle compiles cleanly with Vite in **248 milliseconds** (59 transformed modules).

#### Q29. Is Docker deployed, and what are the deployment requirements?
**Answer**:  
Multi-container Docker deployment is fully configured via `docker-compose.yml`, backend/frontend Dockerfiles, and Nginx reverse proxy configs (`nginx.conf`). However, because Docker Engine is not installed on the local Windows development machine, the application was verified through local bare-metal execution (FastAPI Uvicorn daemon on port 8000 and Vite development server daemon on port 5173). Complete instructions for launching on a Docker-enabled staging machine are documented in [`docs/deployment_and_operations_guide.md`](deployment_and_operations_guide.md).

#### Q30. If you had six more months to work on this project, what would you add?
**Answer**:  
1. **IoT Stream Gauge Integration**: Partner with GHMC and Irrigation Department to ingest live water-level telemetry from ultrasonic sensors along the Musi River, allowing us to calibrate and activate the ML prediction model.
2. **Satellite Synthetic Aperture Radar (SAR)**: Ingest ISRO Bhuvan / Sentinel-1 SAR imagery for cloud-penetrating water detection during active monsoon storms.
3. **High-Resolution Urban DEM**: Incorporate sub-5-meter Digital Elevation Models and stormwater drainage (nala) network layers for street-level water flow simulation.
4. **Live Hospital API Integration**: Connect with official health department telematics for real-time bed and emergency room capacity tracking.
