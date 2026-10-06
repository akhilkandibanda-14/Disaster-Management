# Shelter Data Validation

## 1. Dataset Overview
- **Location:** `data/raw/shelters/hyderabad_shelters.csv`
- **File Size:** 3,635 bytes
- **Rows:** 11
- **Columns:** 18

### Columns
`shelter_id`, `name`, `latitude`, `longitude`, `address`, `area`, `district`, `state`, `capacity`, `current_occupancy`, `operational_status`, `accessibility`, `shelter_type`, `contact`, `source`, `last_updated`, `data_status`, `verification_note`

## 2. Geographic Coverage
- **Latitude Bounds:** 17.3594 to 17.4950
- **Longitude Bounds:** 78.3830 to 78.5590
- **Coordinate Integrity:** 0 missing coordinates, 0 duplicate coordinates, 0 invalid coordinates.
- **Coverage Check:** The coordinates are accurately situated within the Hyderabad metropolitan area.

## 3. Data Quality & Missing Fields
- **Missing Fields (100% missing):**
  - `address`
  - `district`
  - `capacity`
  - `current_occupancy`
  - `contact`
- **Partially Available / Suspicious:**
  - `operational_status` (Available, but all records are set to "UNKNOWN")
  - `accessibility` (Available, but all records are set to "UNKNOWN")
- **Duplicate Records:** 0 duplicated rows, 0 duplicated `shelter_id`.

## 4. Provenance and Verification Classification
- **Classification:** **PUBLIC_UNVERIFIED**
- **Provenance Note:** The `source` column indicates these are a "Public local listing; facility status must be verified with GHMC."
- **Verification Note:** The dataset explicitly states: "Not confirmed as an emergency flood shelter; do not present as flood-safe until officially verified."
- **Official Warning:** While the names contain "GHMC", the data is derived from unverified public listings and the source cannot establish that these are official flood shelters. 

**Candidate shelter locations — flood-shelter status not independently verified.**

## 5. Limitations
- Missing physical addresses and district references.
- Lacks operational statistics like max capacity, occupancy, and contact details.
- Cannot be unconditionally routed to as a safe shelter during an active flood without further live verification logic.

## 6. API Key Requirement
- No API keys were required for this validation phase. No external geocoding or routing APIs were introduced.
