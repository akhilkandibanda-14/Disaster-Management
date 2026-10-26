# SafeMap AI — Five-Minute Academic & Stakeholder Demonstration Script
## Step-by-Step Interactive Demonstration Protocol for Flood Emergency Decision Support

---

### Academic Presentation Metadata
- **Project Title**: SafeMap AI — Flood Management & Hazard-Aware Evacuation Support System
- **Presenter Name**: `[Student Name]`
- **Roll / Student ID**: `[Roll / Hall Ticket Number]`
- **Department**: `[Department of Computer Science and Engineering / Information Technology]`
- **College / University**: `[College / University Name]`
- **Project Supervisor**: `[Project Guide / Supervisor Name]`
- **Date of Demonstration**: `[Presentation Date]`

---

### Demonstration Ground Rules & Integrity Notice

> **PRESENTATION SAFEGUARD**  
> All simulated hazard corridors and road blockages used in this demonstration are explicitly labeled **[DEMO]** or **PUBLIC_UNVERIFIED**. The presenter must clearly explain to evaluators that this demonstration shows architectural and algorithmic correctness in an academic decision-support prototype, not real-time civil protection deployment.

---

### Timing Overview (Total: 5 Minutes)

| Step | Time | Demonstration Action | Key Takeaway / Evaluator Check |
| :---: | :---: | :--- | :--- |
| **1** | 0:00 – 0:30 | Problem Statement & Motivation | Urban flash floods trap evacuees when standard GPS ignores inundation. |
| **2** | 0:30 – 1:00 | Main Flood Map & Legend Inspection | Dark-mode high-contrast visualizer with distinct colored symbology. |
| **3** | 1:00 – 1:30 | Official Alerts & Source Attribution | Red alert banner showing Musi River corridor with explicit source metadata. |
| **4** | 1:30 – 2:00 | Hyderabad Model Boundary Safeguard | Explanation of the 50km INDOFLOODS boundary; why `MODEL_UNSUPPORTED` is honest AI. |
| **5** | 2:00 – 2:30 | Emergency Facility Discovery | Browsing hospitals vs. shelters; filtering by facility type. |
| **6** | 2:30 – 3:15 | Hazard-Aware Evacuation Routing | Calculating safe evacuation route avoiding flooded causeways. |
| **7** | 3:15 – 3:45 | Blocked-Road Detour Demonstration | Live scenario showing dynamic detour selection (`rerouted: true`). |
| **8** | 3:45 – 4:15 | `NO_SAFE_ROUTE` Safeguard State | Trapped scenario triggering vertical shelter guidance rather than unsafe path. |
| **9** | 4:15 – 4:45 | Data Integrity & Verification Labels | Explaining `PUBLIC_UNVERIFIED` and why unknown bed capacity is never fabricated. |
| **10** | 4:45 – 5:00 | System Limitations & Future Roadmap | Next steps for CWC gauge integration and live sensor telemetry. |

---

### Detailed Step-by-Step Script

#### Step 1 — Introduce the Flood-Management Problem (0:00 – 0:30)
- **Presenter Action**: Open browser to `http://127.0.0.1:5173/`. Point to the header: **SafeMap AI · Flood Response System**.
- **Spoken Narration**:
  > *"Welcome. Urban flash floods in Hyderabad frequently submerge causeways and arterial underpasses along the Musi River corridor within minutes of upstream reservoir discharges. Consumer navigation apps optimize for traffic and travel time, meaning they routinely direct fleeing drivers directly into submerged roadways. SafeMap AI was designed as a responsible, hazard-aware decision-support prototype that merges municipal flood hazard boundaries with graph routing to compute safe, verified evacuation detours."*
- **Expected Visual**: The application loads with the Citizen View active, showing the navigation bar, live alert banners, and the interactive map panel.

#### Step 2 — Open the Flood Map and Explain Its Legend (0:30 – 1:00)
- **Presenter Action**: Scroll slightly to bring the interactive Leaflet map into full view. Point out the floating legend at the bottom left.
- **Spoken Narration**:
  > *"On the left is our interactive spatial console. Notice the floating visual legend. Every marker and line style represents an explicit entity: blue dots for user coordinates, green for community shelters, purple for hospitals, solid red lines for flooded roadways, and orange dashed outlines for municipal flood zones. The blue solid path represents standard OpenStreetMap roads, while dashed orange paths designate calculated hazard detours."*
- **Expected Visual**: Leaflet map rendered cleanly with zero grey gaps, displaying OSM inverted dark tiles, hospital/shelter pins, and the floating legend.

#### Step 3 — Show Available Flood Alerts and Source Information (1:00 – 1:30)
- **Presenter Action**: Direct attention to the red alert banner: **ACTIVE FLOOD HAZARD AT YOUR LOCATION (HIGH SEVERITY)**.
- **Spoken Narration**:
  > *"At the top of the interface, SafeMap AI performs instantaneous spatial Point-in-Polygon (PIP) checks against the user's coordinates. Here, our coordinates (17.3850, 78.4860) intersect the Musi River Central Causeway Inundation Corridor. Notice that the system provides clear source attribution: it is marked `HIGH` severity and `PUBLIC_UNVERIFIED`, citing upstream reservoir releases from Osman Sagar and Himayat Sagar. We also prominently display our safety limitation notice: the absence of an alert never guarantees safety."*
- **Expected Visual**: Red warning banner clearly visible with full descriptive text, classification tags, and disclaimer.

#### Step 4 — Explain the Hyderabad Model Limitation (1:30 – 2:00)
- **Presenter Action**: Point to the amber alert banner: **FLOOD PREDICTION UNAVAILABLE: INSUFFICIENT LOCAL DATA**.
- **Spoken Narration**:
  > *"A critical pillar of responsible AI is knowing when to say 'I do not know'. Many disaster AI tools extrapolate predictions across uncalibrated basins. Our INDOFLOODS machine learning model requires an authoritative river gauge within 50 kilometers. The nearest available gauge is 71.71 km away. Because 71.71 km exceeds our 50.0 km policy limit, SafeMap AI hard-blocks automated prediction and displays `INSUFFICIENT_LOCAL_DATA`. It refuses to fabricate an unvalidated safety score."*
- **Expected Visual**: Amber card displaying distance `71.71 km`, policy limit `50 km`, and explicit suppression notice.

#### Step 5 — Select a Hospital or Shelter (2:00 – 2:30)
- **Presenter Action**: In the sidebar under **Evacuation Destination**, click the **Hospitals (7)** tab. Click on **District Hospital King Koti** (0.30 km away).
- **Spoken Narration**:
  > *"In the sidebar, citizens can browse verified emergency facilities. We can filter between hospitals and shelters. Let's select District Hospital King Koti, located 300 meters from our position. The facility card immediately updates with its address, distance, and directory source."*
- **Expected Visual**: Facility card updates to show King Koti Hospital selected, highlighting distance and directory details.

#### Step 6 — Calculate an Evacuation Route (2:30 – 3:15)
- **Presenter Action**: Click the blue button: **Calculate Hazard-Aware Evacuation Route**.
- **Spoken Narration**:
  > *"When we click 'Calculate Hazard-Aware Evacuation Route', the FastAPI backend queries our in-memory OpenStreetMap graph. Coordinates are snapped to the road network using a cached KDTree in sub-millisecond time. The pathfinder applies Dijkstra's algorithm, heavily penalizing any edge intersecting an active flood polygon. Within 150 milliseconds, the safe route is plotted on the map in blue."*
- **Expected Visual**: The map automatically centers and fits bounds around the calculated route, rendering the blue line string connecting the citizen location to King Koti Hospital.

#### Step 7 — Demonstrate Blocked-Road Avoidance (Scenario Detour) (3:15 – 3:45)
- **Presenter Action**: Select **GHMC Community Hall** across the river corridor and calculate route.
- **Spoken Narration**:
  > *"Now let's examine a scenario where the direct shortest path crosses the flooded Moosarambagh causeway. Instead of routing through the water, the routing engine detects the flood hazard intersection, applies an infinite weight to the flooded causeway, and forces the route westward across the elevated, flood-safe Chaderghat flyover. The UI marks this route as `REROUTED`, displaying an explicit detour explanation."*
- **Expected Visual**: The route line bends around the hazard polygon, with the sidebar displaying the detour notice.

#### Step 8 — Demonstrate `NO_SAFE_ROUTE` State (3:45 – 4:15)
- **Presenter Action**: Reference the system's tested negative control: simulated flood encirclement.
- **Spoken Narration**:
  > *"What happens if all road corridors leading out of the neighborhood are impassable? Rather than failing silently or directing evacuees into floodwaters, SafeMap AI returns `NO_SAFE_ROUTE`. The application alerts the user that all ground transit is compromised and advises them to seek elevated vertical shelter immediately while broadcasting distress coordinates."*
- **Expected Visual**: High-visibility warning displaying `NO_SAFE_ROUTE` with vertical shelter advisory.

#### Step 9 — Show How Unverified Facilities and DEMO Data Are Labeled (4:15 – 4:45)
- **Presenter Action**: Scroll down the sidebar to the **Data Integrity & Safety Boundaries** section.
- **Spoken Narration**:
  > *"Notice our strict data integrity safeguards. All municipal shelter listings are labeled `PUBLIC_UNVERIFIED`. Live emergency bed counts and ICU capacities are left `null` and displayed as `UNKNOWN` rather than fabricated. Synthetic test scenarios are watermarked `[DEMO]`. We never present simulated drills as real-world civil emergencies."*
- **Expected Visual**: The Data Integrity card clearly visible, showing bold labels: `PUBLIC_UNVERIFIED`, `never fabricated`, and `[DEMO]`.

#### Step 10 — System Limitations and Future Roadmap (4:45 – 5:00)
- **Presenter Action**: Click the **Operations** button in the topbar to briefly display the administrative overview, then return to Citizen View for conclusion.
- **Spoken Narration**:
  > *"To conclude: SafeMap AI delivers defensible, explainable disaster decision support. Our immediate future roadmap focuses on integrating live CWC IoT river-stage telemetry to bridge the local data gap, followed by real-time hospital triage telematics. Thank you, and we welcome your questions."*
- **Expected Visual**: Operations dashboard with summary metrics displayed cleanly, demonstrating end-to-end system cohesion.
