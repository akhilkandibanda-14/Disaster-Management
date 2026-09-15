-- Phase 1 database boundary. Spatial tables and indexes will be added with PostGIS in Phase 2.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS shelters (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    capacity INTEGER NOT NULL CHECK (capacity >= 0),
    available_capacity INTEGER NOT NULL CHECK (available_capacity >= 0),
    status TEXT NOT NULL DEFAULT 'OPEN',
    accessibility TEXT NOT NULL DEFAULT 'STANDARD',
    contact TEXT,
    risk_level TEXT NOT NULL DEFAULT 'LOW',
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    location GEOGRAPHY(POINT, 4326) GENERATED ALWAYS AS (
        ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
    ) STORED
);

CREATE INDEX IF NOT EXISTS shelters_location_gix ON shelters USING GIST (location);

CREATE TABLE IF NOT EXISTS road_conditions (
    id BIGSERIAL PRIMARY KEY,
    road_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    notes TEXT,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    disaster_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    affected_area TEXT NOT NULL,
    source TEXT NOT NULL,
    description TEXT NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
