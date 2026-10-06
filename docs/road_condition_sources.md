# Real-Time Road Condition Sources Investigation

## Objective
Investigate sources of real-time road condition data (specifically flood inundation, road closures, and traffic incidents) in Hyderabad, Telangana. The goal is to identify a reliable, real-time, dynamic data source that does not require an API key.

## Static vs. Dynamic Data Distinction
It is critical to distinguish between two types of road data:
- **Static Data:** Road geometry, network topology, speed limits, road type, and permanent hazard zones. (Does not change minute-by-minute).
- **Dynamic Data:** Current road closures, active flooding, localized waterlogging, temporary blockages, and live traffic. (Requires real-time streaming).

For disaster routing and shelter recommendations, we require **Dynamic Data**.

## Sources Investigated

| Source | Type | Hyderabad Coverage | Current Conditions | Authentication | Reliability | Recommended? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **HYDRAA / GHMC** | Official Gov Portal | Yes (Complete) | No (No Public API) | N/A | High (for reports) | **No** (No REST API) |
| **Telangana State GIS (TGRAC)** | ArcGIS REST Service | Yes (Complete) | No (Static network only)| None (for public layers)| High (for geometry) | **No** (Static only) |
| **OpenStreetMap (Overpass)**| Crowdsourced GIS | Yes (Complete) | No (Static hazard tags) | None | Medium | **No** (Static only) |
| **Waze for Cities** | Real-time Traffic | Yes (Partial) | Yes | **Requires API Key** | High | **No** (Key needed) |
| **Google Maps Platform** | Real-time Routing | Yes (Complete) | Yes | **Requires API Key** | High | **No** (Key needed) |
| **Mapbox Traffic API** | Real-time Traffic | Yes (Complete) | Yes | **Requires API Key** | High | **No** (Key needed) |

## Source Analysis

### 1. HYDRAA / GHMC (Official Local Sources)
- **Status:** The Hyderabad Disaster Response and Asset Protection Agency (HYDRAA) and the Greater Hyderabad Municipal Corporation (GHMC) manage disaster response, but **they do not expose a public real-time JSON/REST API** for dynamic road inundations. Information is typically shared via internal dashboards, PDF bulletins, press releases, or social media updates.
- **Verdict:** Unusable for programmatic, real-time ingestion without manual data scraping, which is brittle and unreliable.

### 2. Telangana State GIS / TGRAC
- **Status:** Hosts extensive spatial data via ArcGIS REST API. While excellent for pulling the static road geometry (National Highways, State Highways), it explicitly lacks live-updating "flooded road" conditions. 
- **Verdict:** Cannot provide real-time dynamic conditions.

### 3. OpenStreetMap (OSM)
- **Status:** Highly accessible via Overpass API with no key required. However, OSM explicitly discourages mapping real-time, rapidly changing data (like hourly flood status). It provides static tags (e.g. `hazard=flooding`), but this denotes historical vulnerability, not active waterlogging.
- **Verdict:** Excellent for static geometry, but unusable for live condition tracking.

### 4. Commercial APIs (Google Maps, Mapbox, Waze)
- **Status:** These are the only reliable sources of true real-time road closure and traffic data for the region. However, **all of them strictly require API keys**, and in the case of Waze for Cities, a direct partnership agreement.
- **Verdict:** Excluded due to the project's strict "No API Key" policy.

## Conclusion and Recommendations

1. **Official Sources:** GHMC and HYDRAA are the authorities, but they lack public real-time APIs.
2. **No-Key Sources:** OSM and TGRAC exist but only offer static road networks.
3. **API Key Sources:** Google Maps, Mapbox, and Waze have the required data but violate the API key constraint.
4. **Best Recommended Source:** There is **no suitable, unauthenticated, real-time road condition API** publicly available for Hyderabad. 

To maintain system integrity and avoid fabricating safety metrics, the system must either:
- Introduce a mock/demo road-condition service (similar to the hydrology approach) for architectural demonstration.
- Omit real-time dynamic routing and continue to rely on geographic distance until an official open-data portal is launched by the Telangana Government.
