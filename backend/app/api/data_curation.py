"""
API router for SafeMap AI Milestone 6 Data Curation, Provenance Manifest,
and Local Readiness Audit endpoints.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_admin, require_analyst_or_admin
from app.utils.observability import health_monitor, log_structured_event
from app.schemas.data_curation import (
    DataManifestSummary,
    DataReadinessAuditResponse,
    FloodEventItem,
    InstitutionalIntakeCommitResponse,
    InstitutionalIntakeRequest,
    InstitutionalIntakeValidationResponse,
    NegativeControlSchemaResponse,
)
from app.services.data_importers.curation_pipeline import SafeMapCurationPipeline
from app.services.data_importers.institutional_intake import InstitutionalIntakeEngine
from app.services.data_importers.negative_control_manager import (
    NegativeControlClassification,
    NegativeControlEvidenceRule,
    get_negative_control_requirements_summary,
)
from evaluate_hyderabad_data_readiness import audit_local_data_readiness

router = APIRouter(prefix="/data-curation", tags=["data-curation"])

BASE_DIR = Path(__file__).resolve().parents[3]
intake_engine = InstitutionalIntakeEngine(base_dir=BASE_DIR)


@router.get("/manifest", response_model=DataManifestSummary)
def get_data_manifest() -> Dict[str, Any]:
    """
    Returns the reproducible machine-readable dataset manifest and provenance audit.
    If the manifest does not exist, triggers pipeline execution to generate it.
    """
    manifest_path = BASE_DIR / "data" / "data_manifest.json"
    if not manifest_path.exists():
        pipeline = SafeMapCurationPipeline(base_dir=BASE_DIR)
        pipeline.run()

    if not manifest_path.exists():
        raise HTTPException(status_code=500, detail="Data manifest could not be loaded or generated.")

    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/historical-events", response_model=List[FloodEventItem])
def get_historical_flood_events(
    classification: Optional[str] = Query(None, description="Filter by classification (e.g. OBSERVATION, OFFICIAL_ALERT, HISTORICAL_INUNDATION)"),
    confidence: Optional[str] = Query(None, description="Filter by confidence level (e.g. HIGH, VERY_HIGH)"),
) -> List[Dict[str, Any]]:
    """
    Returns the curated historical flood event catalogue for Hyderabad.
    Contains explicit event intervals, physical measurements, and source provenance.
    """
    catalog_path = BASE_DIR / "data" / "curated" / "hyderabad_flood_event_catalogue.json"
    if not catalog_path.exists():
        pipeline = SafeMapCurationPipeline(base_dir=BASE_DIR)
        pipeline.run()

    if not catalog_path.exists():
        raise HTTPException(status_code=500, detail="Curated flood event catalogue not found.")

    with open(catalog_path, "r", encoding="utf-8") as f:
        events = json.load(f)

    if classification:
        cls_upper = classification.strip().upper()
        events = [e for e in events if e.get("data_classification", "").upper() == cls_upper]

    if confidence:
        conf_upper = confidence.strip().upper()
        events = [e for e in events if e.get("confidence_level", "").upper() == conf_upper]

    return events


@router.get("/readiness-audit", response_model=DataReadinessAuditResponse)
def get_data_readiness_audit() -> Dict[str, Any]:
    """
    Returns the reproducible local data readiness and model validation audit for Hyderabad.
    Documents statistical power limits, basin mismatches, and data gap requirements.
    """
    return audit_local_data_readiness(base_dir=BASE_DIR)


# =============================================================================
# Milestone 8 & 10: Institutional Data Intake & Role-Based Permissions
# =============================================================================

@router.post("/intake/validate", response_model=InstitutionalIntakeValidationResponse)
def validate_institutional_intake_file(
    payload: InstitutionalIntakeRequest,
    user_role: str = Depends(require_analyst_or_admin),
) -> Dict[str, Any]:
    """
    Dry-run validation of an authorized institutional data file (CSV, JSON, GeoJSON).
    Requires Analyst or Admin credentials in production.
    Checks timestamps, coordinates, units, missing-value sentinels, and duplicates.
    Does not save to disk.
    """
    meta_dict = payload.metadata.model_dump()
    res = intake_engine.validate_content(payload.content, payload.filename, meta_dict)

    if not res.get("valid", False):
        health_monitor.record_data_import_error(payload.filename, res.get("errors", []))

    # Provide a sample preview of valid records if successful
    norm_recs = res.get("normalized_records", [])
    res["sample_records"] = norm_recs[:5] if norm_recs else []
    return res


@router.post("/intake/commit", response_model=InstitutionalIntakeCommitResponse)
def commit_institutional_intake_file(
    payload: InstitutionalIntakeRequest,
    user_role: str = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Validates and commits an authorized institutional data batch into repository storage.
    Strictly restricted to authorized administrators (HTTP 401/403 enforced).
    Preserves raw source copy, writes normalized curated JSON, and appends to audit ledger.
    Guarantees idempotency via SHA-256 checksums.
    """
    meta_dict = payload.metadata.model_dump()
    res = intake_engine.commit_batch(payload.content, payload.filename, meta_dict)

    log_structured_event(
        "DATA_BATCH_COMMITTED",
        f"Institutional batch '{payload.filename}' committed by administrator",
        level="INFO",
        filename=payload.filename,
        checksum=res.get("file_checksum_sha256"),
        records_committed=res.get("curated_records_count", 0),
        admin=user_role,
    )
    return res


@router.get("/intake/sources")
def get_institutional_sources_inventory(
    user_role: str = Depends(require_analyst_or_admin),
) -> Dict[str, Any]:
    """
    Returns classified inventory of data sources: downloaded & verified, viewer-only,
    restricted institutional, draft request templates, and unsupported measurement gaps.
    Protected: requires Analyst or Admin role in production.
    """
    return intake_engine.get_sources_inventory()


@router.get("/intake/log")
def get_institutional_intake_log(
    user_role: str = Depends(require_analyst_or_admin),
) -> List[Dict[str, Any]]:
    """
    Returns chronological audit log of all ingested institutional batches.
    Protected: requires Analyst or Admin role in production.
    """
    return intake_engine.get_intake_log()


@router.get("/negative-controls/summary", response_model=NegativeControlSchemaResponse)
def get_negative_controls_summary() -> Dict[str, Any]:
    """
    Returns the negative control schema, strict dual-source evidence rules,
    sample size targets, and requirements for legitimate false-alarm rate evaluation.
    """
    return get_negative_control_requirements_summary()
