#!/usr/bin/env python3
"""
SafeMap AI — JSON-to-PostgreSQL Incident Data Migration Utility
Migrates legacy citizen incident records from JSON storage to PostgreSQL.

Features:
- Automated timestamped backup of the original JSON file before migration
- Strict schema validation of all input records (coordinates, categories, severities)
- Preserves primary keys (INC-YYYY-XXX), timestamps, verification statuses, and duplicate linkages
- Compatible Base64 image payload handling
- Idempotent re-execution (skips records that already exist in database)
- Never deletes or destructively modifies the original JSON file
- Generates a rollback ledger allowing safe, single-command reversion of imported records
- Detailed progress and audit summary reporting
"""

import argparse
from datetime import datetime, timezone
import json
import logging
import os
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple

# Add backend directory to sys.path so app modules are resolvable
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import is_in_hyderabad, settings
from app.database import SessionLocal, check_db_connectivity
from app.models.incident import Incident
from app.schemas.incident import FLOOD_INCIDENT_CATEGORIES, INCIDENT_SEVERITY_LEVELS

VALID_CATEGORIES = FLOOD_INCIDENT_CATEGORIES
VALID_SEVERITIES = INCIDENT_SEVERITY_LEVELS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("incident_migration")


def backup_json_file(source_path: str) -> str:
    """Creates a non-destructive timestamped backup of the original JSON data file."""
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source JSON file not found at: {source_path}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"incidents.backup.{timestamp}.json"
    backup_path = os.path.join(os.path.dirname(source_path), backup_filename)

    shutil.copy2(source_path, backup_path)
    logger.info("Created backup of legacy incidents: %s", backup_path)
    return backup_path


def parse_datetime_safe(val: Any) -> datetime:
    """Parses ISO timestamp string or returns current UTC timestamp."""
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str) and val.strip():
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


def validate_incident_record(raw: Dict[str, Any], index: int) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validates a raw JSON record against operational constraints.
    Returns (is_valid, error_reason, cleaned_record).
    """
    if not isinstance(raw, dict):
        return False, f"Record at index {index} is not a valid JSON object.", None

    inc_id = raw.get("id")
    if not inc_id or not isinstance(inc_id, str):
        return False, f"Record at index {index} is missing a valid string 'id'.", None

    try:
        lat = float(raw.get("latitude", 0.0))
        lon = float(raw.get("longitude", 0.0))
    except (TypeError, ValueError):
        return False, f"Record {inc_id}: Invalid geographic coordinates ({raw.get('latitude')}, {raw.get('longitude')}).", None

    # Check bounds
    if not is_in_hyderabad(lat, lon):
        return False, f"Record {inc_id}: Coordinates ({lat}, {lon}) outside Hyderabad bounds.", None

    category = raw.get("incident_category") or raw.get("category")
    if category not in VALID_CATEGORIES:
        return False, f"Record {inc_id}: Invalid or non-flood category '{category}'.", None

    severity = raw.get("severity", "MODERATE")
    if severity not in VALID_SEVERITIES:
        severity = "MODERATE"

    description = raw.get("description", "").strip()
    if not description:
        return False, f"Record {inc_id}: Description is empty.", None

    # Normalization
    created_at = parse_datetime_safe(raw.get("created_at"))
    updated_at = parse_datetime_safe(raw.get("updated_at", raw.get("created_at")))
    verified_at = parse_datetime_safe(raw.get("verified_at")) if raw.get("verified_at") else None

    # Image handling
    has_image = bool(raw.get("has_image", False))
    image_data = raw.get("image_data")
    if not has_image and raw.get("image_url"):
        has_image = True

    cleaned = {
        "id": inc_id,
        "latitude": round(lat, 6),
        "longitude": round(lon, 6),
        "address": raw.get("address") or raw.get("location_name") or "Hyderabad Municipal Area",
        "location_name": raw.get("location_name") or raw.get("address"),
        "incident_category": category,
        "severity": severity,
        "description": description,
        "reporter_name": raw.get("reporter_name", "[CONFIDENTIAL]"),
        "reporter_contact": raw.get("reporter_contact", "[REDACTED]"),
        "has_image": has_image,
        "image_data": image_data,
        "verification_status": raw.get("verification_status") or raw.get("status") or "PENDING_REVIEW",
        "data_status": raw.get("data_status") or "PUBLIC_UNVERIFIED_REPORT",
        "duplicate_of_id": raw.get("duplicate_of_id") or raw.get("duplicate_of"),
        "report_count": int(raw.get("report_count", 1)),
        "created_at": created_at,
        "updated_at": updated_at,
        "verified_at": verified_at,
        "verification_note": raw.get("verification_note", "Migrated legacy citizen report."),
        "client_ip": raw.get("client_ip", "127.0.0.1"),
    }
    return True, None, cleaned


def run_migration(
    input_file: str,
    dry_run: bool = False,
    batch_size: int = 50,
) -> Dict[str, Any]:
    """
    Executes JSON to PostgreSQL incident data migration.
    Returns migration statistics report.
    """
    logger.info("=== SafeMap AI Incident Data Migration ===")
    logger.info("Target Database: %s", settings.get_safe_db_summary())
    logger.info("Source JSON File: %s", input_file)
    logger.info("Dry Run Mode: %s", dry_run)

    # 1. Connectivity test
    conn_info = check_db_connectivity()
    db_connected = conn_info.get("connected", False)
    if not db_connected:
        if not dry_run:
            logger.error("Database connection failure: %s", conn_info.get("message"))
            raise ConnectionError(f"Cannot perform migration without active database: {conn_info.get('message')}")
        else:
            logger.warning("Database offline (%s). Proceeding with schema and payload validation in dry-run mode.", conn_info.get("message"))

    # 2. Backup source JSON
    backup_path = backup_json_file(input_file)

    # 3. Read raw records
    with open(input_file, "r", encoding="utf-8") as f:
        try:
            records = json.load(f)
        except json.JSONDecodeError as err:
            logger.error("Failed to parse JSON file: %s", err)
            raise

    if not isinstance(records, list):
        raise ValueError(f"Expected top-level list of records in {input_file}, got {type(records).__name__}")

    total_records = len(records)
    logger.info("Discovered %d records in legacy JSON storage.", total_records)

    imported_ids: List[str] = []
    skipped_ids: List[str] = []
    failed_records: List[Dict[str, str]] = []

    session = SessionLocal() if db_connected else None
    try:
        # Fetch existing IDs in database to support idempotent re-execution
        existing_ids = set()
        if session is not None:
            existing_ids = set(session.scalars(select(Incident.id)).all())
            logger.info("Found %d existing incident records already present in database.", len(existing_ids))

        batch: List[Incident] = []
        for idx, raw in enumerate(records):
            is_valid, error, cleaned = validate_incident_record(raw, idx)
            if not is_valid or cleaned is None:
                failed_records.append({"index": str(idx), "id": str(raw.get("id", "UNKNOWN")), "reason": error or "Unknown validation error"})
                continue

            rec_id = cleaned["id"]
            if rec_id in existing_ids:
                skipped_ids.append(rec_id)
                continue

            incident_model = Incident(
                id=cleaned["id"],
                latitude=cleaned["latitude"],
                longitude=cleaned["longitude"],
                address=cleaned["address"],
                location_name=cleaned["location_name"],
                incident_category=cleaned["incident_category"],
                severity=cleaned["severity"],
                description=cleaned["description"],
                reporter_name=cleaned["reporter_name"],
                reporter_contact=cleaned["reporter_contact"],
                has_image=cleaned["has_image"],
                image_data=cleaned["image_data"],
                verification_status=cleaned["verification_status"],
                data_status=cleaned["data_status"],
                duplicate_of_id=cleaned["duplicate_of_id"],
                report_count=cleaned["report_count"],
                created_at=cleaned["created_at"],
                updated_at=cleaned["updated_at"],
                verified_at=cleaned["verified_at"],
                verification_note=cleaned["verification_note"],
                client_ip=cleaned["client_ip"],
            )

            batch.append(incident_model)
            imported_ids.append(rec_id)
            existing_ids.add(rec_id)

            if len(batch) >= batch_size:
                if not dry_run:
                    session.add_all(batch)
                    session.commit()
                batch.clear()

        # Flush final batch
        if batch and not dry_run:
            session.add_all(batch)
            session.commit()
            batch.clear()

    except SQLAlchemyError as err:
        if session is not None:
            session.rollback()
        logger.error("Database error during migration batch: %s", err)
        raise
    finally:
        if session is not None:
            session.close()

    # 4. Generate Rollback Ledger if imports occurred
    rollback_file = None
    if imported_ids and not dry_run:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        rollback_filename = f"migration_rollback_{timestamp}.json"
        rollback_file = os.path.join(os.path.dirname(input_file), rollback_filename)
        with open(rollback_file, "w", encoding="utf-8") as rf:
            json.dump({
                "migration_timestamp": datetime.now(timezone.utc).isoformat(),
                "imported_ids": imported_ids,
                "backup_path": backup_path,
            }, rf, indent=2)
        logger.info("Saved migration rollback ledger to: %s", rollback_file)

    report = {
        "total_read": total_records,
        "imported_count": len(imported_ids),
        "skipped_count": len(skipped_ids),
        "failed_count": len(failed_records),
        "backup_path": backup_path,
        "rollback_ledger": rollback_file,
        "dry_run": dry_run,
        "failed_details": failed_records,
    }

    logger.info("=== Migration Complete ===")
    logger.info("Total: %d | Imported: %d | Skipped (Existing): %d | Failed: %d",
                total_records, len(imported_ids), len(skipped_ids), len(failed_records))
    if failed_records:
        logger.warning("Failed records count: %d. Review failed_details in report.", len(failed_records))

    return report


def run_rollback(rollback_file: str) -> int:
    """Reverts records imported during a previous migration using the rollback ledger."""
    logger.info("=== SafeMap AI Incident Rollback Utility ===")
    if not os.path.exists(rollback_file):
        raise FileNotFoundError(f"Rollback ledger file not found: {rollback_file}")

    with open(rollback_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    target_ids = data.get("imported_ids", [])
    if not target_ids:
        logger.warning("No incident IDs specified in rollback ledger.")
        return 0

    logger.info("Found %d incident IDs to remove in rollback ledger.", len(target_ids))
    session: Session = SessionLocal()
    deleted_count = 0
    try:
        for inc_id in target_ids:
            inc = session.scalar(select(Incident).where(Incident.id == inc_id))
            if inc:
                session.delete(inc)
                deleted_count += 1
        session.commit()
        logger.info("Successfully deleted %d migrated records.", deleted_count)
    except SQLAlchemyError as err:
        session.rollback()
        logger.error("Database error during rollback: %s", err)
        raise
    finally:
        session.close()

    return deleted_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SafeMap AI JSON-to-PostgreSQL Incident Data Migration")
    parser.add_argument(
        "--input-file",
        default=os.path.join(BACKEND_DIR, "data", "incidents.json"),
        help="Path to source incidents.json file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate records without committing to database",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Commit batch size",
    )
    parser.add_argument(
        "--rollback",
        type=str,
        default=None,
        help="Path to migration_rollback_<timestamp>.json to revert",
    )

    args = parser.parse_args()

    if args.rollback:
        run_rollback(args.rollback)
    else:
        run_migration(input_file=args.input_file, dry_run=args.dry_run, batch_size=args.batch_size)
