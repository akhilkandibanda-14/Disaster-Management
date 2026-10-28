import logging
from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.schemas.assistant import AssistantQueryRequest, AssistantQueryResponse
from app.services.assistant import assistant_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["safety-assistant"])


@router.post("/query", response_model=AssistantQueryResponse)
def query_assistant(request: AssistantQueryRequest) -> AssistantQueryResponse:
    """
    Submits a flood safety or evacuation query to the SafeMap AI Safety Decision Assistant.
    Prioritizes immediate safety rules, integrates live municipal hazard checks and OSM routing,
    and falls back to a deterministic, offline-reliable Safety Decision Engine.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query message cannot be empty or whitespace only."
        )

    try:
        return assistant_service.process_query(request)
    except Exception as e:
        logger.error(f"Error processing assistant query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process flood safety query. Technical details logged for operational auditing."
        )


@router.get("/status")
def get_assistant_status() -> dict:
    """
    Returns AI Assistant readiness, active provider identification, supported languages,
    and safety invariants.
    """
    has_external_key = bool(settings.gemini_api_key or settings.openai_api_key)
    configured_provider = "GEMINI" if settings.gemini_api_key else ("OPENAI" if settings.openai_api_key else "NONE")
    
    return {
        "status": "ready",
        "service": "safemap-ai-safety-assistant",
        "active_provider": configured_provider if (has_external_key and settings.ai_provider != "fallback") else "SAFETY_DECISION_ENGINE_FALLBACK",
        "external_api_key_configured": has_external_key,
        "supported_languages": ["en", "te", "hi"],
        "safety_invariants": {
            "emergency_priority": True,
            "no_fabricated_data": True,
            "no_automatic_sos": True,
            "honest_no_safe_route": True,
            "truth_in_facilities": True,
            "model_safeguard_50km": True
        }
    }
