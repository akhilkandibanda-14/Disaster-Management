from typing import List, Optional
from datetime import date
from app.schemas.shelter_recommendation import (
    ShelterRecommendationResponse, 
    RequestLocation, 
    RiskContext, 
    RecommendedShelter
)
from app.services.shelter import ShelterService
from app.services.risk_map import RiskMapService
from app.schemas.shelter import Shelter

class ShelterRecommendationService:
    def __init__(self, shelter_service: ShelterService, risk_map_service: RiskMapService):
        self.shelter_service = shelter_service
        self.risk_map_service = risk_map_service

    def recommend_shelters(
        self, 
        latitude: float, 
        longitude: float, 
        radius_km: float, 
        top_n: int, 
        target_date: Optional[date] = None
    ) -> ShelterRecommendationResponse:
        
        # Get Candidate Shelters filtered by radius
        candidates = self.shelter_service.get_shelters(
            latitude=latitude, 
            longitude=longitude, 
            radius_km=radius_km
        )
        
        # Get Risk Context
        risk_result = self.risk_map_service.get_risk_for_location(
            latitude=latitude, 
            longitude=longitude
        )
        
        if risk_result.coverage_status == "MODEL_UNSUPPORTED":
            risk_context = RiskContext(
                prediction_available=False,
                coverage_status="MODEL_UNSUPPORTED"
            )
        else:
            risk_context = RiskContext(
                prediction_available=True,
                coverage_status=risk_result.coverage_status,
                risk_level=risk_result.risk_level,
                predicted_class=risk_result.predicted_class
            )
            
        # Calculate scores and sort candidates
        scored_candidates = []
        for shelter in candidates:
            # We enforce that distance_km is not None from get_shelters when lat/lon is provided
            distance_score = max(0.0, 1.0 - (shelter.distance_km / radius_km))
            
            scored_candidates.append({
                "shelter": shelter,
                "score": distance_score
            })
            
        # Sort by distance score descending, then by distance_km ascending for stability
        scored_candidates.sort(key=lambda x: (-x["score"], x["shelter"].distance_km))
        
        # Take top_n
        top_candidates = scored_candidates[:top_n]
        
        # Format response
        recommended_shelters = []
        for rank, item in enumerate(top_candidates, start=1):
            shelter: Shelter = item["shelter"]
            # Convert Shelter to RecommendedShelter dictionary and add rank, score, safety_status
            shelter_dict = shelter.model_dump()
            shelter_dict["rank"] = rank
            shelter_dict["candidate_score"] = round(item["score"], 4)
            shelter_dict["safety_status"] = "NOT_VERIFIED"
            
            recommended_shelters.append(RecommendedShelter(**shelter_dict))
            
        limitations = [
            "Shelter flood safety has not been independently verified.",
            "Shelter capacity is unavailable.",
            "Current occupancy is unavailable.",
            "Operational status is unknown.",
            "Real-time road safety is not integrated.",
            "Ranking is currently distance-based."
        ]
        if not risk_context.prediction_available:
            limitations.append("Risk-based shelter assessment is unavailable for this location.")
            
        return ShelterRecommendationResponse(
            request_location=RequestLocation(latitude=latitude, longitude=longitude),
            risk_context=risk_context,
            recommendations=recommended_shelters,
            limitations=limitations
        )

# Dependency provider
from fastapi import Depends
from app.services.shelter import get_shelter_service
from app.services.risk_map import get_risk_map_service

def get_shelter_recommendation_service(
    shelter_service: ShelterService = Depends(get_shelter_service),
    risk_map_service: RiskMapService = Depends(get_risk_map_service)
) -> ShelterRecommendationService:
    return ShelterRecommendationService(shelter_service, risk_map_service)
