"""
SafeMap AI — Negative Control Data Management Engine (Milestone 8)
Implements formal classification schema and evidence rules for non-flood epochs:
- CONFIRMED_FLOOD
- DOCUMENTED_NON_FLOOD
- UNKNOWN_OR_UNCLASSIFIED
- MISSING_OBSERVATION
- MODELLED_ESTIMATE

Cardinal Rule: A period lacking an explicit flood report must NEVER automatically
be labeled NO_FLOOD. Strict dual-source evidence is required to certify DOCUMENTED_NON_FLOOD.
Synthetic data generation is strictly prohibited.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


class NegativeControlClassification(str, Enum):
    CONFIRMED_FLOOD = "CONFIRMED_FLOOD"
    DOCUMENTED_NON_FLOOD = "DOCUMENTED_NON_FLOOD"
    UNKNOWN_OR_UNCLASSIFIED = "UNKNOWN_OR_UNCLASSIFIED"
    MISSING_OBSERVATION = "MISSING_OBSERVATION"
    MODELLED_ESTIMATE = "MODELLED_ESTIMATE"


VALID_NEGATIVE_CONTROL_STATES = {e.value for e in NegativeControlClassification}


class NegativeControlEvidenceRule:
    """
    Evaluates hydrometeorological and municipal evidence to classify observation epochs.
    Enforces that non-flood status requires documented operational proof, not passive absence.
    """

    @staticmethod
    def classify_epoch(
        date_iso: str,
        rainfall_mm: Optional[float],
        station_id: Optional[str] = None,
        has_sensor_telemetry: bool = True,
        is_model_output_only: bool = False,
        drf_incident_count: Optional[int] = None,
        drf_dewatering_count: Optional[int] = None,
        causeway_submerged: Optional[bool] = None,
        satellite_inundation_confirmed: Optional[bool] = None,
        municipal_log_reference: Optional[str] = None,
        evidence_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Applies rigorous evidence rule to classify an epoch into the 5-state taxonomy.
        """
        # 1. Missing telemetry
        if not has_sensor_telemetry or rainfall_mm is None:
            return {
                "date_iso": date_iso,
                "classification": NegativeControlClassification.MISSING_OBSERVATION.value,
                "is_evaluable_metric": False,
                "rationale": "Station sensor offline or telemetry transmission dropout; observation missing.",
                "evidence_sources": [],
            }

        # 2. Modelled estimate only
        if is_model_output_only:
            return {
                "date_iso": date_iso,
                "classification": NegativeControlClassification.MODELLED_ESTIMATE.value,
                "is_evaluable_metric": False,
                "rationale": "Modelled reanalysis or simulation output; cannot serve as empirical ground truth label.",
                "evidence_sources": [evidence_note] if evidence_note else ["Gridded Reanalysis"],
            }

        # 3. Confirmed flood event
        if (
            (drf_incident_count is not None and drf_incident_count > 5)
            or (drf_dewatering_count is not None and drf_dewatering_count > 0)
            or (causeway_submerged is True)
            or (satellite_inundation_confirmed is True)
        ):
            return {
                "date_iso": date_iso,
                "classification": NegativeControlClassification.CONFIRMED_FLOOD.value,
                "is_evaluable_metric": True,
                "ground_truth_label": 1,
                "rationale": "Verified flood condition with active municipal emergency deployments, causeway submergence, or remote sensing inundation mask.",
                "evidence_sources": [municipal_log_reference] if municipal_log_reference else ["Municipal Emergency Records"],
            }

        # 4. Verified Non-Flood Control (Rule A: Dry/Trace day, or Rule B: Wet-Weather Zero-Inundation)
        # Requires explicit municipal operational log confirmation of zero deployments!
        if municipal_log_reference and drf_dewatering_count == 0 and causeway_submerged is False:
            if rainfall_mm <= 2.5:
                rule_applied = "Rule A (Verified Dry/Trace Day with Zero Municipal Deployments)"
            else:
                rule_applied = "Rule B (Verified Wet-Weather Non-Flood Day with Active Drainage Capacity)"

            return {
                "date_iso": date_iso,
                "classification": NegativeControlClassification.DOCUMENTED_NON_FLOOD.value,
                "is_evaluable_metric": True,
                "ground_truth_label": 0,
                "rule_applied": rule_applied,
                "rationale": f"Verified non-flood condition: 24h rainfall of {rainfall_mm} mm with explicit municipal log confirming zero dewatering deployments and open traffic corridors.",
                "evidence_sources": [municipal_log_reference],
            }

        # 5. Default: Unknown or Unclassified (Passive absence of disaster notice is NOT proof of no flooding!)
        return {
            "date_iso": date_iso,
            "classification": NegativeControlClassification.UNKNOWN_OR_UNCLASSIFIED.value,
            "is_evaluable_metric": False,
            "ground_truth_label": None,
            "rationale": "No official disaster declaration logged, but ground conditions lack explicit municipal or satellite verification of zero inundation. Passive absence of flood reports cannot be treated as a true negative control.",
            "evidence_sources": ["Unverified Calendar Record"],
        }


def get_negative_control_requirements_summary() -> Dict[str, Any]:
    """Returns metadata and requirements summary for the negative-control schema."""
    return {
        "framework_version": "1.0.0",
        "governing_document": "docs/negative_control_data_requirements.md",
        "supported_states": list(VALID_NEGATIVE_CONTROL_STATES),
        "cardinal_rule": "A period lacking an explicit flood report must NEVER automatically be labeled NO_FLOOD. Explicit municipal or satellite verification is required.",
        "anti_fabrication_rule": "Synthetic negative observations are strictly prohibited.",
        "sample_size_targets": {
            "current_hyd_confirmed_floods": 8,
            "current_hyd_documented_non_floods": 0,
            "minimum_target_non_floods": 475,
            "minimum_target_continuous_days": 500,
        },
        "required_institutional_sources": [
            "TSDPS daily AWS rainfall continuous matrix (2019-2023)",
            "GHMC DRF daily water-logging and pump deployment registers",
            "Telangana I&CAD daily reservoir gate operation logs (zero-gate days)",
        ],
    }
