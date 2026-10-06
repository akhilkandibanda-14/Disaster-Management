# Shelter API Documentation

## Overview

The Shelter API provides access to the shelter locations in the Hyderabad metropolitan area. The data is derived from the `hyderabad_shelters.csv` file.

**Important Data Notice:**
- **Verification Status:** `PUBLIC_UNVERIFIED`
- **Confirmation:** These are candidate shelter locations and have **NOT** been confirmed as emergency flood shelters by the authorities.
- **Missing Data:** Many fields (such as address, capacity, occupancy) are null because they are not provided in the source dataset. They are intentionally left as `null` and are not replaced with fabricated defaults.

## Endpoint

### `GET /shelters`

Returns a list of shelter locations.

**Query Parameters:**
- `latitude` (float, optional): Latitude of the user to calculate the distance from.
- `longitude` (float, optional): Longitude of the user to calculate the distance from.
- `radius_km` (float, optional): Radius in kilometers to filter the shelters. Requires `latitude` and `longitude` to be provided.

**Response Body:**
```json
{
  "total": 11,
  "shelters": [
    {
      "shelter_id": "HYD-S-001",
      "name": "Community Relief Center",
      "latitude": 17.4445,
      "longitude": 78.4630,
      "address": null,
      "district": null,
      "capacity": null,
      "current_occupancy": null,
      "operational_status": "UNKNOWN",
      "accessibility": "UNKNOWN",
      "contact": null,
      "risk_level": "LOW",
      "source": "Local NGO data (must be verified with GHMC)",
      "verification_note": "Not confirmed as an emergency flood shelter",
      "data_status": "PUBLIC_UNVERIFIED",
      "last_updated": "2026-10-06T14:47:30.454309Z",
      "distance_km": 0.0
    }
  ]
}
```

## Implementation Constraints

- **No ML or Hydrology:** This API does not call the ML model, nor the Hydrology demo provider.
- **No Recommendations:** The shelters are not ranked for safety.
- **Determinism:** The API provides deterministic results based strictly on Haversine distance calculations.
