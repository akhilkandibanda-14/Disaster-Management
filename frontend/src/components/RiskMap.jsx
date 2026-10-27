import React, { useState, useEffect } from 'react'
import { CircleMarker, MapContainer, Polygon, Polyline, Popup, TileLayer, ZoomControl, useMap, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

function MapAutoResizer({ routePositions, centerCoords }) {
  const map = useMap()

  useEffect(() => {
    if (!map) return

    window._leaflet_map = map
    map.invalidateSize({ pan: false })

    const t1 = setTimeout(() => map.invalidateSize({ pan: false }), 150)
    const t2 = setTimeout(() => map.invalidateSize({ pan: false }), 500)
    const t3 = setTimeout(() => map.invalidateSize({ pan: false }), 1200)

    const container = map.getContainer()
    let observer = null
    if (typeof ResizeObserver !== 'undefined' && container) {
      observer = new ResizeObserver(() => {
        map.invalidateSize({ pan: false })
      })
      observer.observe(container)
      if (container.parentElement) {
        observer.observe(container.parentElement)
      }
    }

    const onResize = () => {
      map.invalidateSize({ pan: false })
    }
    window.addEventListener('resize', onResize)

    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
      if (observer) observer.disconnect()
      window.removeEventListener('resize', onResize)
    }
  }, [map])

  useEffect(() => {
    if (!map) return
    if (routePositions && routePositions.length > 1) {
      try {
        map.fitBounds(routePositions, { padding: [50, 50], maxZoom: 14 })
      } catch {
        // Safe fallback
      }
    } else if (centerCoords) {
      map.flyTo([centerCoords.latitude, centerCoords.longitude], map.getZoom(), { duration: 1.0 })
    }
  }, [map, routePositions, centerCoords])

  return null
}

function MapClickHandler({ onLocationSelect }) {
  useMapEvents({
    click(e) {
      const lat = e.latlng.lat
      const lon = e.latlng.lng
      // Restrict to Hyderabad boundary
      if (lat >= 17.2 && lat <= 17.6 && lon >= 78.2 && lon <= 78.7) {
        if (onLocationSelect) {
          onLocationSelect({ latitude: lat, longitude: lon })
        }
      }
    }
  })
  return null
}

function MapTileLayer({ tileMode = 'street', onTileErrorChange }) {
  const map = useMap()

  useEffect(() => {
    if (!map) return
    let errCount = 0
    let timer = null

    const onTileError = () => {
      errCount += 1
      if (errCount >= 3) {
        if (onTileErrorChange) onTileErrorChange(true)
      }
    }

    const onTileLoad = () => {
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => {
        errCount = 0
        if (onTileErrorChange) onTileErrorChange(false)
      }, 600)
    }

    map.on('tileerror', onTileError)
    map.on('tileload', onTileLoad)

    return () => {
      map.off('tileerror', onTileError)
      map.off('tileload', onTileLoad)
      if (timer) clearTimeout(timer)
    }
  }, [map, onTileErrorChange, tileMode])

  if (tileMode === 'satellite') {
    return (
      <>
        <TileLayer
          key="esri-satellite"
          attribution="Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          maxZoom={19}
        />
        <TileLayer
          key="esri-labels"
          attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
          maxZoom={19}
          opacity={0.85}
        />
      </>
    )
  }

  return (
    <TileLayer
      key="osm-streets"
      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      maxZoom={19}
    />
  )
}

export default function RiskMap({ 
  riskData, 
  location, 
  facilities, 
  selectedFacility, 
  onFacilitySelect, 
  roads, 
  route, 
  floodHazards, 
  loading,
  onLocationSelect,
  showLayersControl = true,
  height = '100%',
  activeLayers,
  tileMode: externalTileMode,
  onTileModeChange,
  incidents = []
}) {
  const [hasTileError, setHasTileError] = useState(false)
  const [internalTileMode, setInternalTileMode] = useState('street')
  const currentTileMode = externalTileMode || internalTileMode

  const handleTileModeToggle = (mode) => {
    setInternalTileMode(mode)
    if (onTileModeChange) {
      onTileModeChange(mode)
    }
  }
  
  // Layer toggles (synced with activeLayers if passed, otherwise internal state)
  const [internalShowHazards, setInternalShowHazards] = useState(true)
  const [internalShowRoads, setInternalShowRoads] = useState(true)
  const [internalShowShelters, setInternalShowShelters] = useState(true)
  const [internalShowHospitals, setInternalShowHospitals] = useState(true)
  const [internalShowRoute, setInternalShowRoute] = useState(true)
  const [internalShowIncidents, setInternalShowIncidents] = useState(true)

  const showHazards = activeLayers?.risk !== undefined ? activeLayers.risk : internalShowHazards
  const showRoads = activeLayers?.roads !== undefined ? activeLayers.roads : internalShowRoads
  const showShelters = activeLayers?.shelters !== undefined ? activeLayers.shelters : internalShowShelters
  const showHospitals = activeLayers?.hospitals !== undefined ? activeLayers.hospitals : internalShowHospitals
  const showRoute = activeLayers?.route !== undefined ? activeLayers.route : internalShowRoute
  const showIncidents = activeLayers?.incidents !== undefined ? activeLayers.incidents : internalShowIncidents

  const center = [location?.latitude ?? 17.385, location?.longitude ?? 78.4867]
  const routePositions = (route?.geometry && showRoute)
    ? route.geometry.map(([longitude, latitude]) => [latitude, longitude]) 
    : []
  const isDetour = route?.is_rerouted || route?.road_condition_status === 'HAZARDS_AVOIDED'
  const isBlocked = route?.route_status === 'NO_SAFE_ROUTE'

  const handleRetry = () => {
    setHasTileError(false)
    if (window._leaflet_map) {
      window._leaflet_map.eachLayer((layer) => {
        if (layer && typeof layer.redraw === 'function') {
          layer.redraw()
        }
      })
      window._leaflet_map.invalidateSize({ pan: false })
    }
  }

  return (
    <div className="risk-map-wrapper" style={{ height }}>
      {showLayersControl && (
        <div className="map-layer-toggles">
          <div className="map-mode-toggle" style={{ marginRight: '6px' }}>
            <button
              type="button"
              className={`mode-toggle-btn ${currentTileMode === 'street' ? 'active' : ''}`}
              onClick={() => handleTileModeToggle('street')}
              title="OpenStreetMap Road View"
            >
              Street
            </button>
            <button
              type="button"
              className={`mode-toggle-btn ${currentTileMode === 'satellite' ? 'active' : ''}`}
              onClick={() => handleTileModeToggle('satellite')}
              title="Satellite Imagery"
            >
              🛰️ Satellite
            </button>
          </div>
          <label className="layer-checkbox">
            <input 
              type="checkbox" 
              checked={showHazards} 
              onChange={(e) => setInternalShowHazards(e.target.checked)} 
            />
            <span className="checkbox-label">Flood Hazards</span>
          </label>
          <label className="layer-checkbox">
            <input 
              type="checkbox" 
              checked={showRoads} 
              onChange={(e) => setInternalShowRoads(e.target.checked)} 
            />
            <span className="checkbox-label">Roads</span>
          </label>
          <label className="layer-checkbox">
            <input 
              type="checkbox" 
              checked={showShelters} 
              onChange={(e) => setInternalShowShelters(e.target.checked)} 
            />
            <span className="checkbox-label">Shelters</span>
          </label>
          <label className="layer-checkbox">
            <input 
              type="checkbox" 
              checked={showHospitals} 
              onChange={(e) => setInternalShowHospitals(e.target.checked)} 
            />
            <span className="checkbox-label">Hospitals</span>
          </label>
          <label className="layer-checkbox">
            <input 
              type="checkbox" 
              checked={showIncidents} 
              onChange={(e) => setInternalShowIncidents(e.target.checked)} 
            />
            <span className="checkbox-label">Citizen Reports</span>
          </label>
          {route && (
            <label className="layer-checkbox">
              <input 
                type="checkbox" 
                checked={showRoute} 
                onChange={(e) => setInternalShowRoute(e.target.checked)} 
              />
              <span className="checkbox-label">Evac Route</span>
            </label>
          )}
        </div>
      )}

      <MapContainer 
        className="leaflet-map" 
        center={center} 
        zoom={12} 
        scrollWheelZoom 
        zoomControl={false}
      >
        <ZoomControl position="topright" />
        <MapAutoResizer routePositions={routePositions} centerCoords={location} />
        <MapClickHandler onLocationSelect={onLocationSelect} />
        <MapTileLayer tileMode={currentTileMode} onTileErrorChange={setHasTileError} />

        {/* User Location Marker & Accuracy Halo */}
        {location && (
          <>
            <CircleMarker
              center={[location.latitude, location.longitude]}
              pathOptions={{ color: '#0284c7', fillColor: '#38bdf8', fillOpacity: 0.25, weight: 1.5 }}
              radius={24}
            />
            <CircleMarker
              center={[location.latitude, location.longitude]}
              pathOptions={{ color: '#ffffff', fillColor: '#0ea5e9', fillOpacity: 1.0, weight: 3 }}
              radius={8}
            >
              <Popup>
                <div style={{ minWidth: '180px' }}>
                  <strong style={{ color: '#0ea5e9' }}>Selected Location</strong>
                  <div style={{ fontSize: '12px', marginTop: '4px' }}>
                    {location.latitude.toFixed(5)}°N, {location.longitude.toFixed(5)}°E
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                    Click anywhere on map to inspect location
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          </>
        )}

        {/* Flood Hazard Zones */}
        {showHazards && floodHazards && floodHazards.map((hazard) => {
          const isAuth = hazard.data_status === 'AUTHORITATIVE'
          const isDemo = hazard.data_status === 'DEMO'
          const isStale = hazard.data_status === 'STALE' || hazard.is_stale

          let strokeColor = '#f59e0b'
          let fillColor = '#f59e0b'
          let fillOpacity = 0.22
          let dashArray = '6, 6'

          if (isAuth) {
            strokeColor = '#ef4444'
            fillColor = '#ef4444'
            fillOpacity = 0.35
            dashArray = undefined
          } else if (isDemo) {
            strokeColor = '#c084fc'
            fillColor = '#c084fc'
            fillOpacity = 0.25
            dashArray = '4, 4'
          } else if (isStale) {
            strokeColor = '#64748b'
            fillColor = '#64748b'
            fillOpacity = 0.15
            dashArray = '4, 4'
          }

          if (hazard.geometry?.type === 'Polygon' && hazard.geometry.coordinates?.[0]) {
            const latLngs = hazard.geometry.coordinates[0].map(([lon, lat]) => [lat, lon])
            return (
              <Polygon
                key={hazard.hazard_id}
                positions={latLngs}
                pathOptions={{
                  color: strokeColor,
                  fillColor: fillColor,
                  fillOpacity: fillOpacity,
                  weight: isAuth ? 2.5 : 2,
                  dashArray: dashArray
                }}
              >
                <Popup>
                  <div style={{ minWidth: '220px', maxWidth: '300px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                      <strong style={{ fontSize: '13px' }}>{hazard.title}</strong>
                      <span style={{ 
                        fontSize: '10px', 
                        padding: '2px 6px', 
                        borderRadius: '4px',
                        background: isAuth ? 'rgba(239,68,68,0.2)' : (isDemo ? 'rgba(168,85,247,0.2)' : 'rgba(245,158,11,0.2)'),
                        color: strokeColor,
                        fontWeight: 'bold',
                        whiteSpace: 'nowrap'
                      }}>
                        {hazard.data_status}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '6px', margin: '4px 0', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '10px', padding: '1px 6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px' }}>
                        Severity: <b>{hazard.severity}</b>
                      </span>
                      <span style={{ fontSize: '10px', padding: '1px 6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px' }}>
                        {hazard.hazard_type}
                      </span>
                      {hazard.source_type && (
                        <span style={{ fontSize: '10px', padding: '1px 6px', background: 'rgba(56,189,248,0.15)', color: '#38bdf8', borderRadius: '3px', fontWeight: 'bold' }}>
                          {hazard.source_type}
                        </span>
                      )}
                    </div>
                    {hazard.raw_value != null && hazard.measurement_unit && (
                      <div style={{ fontSize: '11px', color: '#38bdf8', margin: '2px 0', fontWeight: 'bold' }}>
                        Modelled Flow: {hazard.raw_value} {hazard.measurement_unit} (Uncalibrated)
                      </div>
                    )}
                    <p style={{ fontSize: '12px', margin: '6px 0', color: 'var(--text-main, #fff)' }}>{hazard.description}</p>
                    <div style={{ fontSize: '11px', color: '#94a3b8', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '4px', marginTop: '4px' }}>
                      <p style={{ margin: '2px 0' }}><strong>Source:</strong> {hazard.source_name}</p>
                      <p style={{ margin: '2px 0' }}><strong>Notice:</strong> {hazard.verification_note}</p>
                    </div>
                  </div>
                </Popup>
              </Polygon>
            )
          } else if (hazard.latitude && hazard.longitude && !hazard.geometry) {
            return (
              <CircleMarker
                key={hazard.hazard_id}
                center={[hazard.latitude, hazard.longitude]}
                pathOptions={{ color: strokeColor, fillColor: fillColor, fillOpacity: 0.7, weight: 2 }}
                radius={8}
              >
                <Popup>
                  <div style={{ minWidth: '220px' }}>
                    <strong>{hazard.title}</strong>
                    <div style={{ display: 'flex', gap: '6px', margin: '4px 0', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '10px', padding: '1px 6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px' }}>
                        <b>{hazard.data_status}</b>
                      </span>
                      <span style={{ fontSize: '10px', padding: '1px 6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px' }}>
                        {hazard.severity}
                      </span>
                    </div>
                    <p style={{ fontSize: '12px', margin: '4px 0' }}>{hazard.description}</p>
                  </div>
                </Popup>
              </CircleMarker>
            )
          }
          return null
        })}

        {/* Road Conditions */}
        {showRoads && roads && roads.map((road) => {
          if (!road.geometry || !road.geometry.coordinates) return null
          const isBlockedRoad = road.condition_status === 'BLOCKED' || road.condition_status === 'IMPASSABLE'
          const roadColor = isBlockedRoad ? '#ef4444' : '#10b981'
          const positions = road.geometry.coordinates.map(([lon, lat]) => [lat, lon])

          return (
            <Polyline
              key={road.road_id}
              positions={positions}
              pathOptions={{
                color: roadColor,
                weight: isBlockedRoad ? 4 : 2,
                opacity: 0.8,
                dashArray: isBlockedRoad ? '4, 4' : undefined
              }}
            >
              <Popup>
                <div style={{ minWidth: '180px' }}>
                  <strong>{road.road_name || 'Road Segment'}</strong>
                  <div style={{ fontSize: '11px', margin: '4px 0' }}>
                    Status: <span style={{ color: roadColor, fontWeight: 'bold' }}>{road.condition_status}</span>
                  </div>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                    {road.verification_note || 'Static OpenStreetMap network assessment.'}
                  </div>
                </div>
              </Popup>
            </Polyline>
          )
        })}

        {/* Facilities & Shelters */}
        {facilities && facilities.map((fac) => {
          const isHospital = fac.facility_type === 'HOSPITAL'
          if (isHospital && !showHospitals) return null
          if (!isHospital && !showShelters) return null

          const isSelected = selectedFacility && (
            (selectedFacility.facility_id && selectedFacility.facility_id === fac.facility_id) ||
            (selectedFacility.id && selectedFacility.id === fac.id)
          )

          const markerColor = isHospital ? '#a855f7' : '#10b981'
          const markerRadius = isSelected ? 12 : 7

          return (
            <CircleMarker
              key={fac.facility_id || fac.id || `${fac.name}-${fac.latitude}`}
              center={[fac.latitude, fac.longitude]}
              pathOptions={{
                color: isSelected ? '#ffffff' : markerColor,
                fillColor: markerColor,
                fillOpacity: isSelected ? 1.0 : 0.85,
                weight: isSelected ? 3 : 1.5
              }}
              radius={markerRadius}
            >
              <Popup>
                <div style={{ minWidth: '220px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ fontSize: '13px' }}>{fac.name}</strong>
                    <span style={{ 
                      fontSize: '10px', 
                      padding: '2px 6px', 
                      borderRadius: '4px', 
                      background: isHospital ? 'rgba(168,85,247,0.2)' : 'rgba(16,185,129,0.2)',
                      color: markerColor,
                      fontWeight: 'bold'
                    }}>
                      {fac.facility_type || 'SHELTER'}
                    </span>
                  </div>
                  <p style={{ fontSize: '11px', color: '#cbd5e1', margin: '4px 0' }}>
                    {fac.verification_note || 'Safety condition: Not verified.'}
                  </p>
                  {fac.distance_km != null && (
                    <p style={{ fontSize: '12px', fontWeight: 'bold', margin: '4px 0', color: '#0ea5e9' }}>
                      {fac.distance_km.toFixed(2)} km from location
                    </p>
                  )}
                  <button
                    type="button"
                    style={{ 
                      marginTop: '8px', 
                      width: '100%', 
                      padding: '6px 10px', 
                      background: '#0ea5e9', 
                      color: 'white', 
                      border: 'none', 
                      borderRadius: '4px', 
                      cursor: 'pointer',
                      fontWeight: 'bold'
                    }}
                    onClick={() => {
                      if (onFacilitySelect) onFacilitySelect(fac)
                    }}
                  >
                    Select as Destination
                  </button>
                </div>
              </Popup>
            </CircleMarker>
          )
        })}

        {/* Citizen Incident Reports Layer */}
        {showIncidents && incidents && incidents.map((inc) => {
          const isVerified = inc.verification_status === 'VERIFIED_MUNICIPAL'
          const isPending = inc.verification_status === 'PENDING_REVIEW'
          const isResolved = inc.verification_status === 'RESOLVED'
          const markerColor = isVerified ? '#10b981' : isResolved ? '#3b82f6' : '#f97316'
          
          return (
            <CircleMarker
              key={inc.incident_id || `${inc.latitude}-${inc.longitude}`}
              center={[inc.latitude, inc.longitude]}
              pathOptions={{
                color: '#ffffff',
                fillColor: markerColor,
                fillOpacity: 0.9,
                weight: 2
              }}
              radius={7}
            >
              <Popup>
                <div style={{ minWidth: '220px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{
                      fontSize: '10px',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontWeight: 'bold',
                      background: isVerified ? 'rgba(16,185,129,0.2)' : 'rgba(249,115,22,0.2)',
                      color: markerColor
                    }}>
                      {isVerified ? '✅ DRF VERIFIED' : isResolved ? 'COMPLETED' : '⚠️ CITIZEN REPORT (UNVERIFIED)'}
                    </span>
                    <span style={{ fontSize: '10px', color: '#94a3b8' }}>
                      {inc.incident_category?.replace('_', ' ')}
                    </span>
                  </div>
                  <strong style={{ fontSize: '13px', display: 'block', margin: '4px 0' }}>{inc.title}</strong>
                  <p style={{ fontSize: '11px', color: '#cbd5e1', margin: '4px 0', lineHeight: '1.4' }}>
                    {inc.description}
                  </p>
                  <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '6px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '4px' }}>
                    <span>Severity: <strong>{inc.severity}</strong></span>
                    {inc.report_count > 1 && (
                      <span style={{ marginLeft: '8px', color: '#38bdf8' }}>👥 {inc.report_count} reports</span>
                    )}
                    <div style={{ marginTop: '2px' }}>
                      Reported: {inc.reported_at ? new Date(inc.reported_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recent'}
                    </div>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          )
        })}

        {/* Alternative Routes if computed */}
        {showRoute && route?.alternatives && route.alternatives.map((alt, idx) => {
          if (!alt.geometry || alt.geometry.length < 2) return null
          const altPositions = alt.geometry.map(([longitude, latitude]) => [latitude, longitude])
          return (
            <Polyline
              key={`alt-route-${idx}`}
              positions={altPositions}
              pathOptions={{
                color: '#a855f7',
                weight: 3.5,
                opacity: 0.75,
                dashArray: '6, 8'
              }}
            >
              <Popup>
                <div style={{ minWidth: '180px' }}>
                  <strong style={{ color: '#a855f7' }}>Alternative Route #{idx + 1}</strong>
                  <div style={{ fontSize: '11px', marginTop: '4px' }}>
                    Distance: <strong>{alt.route_distance_km?.toFixed(2)} km</strong>
                  </div>
                  <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                    {alt.warning_note || 'Secondary trajectory calculated avoiding primary road segments'}
                  </div>
                </div>
              </Popup>
            </Polyline>
          )
        })}

        {/* Evacuation Route Polyline (Two-layer: white casing under colored line) */}
        {showRoute && routePositions.length > 1 && (
          <>
            <Polyline 
              positions={routePositions} 
              pathOptions={{ 
                color: '#ffffff', 
                weight: 7, 
                opacity: 0.9 
              }} 
            />
            <Polyline 
              positions={routePositions} 
              pathOptions={{ 
                color: isDetour ? '#f59e0b' : '#1d5fd1', 
                weight: 4, 
                opacity: 1.0,
                dashArray: isDetour ? '8, 6' : undefined
              }} 
            />
          </>
        )}

        {loading && <div className="leaflet-loading" aria-label="Loading map data">Loading map data...</div>}
      </MapContainer>

      {hasTileError && (
        <div className="map-tile-error-banner" role="alert">
          <span>⚠️ Basemap tile provider issue detected. Map data may be degraded.</span>
          <button type="button" onClick={handleRetry} className="map-tile-retry-btn">
            Retry Tiles
          </button>
        </div>
      )}

      {/* Modern Floating Map Legend */}
      <div className="map-legend-bar">
        <span className="legend-item"><i className="legend-dot user" />Your Location</span>
        <span className="legend-item"><i className="legend-dot" style={{ backgroundColor: '#10b981' }} />Shelter</span>
        <span className="legend-item"><i className="legend-dot" style={{ backgroundColor: '#a855f7' }} />Hospital</span>
        <span className="legend-item"><i className="legend-dot" style={{ backgroundColor: '#ef4444' }} />Flooded Road</span>
        <span className="legend-item"><i className="legend-dot" style={{ backgroundColor: '#ef4444', border: '1px solid #fff' }} />Authoritative Alert</span>
        <span className="legend-item"><i className="legend-dot" style={{ backgroundColor: '#f59e0b' }} />Municipal Flood Zone</span>
        <span className="legend-item"><i className="legend-dot" style={{ backgroundColor: '#f97316', border: '1px solid #fff' }} />Citizen Report</span>
        <span className="legend-item"><i className="legend-dot" style={{ backgroundColor: '#c084fc' }} />[DEMO] Hazard</span>
        <span className="legend-item"><i className="legend-dot" style={{ backgroundColor: '#1d5fd1' }} />OSM Route</span>
        <span className="legend-item"><i className="legend-dot" style={{ backgroundColor: '#f59e0b' }} />Hazard Detour</span>
        {route?.alternatives && route.alternatives.length > 0 && (
          <span className="legend-item"><i className="legend-dot" style={{ backgroundColor: '#a855f7' }} />Alternative Route</span>
        )}
      </div>
    </div>
  )
}
