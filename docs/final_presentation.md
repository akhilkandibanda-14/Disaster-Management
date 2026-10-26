# SafeMap AI — Final Academic Presentation Outline
## Flood Management and Hazard-Aware Evacuation Support System

---

### Academic Presentation Metadata

- **Project Title**: SafeMap AI — Flood Management & Hazard-Aware Evacuation Support System
- **Domain**: Urban Disaster Informatics, Spatial Analysis, and Responsible Machine Learning
- **Student Name**: `[Student Name]`
- **Roll / Student ID**: `[Roll / Hall Ticket Number]`
- **Department**: `[Department of Computer Science and Engineering / Information Technology]`
- **Institution**: `[College / University Name]`
- **Project Supervisor**: `[Project Guide / Supervisor Name]`
- **Academic Year**: `[Academic Year, e.g., 2025–2026]`
- **Date of Presentation**: `[Presentation Date]`

---

## Slide 1: Title Slide

### SafeMap AI: Flood Management and Evacuation Support System
**Subtitle**: An Explainable, Hazard-Aware Decision-Support System for Flood Emergency Response and Safe Evacuation

- **Candidate**: `[Student Name]` (`[Roll / Hall Ticket Number]`)
- **Department**: `[Department Name]`, `[College / University Name]`
- **Under the Guidance of**: `[Project Guide Name, Designation]`
- **Project Repository**: SafeMap AI (Undergraduate Capstone Project)

**Suggested Visual**:
- Project title block with dual institutional logo placeholders and a clean dark-themed thumbnail of the application interface (`docs/screenshots/01_main_flood_map_and_legend.png`).

**Speaker Notes**:
> *"Good morning respected evaluators, project guide, and committee members. Today I am presenting SafeMap AI, an AI-assisted and geospatial decision-support prototype engineered specifically for urban flood emergencies and hazard-aware evacuation routing. This project demonstrates how combining spatial graph routing with strict machine learning boundary safeguards produces transparent, defensible disaster informatics."*

---

## Slide 2: Problem Statement and Motivation

### Why Traditional Navigation Fails in Urban Flash Floods

- **The Urban Flash Flood Reality**: During heavy monsoon downpours and sudden reservoir releases (e.g., Osman Sagar & Himayat Sagar into the Musi River), low-lying causeways and arterial underpasses flood within minutes.
- **Consumer Navigation Blindspots**: Commercial platforms (Google Maps, Apple Maps) optimize strictly for traffic volume and speed. They do not ingest municipal flood warnings, hydrological levels, or causeway submersion alerts.
- **The Evacuation Hazard**: Fleeing drivers are frequently routed into submerged underpasses and submerged causeways because those routes appear free of ordinary vehicular traffic.
- **The "Black-Box" Extrapolation Trap**: Existing academic AI disaster models often fabricate high-confidence flood forecasts across regions where no physical gauge calibration data exists.

**Suggested Visual**:
- Comparative diagram: Consumer GPS routing an evacuee directly across a flooded causeway vs. SafeMap AI detecting the hazard polygon and calculating an alternate bridge detour.

**Speaker Notes**:
> *"The motivation behind SafeMap AI stems from a recurring urban catastrophe. When monsoon floods strike cities like Hyderabad, arterial roads and low-level causeways submerge rapidly. Standard consumer GPS tools only optimize for travel time and traffic delays. When a causeway floods, traffic clears, causing conventional GPS algorithms to view it as an optimal, clear shortcut. Evacuees are directed into life-threatening water. SafeMap AI solves this by integrating active flood boundaries into graph pathfinding."*

---

## Slide 3: Project Objectives and Scope

### Defined Objectives & Explicit Boundaries

- **Primary Objectives**:
  1. Build a high-performance spatial routing engine that detects road-hazard intersections and computes verified detours.
  2. Implement an explainable ML coverage guard that rejects uncalibrated extrapolation (`MODEL_UNSUPPORTED`).
  3. Curate emergency facilities (hospitals, relief shelters) with transparent public verification states.
  4. Ensure end-to-end cryptographic data provenance (SHA-256) and Role-Based Access Control (RBAC).
- **Project Scope Constraints**:
  - **Flood-Only Focus**: Strictly evaluates flood inundation; rejects multi-disaster creep to maintain scientific rigor.
  - **Decision-Support Prototype**: Academic demonstration system; passing tests confirms structural validity, not field-certified operational safety.
  - **Geographic Area**: Hyderabad Metropolitan Area (tested against external catchments as negative controls).

**Suggested Visual**:
- Two-column layout contrasting "In-Scope Capabilities" (Flood PIP checks, Dijkstra detours, 50km coverage guard) against "Explicit System Boundaries" (Flood only, no uncalibrated ML extrapolation, no fabricated hospital telemetry).

**Speaker Notes**:
> *"Our project objectives focus on four pillars: hazard-aware graph routing, explainable ML boundary enforcement, emergency facility discovery, and cryptographic data provenance. Crucially, our scope is strictly limited to flood emergencies. We consciously rejected multi-hazard creep such as earthquakes or fires to maintain deep domain rigor. Furthermore, we explicitly acknowledge that SafeMap AI is a decision-support prototype, not a certified emergency dispatch system."*

---

## Slide 4: Proposed Solution and Key Features

### The SafeMap AI Decision-Support Platform

- **Point-in-Polygon (PIP) Hazard Detection**: Rapidly intersects user coordinates and road links against active flood polygons using Ray-casting and a 150m Haversine buffer.
- **Hazard-Aware Dijkstra Routing**: Applies dynamic penalties ($10^6\times$) to flooded edges, yielding unblocked, explainable detour paths (`rerouted: true`).
- **`NO_SAFE_ROUTE` Fail-Safe**: If all accessible road segments are submerged, the system alerts evacuees and advises immediate vertical shelter rather than suggesting an unsafe route.
- **Transparent Emergency Facility Discovery**: Catalogs nearby hospitals and relief shelters with distance metrics, explicit `PUBLIC_UNVERIFIED` tags, and unconfirmed capacity labels.
- **Dual Presentation Dashboards**: Citizen view for personal route planning and an Operations view for municipal overview.

**Suggested Visual**:
- Screenshot of the Citizen View (`docs/screenshots/03_evacuation_routing_and_detour.png`) highlighting the active route line, detour note, and facility card.

**Speaker Notes**:
> *"Our proposed solution combines an interactive client interface with a FastAPI graph backend. The system evaluates user coordinates using Point-in-Polygon checks, routes users around submerged causeways using Dijkstra's algorithm with heavy hazard penalties, and safely falls back to `NO_SAFE_ROUTE` if all paths are blocked. In the sidebar, citizens can browse hospitals and shelters, where unknown values are left null rather than fabricated."*

---

## Slide 5: System Architecture and Technology Stack

### Decoupled Modular Architecture

- **Frontend Tier**: React 19, Vite 8, Leaflet 1.9, React-Leaflet 5, Vanilla CSS Design System with dark mode tile inversion and `ResizeObserver` map synchronization.
- **Backend API Gateway**: FastAPI, Uvicorn asynchronous server, Pydantic v2 schema validation, RBAC security middleware.
- **Graph & Spatial Computation**: NetworkX MultiDiGraph (100,000+ nodes), OSMnx, SciPy `cKDTree` for sub-millisecond node snapping, Shapely spatial geometry.
- **Data & Curation Engine**: Pandas, NumPy, SHA-256 cryptographic provenance pipeline, curated GeoJSON stores.

**Suggested Visual**:
- The complete system architecture flowchart from `docs/final_project_report.md` showing data flow between the Client Layer, API Gateway, Core Services Layer, and Graph Data Engine.

**Speaker Notes**:
> *"The system architecture is decoupled into three tiers. The frontend uses React 19 and Leaflet with a custom `ResizeObserver` component to prevent layout desynchronization. The backend is built on FastAPI and Python 3.13. For spatial computations, rather than making expensive external GIS calls, we load an OpenStreetMap drive graph into an in-memory NetworkX graph paired with a cached SciPy KDTree for instant coordinate snapping."*

---

## Slide 6: Flood Hazard Mapping and Data Sources

### Multi-Tiered Hazard Spatial Intelligence

- **Authoritative Flood Corridors**: Modeled after historical high-water events along the Musi River (e.g., downstream reservoir releases from Osman Sagar and Himayat Sagar).
- **Municipal Waterlogging Hotspots**: Low-lying arterial underpasses, railway bridges, and Moosarambagh/Chaderghat causeways.
- **Data Source Hierarchy**:
  1. *Authoritative*: Official irrigation department advisories and historical flood records.
  2. *Public Unverified*: Municipal directories and citizen inundation reports.
  3. *Demo / Simulated*: Explicitly labeled synthetic test scenarios (`[DEMO]`).
- **Spatial Evaluation Rule**: Ray-casting PIP for 2D flood polygons; 150m Haversine radius for point alerts.

**Suggested Visual**:
- Screenshot of the main flood map with active polygon overlays and the floating legend (`docs/screenshots/01_main_flood_map_and_legend.png`).

**Speaker Notes**:
> *"Flood hazards are represented as GeoJSON polygons and points. We establish a clear data hierarchy: Authoritative records from irrigation archives, Public Unverified listings from municipal directories, and synthetic test drills explicitly tagged [DEMO]. For spatial intersection, we execute ray-casting point-in-polygon tests for boundary zones and a 150-meter Haversine buffer for point hazards."*

---

## Slide 7: Hazard-Aware Evacuation Routing

### Dynamic Graph Rerouting & `NO_SAFE_ROUTE` Handling

- **Graph Model**: Directed OpenStreetMap network of Hyderabad ($> 100,000$ nodes, $> 200,000$ edges) with real topological distances.
- **Hazard Penalization**: Any edge intersecting an active flood polygon receives an edge weight multiplier of $w_{\text{flood}} = 10^6 \times \text{length}$.
- **Detour Generation**: The engine computes the unblocked shortest path, calculates extra detour distance, and flags `rerouted: true` with human-readable rationale.
- **The Encirclement Safeguard**: When all exit corridors are submerged, the engine refuses to output an unsafe route, returning status `NO_SAFE_ROUTE` and advising vertical shelter.

**Suggested Visual**:
- Side-by-side comparison: Normal unconstrained path vs. hazard detour avoiding the flooded Moosarambagh causeway via Chaderghat bridge (`docs/screenshots/03_evacuation_routing_and_detour.png`).

**Speaker Notes**:
> *"When a citizen requests an evacuation route, coordinates are snapped to the nearest road node using our cached KDTree. The routing engine checks every graph edge against active flood polygons. If an edge intersects a flood zone, its traversal cost is multiplied by one million. Dijkstra's algorithm naturally routes around the obstacle. If floodwaters encircle the origin completely, SafeMap AI returns `NO_SAFE_ROUTE`, telling citizens to seek high ground rather than driving into danger."*

---

## Slide 8: Hospital and Shelter Discovery

### Transparent Emergency Facility Registry

- **Curated Facility Catalog**:
  - *Hospitals*: 7 major tertiary and district hospitals (e.g., Osmania General Hospital, Gandhi Hospital, King Koti Hospital) with verified geographic coordinates.
  - *Shelters*: 11 community relief centers and municipal halls across Hyderabad divisions.
- **Integrity Boundary (Truth-in-Data)**:
  - Hospital bed availability, ICU capacity, and operational generator readiness default to `null` (`UNKNOWN`) because live sensor telemetry is not integrated.
  - All facility records are categorized as `PUBLIC_UNVERIFIED` until confirmed by civil defense officials.
  - We never fabricate synthetic bed counts to give an illusion of operational completeness.

**Suggested Visual**:
- Screenshot of the Emergency Facility Selection card showing King Koti Hospital and GHMC Community Hall with bold `PUBLIC_UNVERIFIED` disclaimers (`docs/screenshots/07_data_integrity_and_boundaries.png`).

**Speaker Notes**:
> *"For emergency facilities, we curated 7 major hospitals and 11 relief shelters from public records. Crucially, we enforce a strict 'truth-in-data' policy: because real-time hospital bed and generator telemetry is not connected, bed counts and operational statuses are left null and displayed as UNKNOWN. We never fabricate numbers. Every listing carries a prominent `PUBLIC_UNVERIFIED` disclaimer."*

---

## Slide 9: Data Quality, Safety Safeguards, and Model Limitations

### Responsible AI: Knowing When Not to Predict

- **The 50 km Geographic Boundary Guard**:
  - The INDOFLOODS machine learning model was trained on CWC river gauge basins.
  - The nearest calibrated gauge to Hyderabad (Gauge 916) is **71.71 km away**.
  - Because $71.71\text{ km} > 50.0\text{ km}$, the backend hard-blocks automated severity prediction.
- **Status `INSUFFICIENT_LOCAL_DATA`**: Transparently informs citizens and operators that local gauge telemetry is missing, preventing unvalidated AI extrapolation.
- **Road Condition Truth**: Unmonitored roads are labeled `NO KNOWN HAZARD INTERSECTS THIS LOCATION`, avoiding the false assurance of claiming an unmonitored road is "safe" or "clear".
- **Cryptographic Provenance**: 8 historical Hyderabad flood events tracked with raw SHA-256 hashes and immutable audit trails.

**Suggested Visual**:
- Screenshot of the amber Model Limitation banner showing the 71.71 km distance vs. 50.0 km policy limit (`docs/screenshots/02_flood_prediction_limitation.png`).

**Speaker Notes**:
> *"A key contribution of this project is its defense against uncalibrated machine learning. Our INDOFLOODS model has a strict 50-kilometer validity boundary. Hyderabad's nearest gauge is 71.71 km away. Rather than generating an unvalidated hallucinated prediction, the system suppresses the model and displays `INSUFFICIENT_LOCAL_DATA`. Furthermore, unmonitored roads are labeled 'no known hazard intersects this location', never 'clear'."*

---

## Slide 10: Testing and Implementation Results

### Comprehensive Automated Test Verification

- **Backend Test Suite Results**:
  - Total Tests: **311 passed**, 0 failed, 41 warnings.
  - Execution Duration: **158.59 seconds** (0:02:38).
  - Test Categories: Routing logic (21), flood hazard PIP (12), emergency facilities (12), deployment smoke (22), verification & CORS (19), data curation idempotency (25), and model boundary checks (175+).
- **Frontend Production Build**:
  - Transformed 59 client modules into optimized bundle in **248 milliseconds** via Vite.
- **Spatial Optimization**:
  - Replaced repetitive GeoDataFrame allocations with cached `cKDTree`, reducing nearest-node query time to $< 1$ millisecond and eliminating memory bottlenecks.

**Suggested Visual**:
- Table and terminal capture excerpt showing the `311 passed in 158.59s` summary and the `npm run build` output.

**Speaker Notes**:
> *"Our implementation has been rigorously validated. The backend test suite contains 311 automated tests, all of which pass cleanly in 158 seconds. These tests cover spatial intersection, Dijkstra routing, detour generation, RBAC security, and pipeline idempotency. The frontend production build compiles in 248 milliseconds. By caching KDTree spatial indexes, we achieved sub-millisecond node snapping on a 100,000-node graph."*

---

## Slide 11: Current Limitations and Future Enhancements

### Transparent Engineering Reality & Roadmap

- **Current Limitations**:
  1. *Telemetry Gap*: Absence of continuous automated river-stage sensors along the Musi River prevents real-time calibration.
  2. *Static Edge Speeds*: Routing calculates topological shortest paths with flood penalties, but does not yet ingest live vehicular traffic speeds.
  3. *Unverified Resource Telemetry*: Hospital bed occupancies and relief supplies are not connected to dynamic hospital APIs.
- **Future Enhancements**:
  1. Integrate IoT water-level sensor telemetry from GHMC and Telangana Irrigation Department.
  2. Ingest ISRO Bhuvan / Sentinel-1 SAR satellite flood-inundation raster overlays.
  3. Deploy high-resolution ($< 5\text{m}$) Digital Elevation Models (DEM) for micro-topographical street drainage modeling.

**Suggested Visual**:
- Roadmap timeline graphic showing Phase 1 (Current Prototype: Graph Routing & Boundary Guards), Phase 2 (IoT Sensor Integration), and Phase 3 (Satellite SAR & Live Telemetry).

**Speaker Notes**:
> *"We maintain full transparency regarding current system limitations. The lack of continuous Musi River stream gauge telemetry is why the ML model remains suppressed. For future work, we plan to integrate IoT ultrasonic water-level sensors deployed by municipal authorities, ingest cloud-penetrating Sentinel-1 SAR satellite imagery, and incorporate high-resolution digital elevation models for street-level runoff simulation."*

---

## Slide 12: Conclusion

### Defensible, Human-Centered Disaster Informatics

- **Core Accomplishment**: Successfully developed and demonstrated an explainable, hazard-aware decision-support prototype for urban flood emergencies.
- **Key Takeaways**:
  1. Hazard-aware pathfinding prevents evacuees from being directed into submerged causeways.
  2. Responsible AI requires transparent boundary enforcement (`MODEL_UNSUPPORTED`) rather than deceptive extrapolation.
  3. Decision-support systems must communicate data uncertainty through clear labeling (`PUBLIC_UNVERIFIED`, `[DEMO]`).
- **Academic Impact**: Proves that safety-critical disaster tools can maintain high performance while strictly enforcing ethical and statistical constraints.

**Suggested Visual**:
- Concluding slide with project title, candidate details, acknowledgments to supervisor, and "Thank You — Questions & Discussion" header.

**Speaker Notes**:
> *"In conclusion, SafeMap AI demonstrates that in disaster informatics, responsible AI is defined as much by what a system refuses to do as what it accomplishes. By uniting hazard-aware graph rerouting with honest model boundary enforcement and unverified resource warnings, we have built a defensible, academically rigorous prototype. Thank you for your time, and I am now ready for your questions."*
