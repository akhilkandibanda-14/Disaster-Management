# Shelter Recommendation API

## Architecture
The Shelter Recommendation service acts as an orchestration layer connecting the `ShelterService` and the `RiskMapService`. It fetches candidate shelters geographically, queries the local ML-based geographic risk model to establish environmental context, ranks the shelters according to a distance-based formula, and wraps the result in an explicit API schema that prioritizes data integrity.

## Candidate Selection
The service takes the user's location (`latitude`, `longitude`) and retrieves candidate shelters using the `ShelterService`. The `ShelterService` filters these geographically based on the requested `radius_km`. Missing or invalid coordinates are excluded at the data-loading level.

## Distance Formula
The system calculates distances from the user to candidate shelters using the Haversine formula, providing a great-circle geographic distance in kilometers.

## Current Ranking Formula
For the current prototype, candidate shelters are ranked transparently based on distance. The formula is:
```
distance_score = max(0, 1 - distance_km / radius_km)
candidate_score = distance_score
```
This implies the closer the shelter, the higher its score.

## Why Full Safety Weighting Cannot Yet Be Used
The original conceptual weighting factored in disaster safety (40%), road safety (25%), capacity (15%), accessibility (10%), and distance (10%). However, we cannot use this full weighting currently because:
- **Road Safety:** Not implemented yet.
- **Missing Capacity:** We have no valid data on shelter sizes.
- **Missing Occupancy:** We have no real-time data on how many people are already there.
- **Unknown Operational Status:** We cannot verify if a candidate shelter is actually open.
- **Unknown Accessibility:** We do not know if the shelters are accessible to everyone.
- **Unverified Shelter Safety:** We cannot independently verify that these candidate shelters are actually safe from flooding (they are PUBLIC_UNVERIFIED).

To maintain integrity and avoid fabricating numbers, we must rank solely based on what we can verify (distance).

## 50 km ML Coverage & Out-of-Coverage Behavior
The ML geographic risk model operates strictly within a 50 km radius of known INDOFLOODS gauges. 
- If the user's location is inside this coverage, the API returns the predicted risk context.
- If the user is outside this coverage, the system returns `prediction_available = false` and `coverage_status = "MODEL_UNSUPPORTED"`. It **does not** fabricate a flood risk context. The candidate shelters are still recommended, but the limitation "Risk-based shelter assessment is unavailable for this location" is prominently surfaced.

## Limitations
- Shelter flood safety has not been independently verified.
- Shelter capacity is unavailable.
- Current occupancy is unavailable.
- Operational status is unknown.
- Real-time road safety is not integrated.
- Ranking is currently distance-based.

## Future Improvements
Future ranking factors (which MUST NOT be implemented now) should include:
1. Verified flood safety
2. Real operational status
3. Capacity
4. Current occupancy
5. Accessibility
6. Real road safety
7. Distance
8. Dynamic routing

## API Key Status
**NO API KEY REQUIRED.** This service uses historical rainfall data (Open-Meteo) and pre-trained models. No paid mapping, geocoding, or external services are used.
