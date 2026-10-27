import React from 'react'
import RiskMap from '../RiskMap'

export default function MapTab({
  riskData,
  location,
  facilities,
  selectedFacility,
  onFacilitySelect,
  roads,
  route,
  floodHazards,
  loading,
  hazardWarning,
  onLocationSelect,
  incidents = []
}) {
  return (
    <div className="tab-map-view">
      <div className="map-page-layout">
        <div className="map-page-main">
          <RiskMap
            riskData={riskData}
            location={location}
            facilities={facilities}
            selectedFacility={selectedFacility}
            onFacilitySelect={onFacilitySelect}
            roads={roads}
            route={route}
            floodHazards={floodHazards}
            loading={loading}
            onLocationSelect={onLocationSelect}
            showLayersControl={true}
            height="calc(100vh - 160px)"
            incidents={incidents}
          />
        </div>

        <aside className="map-page-sidebar">
          {/* Selected Coordinate Inspector */}
          <div className="card-panel">
            <h3 className="panel-title">Location Inspector</h3>
            <div className="inspector-coords-box">
              <span className="coord-label">LATITUDE / LONGITUDE</span>
              <strong className="coord-value">{location.latitude.toFixed(5)}° N, {location.longitude.toFixed(5)}° E</strong>
              <p className="coord-hint">💡 Click anywhere on the map to query risk and test flood boundaries.</p>
            </div>

            <div className="inspector-status-box">
              <span className="status-title">Flood Hazard Intersection:</span>
              {hazardWarning ? (
                hazardWarning.is_in_hazard_zone ? (
                  <div className="hazard-intersect-alert">
                    <strong className="danger-text">⚠️ Intersects {hazardWarning.hazard_count} Hazard Zone(s)</strong>
                    <span className="severity-pill">{hazardWarning.highest_severity} SEVERITY</span>
                    <ul className="intersected-list">
                      {hazardWarning.intersected_hazards.map((hz) => (
                        <li key={hz.hazard_id}>
                          <strong>{hz.title}</strong> ({hz.severity})
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <div className="hazard-clear-notice">
                    <span className="clear-icon">✓</span>
                    <span>No hazard polygon intersects this point</span>
                    <small>Note: Unmonitored locations are NOT guaranteed flood-safe.</small>
                  </div>
                )
              ) : (
                <p className="muted">Evaluating location telemetry...</p>
              )}
            </div>
          </div>

          {/* Model Coverage Notice */}
          <div className="card-panel">
            <h3 className="panel-title">Model Coverage Limit</h3>
            <p className="small-text">
              The INDOFLOODS machine learning model requires an official river gauge within 50 km. 
              The nearest reference station to Hyderabad is <strong>INDOFLOODS-gauge-916</strong> at <strong>71.8 km</strong>.
            </p>
            <div className="safeguard-badge-row">
              <span className="badge-safeguard">MODEL_UNSUPPORTED</span>
              <span className="badge-safeguard">NON_FABRICATED</span>
            </div>
          </div>

          {/* Map Layer Legend */}
          <div className="card-panel">
            <h3 className="panel-title">Layer Legend & Data Status</h3>
            <div className="legend-items-list">
              <div className="legend-row">
                <span className="legend-dot user" />
                <div>
                  <strong>User / Selected Location</strong>
                  <p>Target point for routing and checks</p>
                </div>
              </div>
              <div className="legend-row">
                <span className="legend-dot" style={{ backgroundColor: '#10b981' }} />
                <div>
                  <strong>Shelter (PUBLIC_UNVERIFIED)</strong>
                  <p>Municipal facility; capacity unverified</p>
                </div>
              </div>
              <div className="legend-row">
                <span className="legend-dot" style={{ backgroundColor: '#a855f7' }} />
                <div>
                  <strong>Hospital / Medical Care</strong>
                  <p>Bed capacity and operations unverified</p>
                </div>
              </div>
              <div className="legend-row">
                <span className="legend-dot" style={{ backgroundColor: '#ef4444' }} />
                <div>
                  <strong>Flooded / Blocked Road Segment</strong>
                  <p>Impassable during flood events</p>
                </div>
              </div>
              <div className="legend-row">
                <span className="legend-dot" style={{ backgroundColor: '#ef4444', border: '1px solid #fff' }} />
                <div>
                  <strong>Authoritative Flood Alert Zone</strong>
                  <p>Official NDMA / municipal bulletin</p>
                </div>
              </div>
              <div className="legend-row">
                <span className="legend-dot" style={{ backgroundColor: '#f59e0b' }} />
                <div>
                  <strong>Municipal Survey Flood Zone</strong>
                  <p>Historical waterlogging vulnerability</p>
                </div>
              </div>
              <div className="legend-row">
                <span className="legend-dot" style={{ backgroundColor: '#c084fc' }} />
                <div>
                  <strong>Demonstration Hazard Zone [DEMO]</strong>
                  <p>Simulated test polygons for pilot evaluation</p>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
