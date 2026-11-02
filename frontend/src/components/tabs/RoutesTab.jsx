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
  onOpenNavigation,
  onMyLocation,
  onLocationSelect,
  incidents = [],
  dashboardStatus = {},
  nearbyHospitals = [],
  nearbyLoading = false,
  nearbyError = '',
  nearbyRadius = 5.0,
  onRadiusChange,
  onRefreshNearbyHospitals,
  nearbySource = '',
  nearbyWarning = ''
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
            {(dashboardStatus.roads === 'refreshing' || dashboardStatus.roads === 'unavailable') && (
              <p className="panel-subtitle">
                {dashboardStatus.roads === 'refreshing'
                  ? 'Road-condition feed refreshing; retained records are not current.'
                  : 'Road-condition feed unavailable; retained records may be stale.'}
              </p>
            )}
            <button
              type="button"
              className="btn-text-small"
              onClick={onMyLocation}
              style={{ marginBottom: '12px' }}
            >
              Locate me and refresh nearby hospitals
            </button>

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
                        {selectedFacility.distance_km != null ? `${selectedFacility.distance_km.toFixed(2)} km away` : ''} · {selectedFacility.facility_type || 'SHELTER'} {selectedFacility.verification_status === 'UNVERIFIED' || selectedFacility.data_status === 'PUBLIC_UNVERIFIED' ? '· (Unverified)' : ''}
                      </span>
                    </>
                  ) : (
                    <span className="muted">Select a destination from the lists below</span>
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
                  <span>Calculating mapped route...</span>
                </>
              ) : (
                <>Plan Route on OSM Network</>
              )}
            </button>
            <button
              type="button"
              className="btn-external-navigation"
              onClick={onOpenNavigation}
              disabled={!selectedFacility}
            >
              <span aria-hidden="true">🧭</span>
              Open external directions (not flood-verified)
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
                          {isDetour
                            ? 'HAZARDS AVOIDED (COMPUTED)'
                            : route.road_condition_status === 'CLEAR'
                              ? 'CURRENT STATUS NOT VERIFIED'
                              : (route.road_condition_status || 'Not reported')}
                        </strong>
                      </div>
                    </div>

                    {isDetour && (
                      <div className="route-detour-notice">
                        <strong>⚠️ Alternate Detour Recalculated:</strong> Primary road segment intersects flooded hazards. Avoidance detour trajectory computed around reported hazards.
                      </div>
                    )}
                    <p className="panel-subtitle">Computed from mapped road data; current flooding, closures, debris and accessibility are not verified.</p>

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

          {/* Dedicated Section: Nearby Hospital Candidates (OpenStreetMap) */}
          <div className="card-panel" style={{ marginTop: '16px' }}>
            <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 className="panel-title">Nearby Hospital Candidates (OSM)</h3>
                <p className="panel-subtitle" style={{ margin: '2px 0 0', fontSize: '11px', color: '#94a3b8' }}>
                  Real OpenStreetMap healthcare POIs discovered near your location
                </p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <label htmlFor="nearby-radius-select" style={{ fontSize: '12px', color: '#94a3b8' }}>Radius:</label>
                <select
                  id="nearby-radius-select"
                  aria-label="Nearby search radius"
                  value={nearbyRadius}
                  onChange={(e) => onRadiusChange && onRadiusChange(Number(e.target.value))}
                  style={{
                    background: '#1e293b',
                    color: '#f8fafc',
                    border: '1px solid #475569',
                    borderRadius: '4px',
                    padding: '3px 8px',
                    fontSize: '12px'
                  }}
                  disabled={nearbyLoading}
                >
                  <option value={2}>2 km</option>
                  <option value={5}>5 km</option>
                  <option value={10}>10 km</option>
                  <option value={15}>15 km</option>
                </select>
                <button
                  type="button"
                  className="btn-select-small"
                  onClick={() => onRefreshNearbyHospitals && onRefreshNearbyHospitals(nearbyRadius, true)}
                  disabled={nearbyLoading}
                  title="Refresh nearby hospital candidates"
                  style={{ padding: '4px 8px', fontSize: '12px' }}
                >
                  {nearbyLoading ? 'Searching...' : 'Refresh'}
                </button>
              </div>
            </div>

            {/* Truth-in-data Notice */}
            <div style={{
              marginTop: '10px',
              padding: '8px 10px',
              background: 'rgba(234, 179, 8, 0.12)',
              border: '1px solid rgba(234, 179, 8, 0.35)',
              borderRadius: '6px',
              fontSize: '11px',
              color: '#fef08a'
            }}>
              ⚠️ <strong>Verification Notice:</strong> Hospital records from OpenStreetMap are unverified. Operational readiness, trauma intake, and casualty acceptance are not confirmed in real time. Confirm via 108 / 112 before travelling.
            </div>

            {nearbyWarning && (
              <div style={{
                marginTop: '8px',
                padding: '6px 10px',
                background: 'rgba(59, 130, 246, 0.15)',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                borderRadius: '6px',
                fontSize: '11px',
                color: '#93c5fd'
              }}>
                ℹ️ {nearbyWarning}
              </div>
            )}

            {nearbyError && (
              <div style={{
                marginTop: '8px',
                padding: '8px 10px',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                borderRadius: '6px',
                fontSize: '11px',
                color: '#fca5a5'
              }}>
                ❌ {nearbyError}
              </div>
            )}

            {nearbyLoading ? (
              <div style={{ padding: '24px', textAlign: 'center', color: '#94a3b8' }}>
                <span className="spinner" aria-hidden="true" style={{ display: 'inline-block', marginRight: '8px' }} />
                <span>Searching nearby OpenStreetMap healthcare facilities...</span>
              </div>
            ) : nearbyHospitals.length === 0 ? (
              <p className="muted" style={{ padding: '16px 4px', textAlign: 'center' }}>
                No hospital candidates discovered within {nearbyRadius} km. Try expanding the search radius.
              </p>
            ) : (
              <div className="routes-facilities-scroll" style={{ maxHeight: '220px', overflowY: 'auto', marginTop: '10px' }}>
                {nearbyHospitals.map((fac) => {
                  const isSelected = selectedFacility && (
                    (selectedFacility.facility_id && selectedFacility.facility_id === fac.facility_id) ||
                    (selectedFacility.id && selectedFacility.id === fac.facility_id)
                  )
                  return (
                    <div
                      key={fac.facility_id}
                      className={`facility-selection-item ${isSelected ? 'active' : ''}`}
                      onClick={() => onFacilitySelect(fac)}
                      style={{ cursor: 'pointer' }}
                    >
                      <div className="fac-select-info">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <strong>{fac.name}</strong>
                          <span style={{
                            fontSize: '9px',
                            padding: '1px 5px',
                            borderRadius: '3px',
                            background: 'rgba(239, 68, 68, 0.2)',
                            color: '#f87171',
                            fontWeight: 'bold'
                          }}>
                            UNVERIFIED
                          </span>
                        </div>
                        <span className="fac-meta-line" style={{ display: 'block', marginTop: '2px', fontSize: '11px', color: '#94a3b8' }}>
                          {fac.distance_km != null ? `${fac.distance_km.toFixed(2)} km away` : ''} · {fac.facility_type || 'HOSPITAL'} · {fac.area || 'Hyderabad'}
                        </span>
                      </div>
                      <button
                        type="button"
                        className={`btn-select-small ${isSelected ? 'active' : ''}`}
                        onClick={(e) => {
                          e.stopPropagation()
                          onFacilitySelect(fac)
                        }}
                      >
                        {isSelected ? 'Selected' : 'Select'}
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Alternative Facilities Selector (Curated Directory) */}
          <div className="card-panel" style={{ marginTop: '16px' }}>
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
              {filteredFacilities.length === 0 ? (
                <p className="muted" style={{ padding: '12px 4px' }}>
                  No nearby {filterType === 'HOSPITAL' ? 'hospitals' : filterType === 'SHELTER' ? 'shelters' : 'destination facilities'} found within 15 km.
                </p>
              ) : filteredFacilities.map((fac) => {
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
              nearbyHospitals={nearbyHospitals}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
