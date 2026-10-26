"""
SafeMap AI — Operational Observability, Structured Logging & Health Diagnostics

Provides:
- Structured JSON and key-value logging for provider failures, stale observations, route failures,
  data import errors, and security events.
- Automatic secret and credential redaction (passwords, tokens, API keys).
- Clear architectural separation between API process health and external feed health.
- System health monitoring tracking external telemetry statuses.
- Startup readiness validation checks.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("safemap.observability")

# Sensitive key patterns that must be redacted from all log payloads
SENSITIVE_KEY_PATTERN = re.compile(
    r"(key|secret|password|token|auth|credential|admin_api|analyst_api|api_key)",
    re.IGNORECASE,
)

# URL query parameter pattern to redact API keys in logged URLs
URL_SECRET_PATTERN = re.compile(
    r"([?&](?:appid|key|api_key|token|secret)=)[^&]+",
    re.IGNORECASE,
)


def redact_sensitive_value(val: Any) -> Any:
    if isinstance(val, str):
        # Redact secrets embedded in URLs
        return URL_SECRET_PATTERN.sub(r"\1[REDACTED]", val)
    return val


def sanitize_payload(obj: Any) -> Any:
    """
    Recursively masks sensitive values (passwords, API keys, tokens) in dictionaries and lists.
    """
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            if SENSITIVE_KEY_PATTERN.search(str(k)):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                sanitized[k] = sanitize_payload(v)
            else:
                sanitized[k] = redact_sensitive_value(v)
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_payload(item) for item in obj]
    else:
        return redact_sensitive_value(obj)


def log_structured_event(
    event_type: str,
    message: str,
    level: str = "INFO",
    **details: Any,
) -> Dict[str, Any]:
    """
    Emits a structured log record without exposing credentials or secrets.
    """
    clean_details = sanitize_payload(details)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "safemap-ai",
        "event_type": event_type,
        "level": level.upper(),
        "message": message,
        "details": clean_details,
    }

    log_msg = json.dumps(record, default=str)
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(log_msg)
    return record


class SystemHealthMonitor:
    """
    Tracks runtime operational health, external provider statuses, and data staleness.
    Keeps API process health strictly distinct from external feed availability.
    """

    def __init__(self):
        self.start_time: float = time.time()
        self.weather_provider_status: str = "INITIALIZING"
        self.weather_last_checked: Optional[datetime] = None
        self.weather_is_stale: bool = False
        self.weather_is_simulated: bool = settings.demo_mode
        self.weather_warning: Optional[str] = None
        self.hazard_provider_warnings: List[str] = []

    def record_weather_observation(
        self,
        provider: str,
        is_stale: bool,
        is_simulated: bool,
        warning: Optional[str] = None,
    ) -> None:
        self.weather_last_checked = datetime.now(timezone.utc)
        self.weather_is_stale = is_stale
        self.weather_is_simulated = is_simulated
        self.weather_warning = warning

        if warning and "failed" in warning.lower():
            self.weather_provider_status = "DEGRADED"
            log_structured_event(
                "PROVIDER_FAILURE",
                f"Weather provider degraded: {warning}",
                level="WARNING",
                provider=provider,
                warning=warning,
            )
        elif is_stale:
            self.weather_provider_status = "STALE"
            log_structured_event(
                "STALE_DATA_DETECTED",
                "Weather observation exceeds staleness threshold (> 3 hours)",
                level="WARNING",
                provider=provider,
            )
        elif is_simulated:
            self.weather_provider_status = "DEMO_FALLBACK"
        else:
            self.weather_provider_status = "OPERATIONAL"

    def record_hazard_warnings(self, warnings: List[str]) -> None:
        self.hazard_provider_warnings = warnings
        if warnings:
            log_structured_event(
                "PROVIDER_WARNING",
                "External hazard feeds emitted warnings",
                level="WARNING",
                warnings=warnings,
            )

    def record_route_failure(
        self,
        origin: Dict[str, float],
        destination: Dict[str, float],
        reason: str,
    ) -> None:
        log_structured_event(
            "ROUTING_FAILURE",
            f"Evacuation routing failed: {reason}",
            level="WARNING",
            origin=origin,
            destination=destination,
            reason=reason,
        )

    def record_data_import_error(self, filename: str, errors: List[Dict[str, Any]]) -> None:
        log_structured_event(
            "DATA_IMPORT_ERROR",
            f"Institutional data intake error in '{filename}'",
            level="ERROR",
            filename=filename,
            error_count=len(errors),
            sample_errors=errors[:3],
        )

    def record_auth_failure(self, endpoint: str, reason: str, role_required: str) -> None:
        log_structured_event(
            "AUTH_FAILURE",
            f"Unauthorized access attempt on {endpoint}",
            level="WARNING",
            endpoint=endpoint,
            reason=reason,
            role_required=role_required,
        )

    def record_verification_promotion(
        self,
        facility_id: str,
        admin_actor: str,
        evidence_source: str,
        updated_fields: Dict[str, Any],
    ) -> None:
        log_structured_event(
            "VERIFICATION_PROMOTION",
            f"Emergency facility '{facility_id}' verification status promoted by administrator",
            level="INFO",
            facility_id=facility_id,
            admin=admin_actor,
            evidence_source=evidence_source,
            updated_fields=updated_fields,
        )

    def get_health_status(self, road_loaded: bool = False, model_loaded: bool = True) -> Dict[str, Any]:
        """
        Produces process health status strictly separated from external feed health.
        """
        uptime = time.time() - self.start_time

        # Weather feed status evaluation
        weather_status = self.weather_provider_status
        if weather_status == "INITIALIZING":
            weather_status = "DEMO_FALLBACK" if settings.demo_mode else "OPERATIONAL"

        # Hazard feed status
        hazard_status = "WARNING" if self.hazard_provider_warnings else "OPERATIONAL"

        # Road network status
        road_status = "LOADED" if road_loaded else "LOADING_OR_UNAVAILABLE"

        return {
            "status": "ok",
            "service": "safemap-flood-management-api",
            "environment": settings.app_env,
            "demo_mode": settings.demo_mode,
            "process": {
                "status": "healthy",
                "uptime_seconds": round(uptime, 2),
                "road_network_loaded": road_loaded,
                "model_loaded": model_loaded,
            },
            "external_feeds": {
                "weather": {
                    "status": weather_status,
                    "is_stale": self.weather_is_stale,
                    "is_simulated": self.weather_is_simulated,
                    "last_warning": self.weather_warning,
                },
                "hazard_feeds": {
                    "status": hazard_status,
                    "provider_warnings": self.hazard_provider_warnings,
                },
                "road_network": {
                    "status": road_status,
                },
            },
        }


# Global health monitor instance
health_monitor = SystemHealthMonitor()


def run_startup_diagnostics(
    project_root: Optional[Path] = None,
    custom_settings: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Performs clear startup checks for essential resources, datasets, ML models,
    and external providers, logging structured findings.
    In production environments, refuses startup if insecure default credentials
    or missing required configuration are detected.
    """
    cfg = custom_settings or settings
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]

    road_graph_path = project_root / "data" / "raw" / "roads" / "hyderabad_road_network.graphml"
    catalogue_path = project_root / "data" / "curated" / "hyderabad_flood_event_catalogue.json"
    manifest_path = project_root / "data" / "data_manifest.json"
    model_path = project_root / "ml" / "models" / "flood_severity_model.joblib"

    diagnostics = {
        "environment": cfg.app_env,
        "demo_mode": cfg.demo_mode,
        "is_production": cfg.is_production(),
        "road_network_graph_present": road_graph_path.exists(),
        "road_graph_size_mb": round(road_graph_path.stat().st_size / (1024 * 1024), 2) if road_graph_path.exists() else 0,
        "curated_flood_catalogue_present": catalogue_path.exists(),
        "manifest_present": manifest_path.exists(),
        "ml_model_present": model_path.exists(),
        "weather_api_key_configured": bool(cfg.weather_api_key),
        "cors_origins": cfg.cors_origins,
        "warnings": [],
        "errors": [],
    }

    if not diagnostics["road_network_graph_present"]:
        diagnostics["warnings"].append(
            f"Road network graph not found at {road_graph_path}. Evacuation routing will fall back or be unavailable."
        )

    if not diagnostics["ml_model_present"]:
        diagnostics["warnings"].append(
            f"ML model file not found at {model_path}. Severity prediction will be unavailable."
        )

    if cfg.is_production():
        insecure_keys = []
        # Check admin API key
        if (
            not cfg.admin_api_key
            or cfg.admin_api_key in ("safemap-admin-dev-key", "admin", "password", "secret")
            or len(cfg.admin_api_key.strip()) < 16
        ):
            insecure_keys.append("ADMIN_API_KEY (insecure default or < 16 characters)")

        # Check analyst API key
        if (
            not cfg.analyst_api_key
            or cfg.analyst_api_key in ("safemap-analyst-dev-key", "analyst", "password", "secret")
            or len(cfg.analyst_api_key.strip()) < 16
        ):
            insecure_keys.append("ANALYST_API_KEY (insecure default or < 16 characters)")

        if insecure_keys:
            err_msg = (
                f"Production startup refused: Insecure or default credentials detected for: {', '.join(insecure_keys)}. "
                "Production environment requires explicit, unique secrets (>=16 chars) set via environment variables."
            )
            diagnostics["errors"].append(err_msg)
            log_structured_event("STARTUP_SECURITY_REFUSAL", err_msg, level="ERROR")
            raise RuntimeError(err_msg)

        if cfg.demo_mode:
            diagnostics["warnings"].append(
                "WARNING: DEMO_MODE is active in a PRODUCTION environment. Simulated telemetry may be used."
            )
        if not cfg.database_url:
            diagnostics["warnings"].append(
                "Production warning: DATABASE_URL is not configured."
            )

    log_structured_event(
        "STARTUP_DIAGNOSTIC",
        "SafeMap AI startup readiness validation completed",
        level="WARNING" if diagnostics["warnings"] else "INFO",
        diagnostics=diagnostics,
    )

    return diagnostics
