# SafeMap AI — Project Abstract
## An Explainable, Hazard-Aware Decision-Support System for Flood Emergency Response and Safe Evacuation

---

### Academic Submission Details

| Field | Detail |
| :--- | :--- |
| **Project Title** | SafeMap AI: Flood Management and Evacuation Support System |
| **Degree / Course** | Bachelor of Technology (B.Tech) in Computer Science and Engineering / Information Technology |
| **Student Name** | `[Student Name]` |
| **Roll / Registration No.** | `[Roll / Hall Ticket Number]` |
| **Department** | `[Department of Computer Science and Engineering / Information Technology]` |
| **College / Institute** | `[College / University Name]` |
| **Project Supervisor** | `[Project Guide / Supervisor Name, Designation]` |
| **Academic Session** | `[Academic Year, e.g., 2025–2026]` |
| **Date of Submission** | `[Submission Date]` |

---

### Abstract

#### 1. Background
Urban flash flooding has emerged as an acute public safety hazard in rapidly expanding metropolitan centers across India. During intense South-West monsoon storms and upstream reservoir discharges, arterial roadways, low-lying causeways, and underpasses in cities such as Hyderabad submerge rapidly, stranding residents and severing emergency access corridors. 

#### 2. Problem Statement
Commercial navigation platforms (such as Google Maps) prioritize traffic volume and shortest travel time. During floods, as vehicles abandon inundated roads, conventional navigation algorithms falsely interpret the cleared roads as optimal shortcuts, directing fleeing citizens directly into submerged waterways. Furthermore, modern AI-driven disaster prototypes frequently suffer from uncalibrated extrapolation, outputting unvalidated flood risk scores for river basins that completely lack physical stream gauge monitoring.

#### 3. Proposed System
SafeMap AI is an explainable, hazard-aware decision-support prototype engineered to bridge municipal flood intelligence with spatial graph routing. The platform couples an OpenStreetMap road network graph with active flood hazard polygons to calculate verified evacuation detours around submerged causeways. Crucially, SafeMap AI incorporates responsible machine learning safeguards, strictly suppressing automated flood prediction when local river gauge data is insufficient rather than generating misleading or hazardous estimates.

#### 4. Main Implemented Features
- **Spatial Point-in-Polygon (PIP) Hazard Detection**: Rapidly identifies whether citizen coordinates or road segments intersect active flood polygons using Ray-casting and a 150-meter Haversine buffer.
- **Hazard-Aware Dijkstra Evacuation Routing**: Penalizes flooded road segments ($w_{\text{flood}} = 10^6 \times \text{length}$) to compute optimal detour corridors while flagging `rerouted: true` with human-readable rationale.
- **`NO_SAFE_ROUTE` Life-Safety Fail-Safe**: Catches severed-network encirclement and advises evacuees to seek immediate elevated vertical shelter rather than traversing hazardous water.
- **Transparent Emergency Facility Catalog**: Curates 7 major hospitals and 11 community relief shelters with distance metrics, explicit `PUBLIC_UNVERIFIED` tags, and unconfirmed capacity labels.
- **Explainable ML Boundary Guard**: Enforces a strict 50-kilometer proximity threshold from calibrated river gauges. Because Hyderabad’s nearest gauge is 71.71 km away, automated predictions gracefully return `INSUFFICIENT_LOCAL_DATA` / `MODEL_UNSUPPORTED`.
- **Dual Presentation Dashboards**: Delivers an interactive Citizen View for personal route planning and an Operations View for regional municipal telemetry.

#### 5. Technology Stack
- **Frontend Presentation Tier**: React 19, Vite 8, Leaflet 1.9, React-Leaflet 5, Vanilla CSS Design System with dark-mode tile inversion and `ResizeObserver` container synchronization.
- **Backend Services Tier**: Python 3.13, FastAPI asynchronous REST API, Uvicorn server, Pydantic v2 data models, Role-Based Access Control (RBAC).
- **Spatial & Graph Computation**: NetworkX directed drive graph (100,000+ nodes), OSMnx, SciPy (`cKDTree`) for sub-millisecond coordinate snapping, Shapely spatial geometry.
- **Data Curation & Provenance**: Pandas, NumPy, SHA-256 cryptographic provenance verification, GeoJSON stores.

#### 6. Testing Summary
The system has been thoroughly validated through an automated test suite consisting of **311 passing backend tests** (0 failed, 41 warnings) executed in **158.59 seconds** via `pytest`. The test suite covers Dijkstra routing, detour generation, `NO_SAFE_ROUTE` fallback, spatial PIP checks, emergency facility filtering, RBAC authentication, and pipeline idempotency. The frontend production bundle compiles cleanly via Vite in **248 milliseconds** with zero warnings or errors.

#### 7. Limitations and Conclusion
SafeMap AI demonstrates an ethically grounded, technically sound prototype for disaster informatics. Current operational limitations include the absence of continuous automated stream-gauge telemetry on the Musi River and lack of dynamic hospital bed APIs. The system avoids deceptive claims by explicitly labeling unmonitored roads as unverified and suppressing uncalibrated AI predictions. In disaster informatics, responsible engineering is defined as much by what a system refuses to fabricate as what it computes. SafeMap AI provides an academically defensible foundation for next-generation urban disaster decision support.

---

### Keywords
Disaster Informatics, Flood Management, Evacuation Routing, Dijkstra's Algorithm, Point-in-Polygon (PIP), Spatial Graph Analysis, Responsible AI, OpenStreetMap, FastAPI, React Leaflet.
