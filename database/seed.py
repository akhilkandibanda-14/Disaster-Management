"""Insert clearly labelled development records into PostgreSQL."""

import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import settings


SEED_SHELTERS = [
    ("Community Relief Center", 17.401, 78.472, 500, 320, "OPEN", "FULL", "112", "LOW"),
    ("Riverbank School Shelter", 17.377, 78.503, 250, 0, "FULL", "STANDARD", "108", "MEDIUM"),
    ("East Ward Hall", 17.362, 78.486, 180, 90, "OPEN", "STANDARD", "100", "HIGH"),
]

if __name__ == "__main__":
    engine = create_engine(settings.database_url)
    with engine.begin() as connection:
        for shelter in SEED_SHELTERS:
            connection.execute(
                text("""
                    INSERT INTO shelters
                    (name, latitude, longitude, capacity, available_capacity, status, accessibility, contact, risk_level, last_updated)
                    VALUES (:name, :latitude, :longitude, :capacity, :available_capacity, :status, :accessibility, :contact, :risk_level, :last_updated)
                """),
                dict(zip(("name", "latitude", "longitude", "capacity", "available_capacity", "status", "accessibility", "contact", "risk_level"), shelter, strict=True)) | {"last_updated": datetime.utcnow()},
            )
    print("Inserted development shelter records.")
