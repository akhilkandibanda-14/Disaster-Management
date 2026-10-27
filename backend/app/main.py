import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.data_curation import router as data_curation_router
from app.api.emergency_facility import router as emergency_facility_router
from app.api.gauge import router as gauge_router
from app.api.hazard import router as hazard_router
from app.api.hydrology import router as hydrology_router
from app.api.prediction import router as prediction_router
from app.api.resources import router as resources_router
from app.api.risk import router as risk_router
from app.api.incident import router as incident_router
from app.api.routing import router as routing_router
from app.api.shelter import router as shelter_router
from app.api.weather import router as weather_router
from app.config import settings
from app.services.road_network import road_network_service


from app.utils.observability import health_monitor, log_structured_event, run_startup_diagnostics


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Execute startup readiness diagnostics for essential resources and providers
    run_startup_diagnostics()

    # Non-blocking road network initialization in a worker thread.
    # This prevents blocking the asyncio event loop during application startup,
    # ensuring immediate readiness for health checks and APIs while the graph pre-loads.
    app.state.road_network_task = asyncio.create_task(
        asyncio.to_thread(road_network_service.load_graph_safe)
    )
    try:
        yield
    finally:
        task = getattr(app.state, "road_network_task", None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


app = FastAPI(
    title="SafeMap AI — Flood Management & Evacuation API",
    version="0.1.0",
    description="Flood risk and safe evacuation decision-support API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

app.include_router(resources_router)
app.include_router(prediction_router)
app.include_router(weather_router)
app.include_router(gauge_router, prefix="/gauges", tags=["gauges"])
app.include_router(risk_router)
app.include_router(routing_router)
app.include_router(hydrology_router)
app.include_router(shelter_router)
app.include_router(emergency_facility_router)
app.include_router(hazard_router)
app.include_router(data_curation_router)
app.include_router(incident_router)


import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log_structured_event(
        "UNHANDLED_EXCEPTION",
        f"Unhandled exception processing {request.method} {request.url.path}: {str(exc)}",
        level="ERROR",
        method=request.method,
        path=request.url.path,
        error_type=exc.__class__.__name__,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Technical details have been logged for operational auditing."}
    )


@app.get("/health", tags=["system"])
def health() -> dict:
    """
    Returns API health status, clearly distinguishing process health from external feed statuses.
    """
    status_dict = health_monitor.get_health_status(road_loaded=road_network_service.is_loaded)
    status_dict["road_network_loaded"] = road_network_service.is_loaded
    return status_dict


@app.get("/health/live", tags=["system"])
def liveness() -> dict:
    """Process liveness probe for container orchestrators."""
    return {"status": "alive", "service": "safemap-flood-management-api"}


@app.get("/health/ready", tags=["system"])
def readiness() -> dict:
    """Readiness probe indicating whether essential dependencies are operational."""
    return {
        "status": "ready",
        "road_network_loaded": road_network_service.is_loaded,
        "demo_mode": settings.demo_mode,
        "environment": settings.app_env,
    }

