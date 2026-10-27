#!/usr/bin/env python3
"""
SafeMap AI — Institutional Incident Verification Utility
Official emergency dispatch tool to record physical municipal verification of flood incidents.

Enforces:
- Restricts VERIFIED_MUNICIPAL status to authoritative institutional command-line execution
- Updates database record with official verification timestamp, inspector unit, and notes
- Does not expose authentication credentials over the public web
"""

import argparse
from datetime import datetime, timezone
import logging
import os
import sys

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.schemas.incident import IncidentStatusUpdate
from app.services.incident import get_incident_service
from app.database import get_db_session

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("institutional_verification")


def verify_incident(
    incident_id: str,
    status: str,
    inspector_unit: str,
    notes: str,
) -> None:
    service = get_incident_service()
    update_data = IncidentStatusUpdate(
        verification_status=status,
        verification_note=f"Verified by {inspector_unit}: {notes}",
    )

    logger.info("Executing institutional status update for %s -> %s", incident_id, status)
    try:
        with get_db_session() as db:
            result = service.update_status(
                incident_id=incident_id,
                update=update_data,
                db=db,
                is_institutional=True,
            )
            if not result:
                logger.error("Incident %s not found in database or local storage.", incident_id)
                sys.exit(1)
            logger.info("Successfully recorded institutional verification: %s (%s)", result.id, result.verification_status)
    except Exception as err:
        logger.error("Failed to execute institutional verification: %s", err)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="SafeMap AI Institutional Incident Verification")
    parser.add_argument("incident_id", help="Canonical incident ID (e.g. INC-2026-001)")
    parser.add_argument(
        "--status",
        choices=["VERIFIED_MUNICIPAL", "REJECTED", "RESOLVED"],
        default="VERIFIED_MUNICIPAL",
        help="Institutional verification status",
    )
    parser.add_argument(
        "--inspector-unit",
        default="GHMC Disaster Response Force (DRF) Unit",
        help="Field team or monitoring agency identifying unit",
    )
    parser.add_argument(
        "--notes",
        default="Physical field verification confirmed active road flooding condition.",
        help="Official verification details and observations",
    )

    args = parser.parse_args()
    verify_incident(args.incident_id, args.status, args.inspector_unit, args.notes)


if __name__ == "__main__":
    main()
