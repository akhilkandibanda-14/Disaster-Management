import React, { useState } from 'react'
import RiskMap from '../RiskMap'

export default function RoutesTab({
  location,
  facilities,
  selectedFacility,
  onFacilitySelect,
  route,
  roads,
  floodHazards,
  loading,
  isRouting,
  onCalculateRoute,
  onLocationSelect,
  incidents = []
}) {
  const [filterType, setFilterType] = useState('ALL')

  const filteredFacilities = facilities.filter((f) => {
    if (filterType === 'ALL') return true
    return f.facility_type === filterType
  })

  const isDetour = route?.is_rerouted || route?.road_condition_status === 'HAZARDS_AVOIDED'
  const isBlocked = route?.route_status === 'NO_SAFE_ROUTE'

  return (
    <div className="tab-routes">
      <div className="routes-page-layout">
        {/* Left: Planning Controls & Route Results */}
        <div className="routes-control-col">
          <div className="card-panel">
            <h2 className="panel-title">Evacuation Route Console</h2>
            <p className="panel-subtitle">Dijkstra shortest path calculated over OpenStreetMap Hyderabad network</p>

            <div className="route-endpoints-box">
              <div className="endpoint-item">
                <span className="endpoint-badge origin">A</span>
                <div className="endpoint-details">
                  <span className="endpoint-label">ORIGIN (START POINT)</span>
                  <strong>Your Reported Location</strong>
                  <span className="endpoint-coords">{location.latitude.toFixed(4)}° N, {location.longitude.toFixed(4)}° E</span>
                </div>
              </div>

              <div className="endpoint-connector" />

              <div className="endpoint-item">
                <span className="endpoint-badge destination">B</span>
                <div className="endpoint-details">
                  <span className="endpoint-label">DESTINATION (SHELTER / HOSPITAL)</span>
                  {selectedFacility ? (
                    <>
                      <strong>{selectedFacility.name}</strong>
                      <span className="endpoint-coords">
                        {selectedFacility.distance_km != null ? `${selectedFacility.distance_km.toFixed(2)} km away` : ''} · {selectedFacility.facility_type || 'SHELTER'}
                      </span>
                    </>
                  ) : (
                    <span className="muted">Select a destination from the list below</span>
                  )}
                </div>
              </div>
            </div>

            <button
              type="button"
              className="btn-primary-block"
              onClick={onCalculateRoute}
              disabled={isRouting || !selectedFacility}
            >
              {isRouting ? (
                <>
                  <span className="spinner" aria-hidden="true" />
                  <span>Calculating Safe Trajectory...</span>
                </>
              ) : (
                <>Plan Route on OSM Network</>
              )}
            </button>

            {/* Route Calculation Result */}
            {route && (
              <div className="routes-calculated-results">
                {isBlocked ? (
                  <div className="route-blocked-alert" role="alert">
                    <span className="blocked-icon">⛔</span>
                    <div>
                      <strong>NO SAFE ROUTE FOUND (ALL ACCESS SEVERED)</strong>
                      <p>{route.warning_note || 'All road corridors leading to this facility are severed by active flood zones. Do not attempt road travel. Seek high ground immediately.'}</p>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="route-kpi-row">
                      <div className="route-kpi">
                        <span className="kpi-label">DISTANCE</span>
                        <strong className="kpi-val">
                          {route.route_distance_km != null 
                            ? `${route.route_distance_km.toFixed(2)} km` 
                            : (route.distance_km != null ? `${route.distance_km.toFixed(2)} km` : 'N/A')}
                        </strong>
                      </div>
                      <div className="route-kpi">
                        <span className="kpi-label">EST. TIME</span>
                        <strong className="kpi-val">
                          {route.estimated_duration_min != null 
                            ? `${Math.round(route.estimated_duration_min)} min` 
                            : (route.estimated_travel_time_minutes != null ? `${Math.round(route.estimated_travel_time_minutes)} min` : 'Not estimated')}
                        </strong>
                      </div>
                      <div className="route-kpi">
                        <span className="kpi-label">ROAD CONDITION</span>
                        <strong className={`kpi-val ${isDetour ? 'warning-text' : ''}`}>
                          {isDetour ? 'HAZARDS AVOIDED' : (route.road_condition_status || 'Passable')}
                        </strong>
                      </div>
                    </div>

                    {isDetour && (
                      <div className="route-detour-notice">
                        <strong>⚠️ Alternate Detour Recalculated:</strong> Primary road segment intersects flooded hazards. Avoidance detour trajectory computed around reported hazards.
                      </div>
                    )}

                    {route.alternatives && route.alternatives.length > 0 && (
                      <div className="route-alternatives-box" style={{ marginTop: '12px', padding: '10px 12px', background: 'rgba(168,85,247,0.1)', border: '1px solid rgba(168,85,247,0.3)', borderRadius: '8px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                          <strong style={{ color: '#d8b4fe', fontSize: '13px' }}>🔀 Computed Alternative Routes ({route.alternatives.length})</strong>
                        </div>
                        {route.alternatives.map((alt, idx) => (
                          <div key={idx} style={{ padding: '6px 8px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', marginBottom: idx < route.alternatives.length - 1 ? '6px' : 0 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#f3e8ff' }}>Alternative #{idx + 1}</span>
                              <span style={{ fontSize: '12px', color: '#c084fc', fontWeight: 'bold' }}>{alt.route_distance_km?.toFixed(2)} km</span>
                            </div>
                            <p style={{ fontSize: '11px', color: '#94a3b8', margin: '2px 0 0' }}>{alt.description || alt.warning_note}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {route.stale_hazards_present && (
                      <div style={{ marginTop: '8px', padding: '6px 10px', background: 'rgba(234, 179, 8, 0.15)', border: '1px solid rgba(234, 179, 8, 0.4)', borderRadius: '6px', fontSize: '11px', color: '#fef08a' }}>
                        ⚠️ <strong>Freshness Advisory:</strong> Upstream hazard observations contain cached or historical survey data. Proceed with caution.
                      </div>
                    )}

                    {route.data_sources_used && route.data_sources_used.length > 0 && (
                      <div style={{ marginTop: '8px', fontSize: '11px', color: '#94a3b8' }}>
                        <span>Feeds evaluated: {route.data_sources_used.join(' • ')}</span>
                      </div>
                    )}

                    <div className="route-safety-caveat">
                      <p>
                        <strong>Evacuation Safety Warning:</strong> {route.safety_disclaimer || 'Evacuation routes are computed based on currently known road conditions and flood hazard information. Real-time water depth, debris, and sudden flash floods may not be modeled. Never attempt to drive or walk through flooded roadways.'}
                      </p>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Alternative Facilities Selector */}
          <div className="card-panel">
            <div className="panel-header">
              <h3 className="panel-title">Available Destination Facilities</h3>
              <div className="filter-pill-group">
                <button 
                  type="button" 
                  className={`filter-pill ${filterType === 'ALL' ? 'active' : ''}`}
                  onClick={() => setFilterType('ALL')}
                >
                  All
                </button>
                <button 
                  type="button" 
                  className={`filter-pill ${filterType === 'SHELTER' ? 'active' : ''}`}
                  onClick={() => setFilterType('SHELTER')}
                >
                  Shelters
                </button>
                <button 
                  type="button" 
                  className={`filter-pill ${filterType === 'HOSPITAL' ? 'active' : ''}`}
                  onClick={() => setFilterType('HOSPITAL')}
                >
                  Hospitals
                </button>
              </div>
            </div>

            <div className="routes-facilities-scroll">
              {filteredFacilities.map((fac) => {
                const isSelected = selectedFacility && (
                  (selectedFacility.facility_id && selectedFacility.facility_id === fac.facility_id) ||
                  (selectedFacility.id && selectedFacility.id === fac.id)
                )

                return (
                  <div 
                    key={fac.facility_id || fac.id || fac.name}
                    className={`facility-selection-item ${isSelected ? 'active' : ''}`}
                    onClick={() => onFacilitySelect(fac)}
                  >
                    <div className="fac-select-info">
                      <strong>{fac.name}</strong>
                      <span className="fac-meta-line">
                        {fac.distance_km != null ? `${fac.distance_km.toFixed(2)} km away` : ''} · {fac.facility_type || 'SHELTER'} · <em className="unverified-tag">Unverified</em>
                      </span>
                    </div>
                    <button 
                      type="button" 
                      className={`btn-select-small ${isSelected ? 'active' : ''}`}
                    >
                      {isSelected ? 'Selected' : 'Select'}
                    </button>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Right: Map Visualizing Route */}
        <div className="routes-map-col">
          <div className="card-panel" style={{ height: '100%', minHeight: '620px' }}>
            <div className="panel-header">
              <h2 className="panel-title">Evacuation Corridor Map</h2>
              <span className="panel-badge">{isDetour ? 'Hazard Detour Active' : 'Calculated Route'}</span>
            </div>
            <RiskMap
              location={location}
              facilities={facilities}
              selectedFacility={selectedFacility}
              onFacilitySelect={onFacilitySelect}
              roads={roads}
              route={route}
              floodHazards={floodHazards}
              loading={loading}
              onLocationSelect={onLocationSelect}
              height="580px"
              incidents={incidents}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
