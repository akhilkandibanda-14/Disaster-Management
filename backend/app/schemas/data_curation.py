"""
Pydantic schemas for SafeMap AI Milestone 6 Data Curation and Manifest endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FloodEventItem(BaseModel):
    event_id: str
    event_name: str
    start_date_iso: str
    end_date_iso: Optional[str] = None
    flood_type: str
    description: str
    district: str
    affected_areas: List[str]
    max_24h_rainfall_mm: Optional[float] = None
    rainfall_station: Optional[str] = None
    rainfall_unit: str = "mm"
    rainfall_measurement_type: str = "UNKNOWN"
    peak_river_discharge_cumec: Optional[float] = None
    discharge_unit: str = "m^3/s"
    discharge_measurement_type: str = "UNKNOWN"
    fatalities_estimated: Optional[int] = None
    source_agency: str
    source_url: str
    data_classification: str
    confidence_level: str
    verification_state: str = "UNVERIFIED"
    geographic_uncertainty: str
    provenance: Optional[Dict[str, Any]] = None
    audit_trail: Optional[Dict[str, Any]] = None
    raw_checksum_sha256: str
    curated_at_utc: str



class DataManifestSummary(BaseModel):
    manifest_version: str
    project: str
    milestone: str
    generated_at_utc: str
    pipeline_execution_duration_seconds: float
    target_region: str
    reference_coordinates: Dict[str, Any]
    summary_metrics: Dict[str, Any]
    datasets: List[Dict[str, Any]]


class DataReadinessAuditResponse(BaseModel):
    evaluation_timestamp_utc: str
    target_region: str
    reference_coordinates: Dict[str, Any]
    model_coverage_guard_km: float
    nearest_indofloods_gauge: Dict[str, Any]
    curated_data_inventory: Dict[str, Any]
    statistical_power_audit: Dict[str, Any]
    baseline_evaluation_loeo: Dict[str, Any]
    readiness_determination: Dict[str, Any]
    data_gap_requirements: List[str]


class InstitutionalIntakeMetadata(BaseModel):
    provider: str = Field(..., description="Agency or organization name (e.g. TSDPS, TG_IRRIGATION, ISRO_NRSC, IMD)")
    source_reference: str = Field(..., description="Document reference, bulletin ID, or portal URL")
    retrieval_date: str = Field(..., description="ISO 8601 retrieval timestamp")
    data_owner: Optional[str] = Field(None, description="Formal data rights holder")
    usage_restrictions: str = Field("RESTRICTED_RESEARCH_ONLY", description="Usage license or security classification")
    measurement_classification: str = Field("OBSERVED", description="OBSERVED, SECONDARY_REPORTED, ESTIMATED, MODELLED, etc.")


class InstitutionalIntakeRequest(BaseModel):
    filename: str = Field(..., description="File name (e.g. 'tsdps_aws_sample.csv')")
    content: str = Field(..., description="Raw text content of the CSV, JSON, or GeoJSON file")
    metadata: InstitutionalIntakeMetadata


class InstitutionalIntakeValidationResponse(BaseModel):
    valid: bool
    filename: str
    file_checksum_sha256: str
    total_records_processed: int
    valid_records_count: int
    errors: List[Dict[str, Any]]
    warnings: List[str]
    sample_records: Optional[List[Dict[str, Any]]] = None


class InstitutionalIntakeCommitResponse(BaseModel):
    status: str
    message: str
    batch_id: Optional[str] = None
    file_checksum_sha256: Optional[str] = None
    curated_sha256: Optional[str] = None
    records_stored: Optional[int] = None
    raw_file: Optional[str] = None
    curated_file: Optional[str] = None
    warnings: Optional[List[str]] = None
    validation: Optional[Dict[str, Any]] = None


class NegativeControlSchemaResponse(BaseModel):
    framework_version: str
    governing_document: str
    supported_states: List[str]
    cardinal_rule: str
    anti_fabrication_rule: str
    sample_size_targets: Dict[str, Any]
    required_institutional_sources: List[str]
