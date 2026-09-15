from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.prediction import router as prediction_router
from app.api.risk import router as risk_router
from app.api.resources import router as resources_router
from app.api.routing import router as routing_router
from app.api.weather import router as weather_router
from app.config import settings

app = FastAPI(
    title="AI Disaster Management API",
    version="0.1.0",
    description="Flood risk and safe evacuation decision-support API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resources_router)
app.include_router(prediction_router)
app.include_router(weather_router)
app.include_router(risk_router)
app.include_router(routing_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "service": "disaster-management-api",
        "demo_mode": settings.demo_mode,
    }
