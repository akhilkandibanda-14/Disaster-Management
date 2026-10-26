import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, Polygon, Polyline, Popup, TileLayer, ZoomControl, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import OperationsDashboard from './components/OperationsDashboard'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const hyderabadLocation = { latitude: 17.385, longitude: 78.486 }
const isInHyderabad = ({ latitude, longitude }) => latitude >= 17.2 && latitude <= 17.6 && longitude >= 78.2 && longitude <= 78.7

const riskColors = {
  HIGH: '#ef4444',
  MEDIUM: '#f59e0b',
  LOW: '#10b981',
}

function MapAutoResizer({ routePositions }) {
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
        map.fitBounds(routePositions, { padding: [40, 40], maxZoom: 14 })
      } catch {
        // Safe fallback
      }
    }
  }, [map, routePositions])

  return null
}

function MapTileLayer({ onTileErrorChange }) {
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
  }, [map, onTileErrorChange])

  return (
    <TileLayer
      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      maxZoom={19}
    />
  )
}

function RiskMap({ riskData, location, facilities, selectedFacility, onFacilitySelect, roads, route, floodHazards, loading }) {
  const [hasTileError, setHasTileError] = useState(false)
  const center = [(17.2 + 17.6) / 2, (78.2 + 78.7) / 2]
  const routePositions = route?.geometry?.map(([longitude, latitude]) => [latitude, longitude]) ?? []
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
    <>
      <MapContainer className="leaflet-map" center={center} zoom={11} scrollWheelZoom zoomControl={false}>
        <ZoomControl position="topright" />
        <MapAutoResizer routePositions={routePositions} />
        <MapTileLayer onTileErrorChange={setHasTileError} />
      
      {/* Flood Hazard Zones & Alerts */}
      {floodHazards && floodHazards.map((hazard) => {
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
                    {hazard.geographic_uncertainty && (
                      <p style={{ margin: '2px 0', color: '#cbd5e1', fontStyle: 'italic' }}><strong>Spatial Limit:</strong> {hazard.geographic_uncertainty}</p>
                    )}
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
                    {hazard.source_type && (
                      <span style={{ fontSize: '10px', padding: '1px 6px', background: 'rgba(56,189,248,0.15)', color: '#38bdf8', borderRadius: '3px', fontWeight: 'bold' }}>
                        {hazard.source_type}
                      </span>
                    )}
                  </div>
                  {hazard.raw_value != null && hazard.measurement_unit && (
                    <div style={{ fontSize: '11px', color: '#38bdf8', margin: '2px 0', fontWeight: 'bold' }}>
                      Modelled Discharge: {hazard.raw_value} {hazard.measurement_unit}
                    </div>
                  )}
                  <p style={{ fontSize: '12px', margin: '4px 0' }}>{hazard.description}</p>
                  <div style={{ fontSize: '11px', color: '#94a3b8', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '4px', marginTop: '4px' }}>
                    <p style={{ margin: '2px 0' }}><strong>Source:</strong> {hazard.source_name}</p>
                    {hazard.geographic_uncertainty && (
                      <p style={{ margin: '2px 0', color: '#cbd5e1', fontStyle: 'italic' }}><strong>Limitation:</strong> {hazard.geographic_uncertainty}</p>
                    )}
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          )
        }
        return null
      })}
      
      {/* Risk Point */}
      {riskData && riskData.prediction_available && riskData.risk_level && (
        <CircleMarker
          center={[riskData.latitude, riskData.longitude]}
          pathOptions={{ 
            color: riskColors[riskData.risk_level] || '#94a3b8', 
            fillColor: riskColors[riskData.risk_level] || '#94a3b8', 
            fillOpacity: 0.35, 
            weight: 2 
          }}
          radius={40}
        >
          <Popup>{riskData.risk_level} risk at queried location</Popup>
        </CircleMarker>
      )}

      {/* User Live Location */}
      <CircleMarker center={[location.latitude, location.longitude]} pathOptions={{ color: '#0ea5e9', fillColor: '#0ea5e9', fillOpacity: 1, weight: 3 }} radius={7}>
        <Popup><strong>Your live location</strong><br/>{location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}</Popup>
      </CircleMarker>

      {/* Reported Road Hazards / Flooded Roads */}
      {roads && roads.map((road, idx) => {
        const isHazard = ['FLOODED', 'BLOCKED', 'DANGEROUS'].includes(road.status?.toUpperCase())
        if (!isHazard) return null
        return (
          <CircleMarker
            key={`hazard-${idx}`}
            center={[road.latitude, road.longitude]}
            pathOptions={{ color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.85, weight: 2 }}
            radius={6}
          >
            <Popup>
              <div style={{ minWidth: '160px' }}>
                <strong style={{ color: '#ef4444' }}>⚠️ Road Hazard ({road.status})</strong>
                <p style={{ margin: '4px 0', fontWeight: 'bold' }}>{road.road_name}</p>
                <small style={{ color: '#64748b' }}>{road.notes || 'Reported blocked segment'}</small>
              </div>
            </Popup>
          </CircleMarker>
        )
      })}
      
      {/* Emergency Facilities & Shelters */}
      {facilities && facilities.map((fac) => {
        const isSelected = selectedFacility && (selectedFacility.facility_id === fac.facility_id || (selectedFacility.id && selectedFacility.id === fac.id))
        const isHospital = fac.facility_type === 'HOSPITAL'
        const markerColor = isHospital ? '#a855f7' : '#10b981'

        return (
          <CircleMarker
            key={fac.facility_id || fac.id || `${fac.name}-${fac.latitude}-${fac.longitude}`}
            center={[fac.latitude, fac.longitude]}
            pathOptions={{ 
              color: isSelected ? '#38bdf8' : markerColor, 
              fillColor: markerColor, 
              fillOpacity: isSelected ? 1 : 0.7, 
              weight: isSelected ? 3 : 1 
            }}
            radius={isSelected ? 9 : (isHospital ? 7 : 5)}
          >
            <Popup>
              <div style={{ minWidth: '200px' }}>
                <strong>{fac.name}</strong>
                <div style={{ display: 'flex', gap: '6px', margin: '4px 0' }}>
                  <span style={{ fontSize: '10px', padding: '2px 6px', background: isHospital ? 'rgba(168,85,247,0.15)' : 'rgba(16,185,129,0.15)', color: markerColor, borderRadius: '4px', fontWeight: 'bold' }}>
                    {fac.facility_type || 'SHELTER'}
                  </span>
                  <span style={{ fontSize: '10px', padding: '2px 6px', background: 'rgba(245,158,11,0.15)', color: '#f59e0b', borderRadius: '4px', fontWeight: 'bold' }}>
                    {fac.data_status || 'PUBLIC_UNVERIFIED'}
                  </span>
                </div>
                {fac.address && <p style={{ fontSize: '12px', margin: '4px 0', color: '#64748b' }}>{fac.address}</p>}
                <p style={{ fontSize: '12px', margin: '2px 0' }}>
                  Operational Status: <strong>{fac.operational_status_verified ? (fac.operational_status || 'OPERATIONAL') : `${fac.operational_status || 'UNKNOWN'} (Unverified)`}</strong>
                </p>
                <p style={{ fontSize: '12px', margin: '2px 0' }}>
                  Capacity: {fac.capacity != null ? `${fac.capacity}` : 'Not publicly verified'}
                </p>
                <p style={{ fontSize: '11px', margin: '4px 0', color: '#94a3b8' }}>
                  Source: {fac.source || 'Local directory'}
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
                  onClick={() => onFacilitySelect(fac)}
                >
                  Select as Destination
                </button>
              </div>
            </Popup>
          </CircleMarker>
        )
      })}

      {/* Evacuation Route Polyline */}
      {routePositions.length > 1 && (
        <Polyline 
          positions={routePositions} 
          pathOptions={{ 
            color: isDetour ? '#f59e0b' : '#38bdf8', 
            weight: 5, 
            opacity: 0.9,
            dashArray: isDetour ? '8, 6' : undefined
          }} 
        />
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
    </>
  )
}

function App() {
  const [apiStatus, setApiStatus] = useState('Checking API...')
  const [location, setLocation] = useState(hyderabadLocation)
  const [locationStatus, setLocationStatus] = useState('Hyderabad center location')
  const [weather, setWeather] = useState(null)
  const [riskData, setRiskData] = useState(null)
  const [recommendationResponse, setRecommendationResponse] = useState(null)
  const [facilities, setFacilities] = useState([])
  const [facilityTypeFilter, setFacilityTypeFilter] = useState('ALL')
  const [selectedFacility, setSelectedFacility] = useState(null)
  const [route, setRoute] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [shelters, setShelters] = useState([])
  const [roads, setRoads] = useState([])
  const [gauges, setGauges] = useState([])
  const [hydrology, setHydrology] = useState(null)
  const [floodHazards, setFloodHazards] = useState([])
  const [hazardWarning, setHazardWarning] = useState(null)
  const [view, setView] = useState('citizen')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const request = async (path, options) => {
    const response = await fetch(`${apiBaseUrl}${path}`, options)
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      throw new Error(payload.detail ?? `Request failed: ${response.status}`)
    }
    return response.json()
  }

  const loadDashboard = async (currentLocation) => {
    setLoading(true)
    setError('')
    const query = `latitude=${currentLocation.latitude}&longitude=${currentLocation.longitude}`
    const recQuery = `${query}&radius_km=15.0&top_n=3`
    try {
      const [
        health, 
        weatherData, 
        riskRes, 
        shelterRes, 
        facilityRes, 
        alertData, 
        shelterList, 
        roadList, 
        gaugeList, 
        hydroData,
        hazardData,
        locationWarningData
      ] = await Promise.all([
        request('/health').catch(() => ({})),
        request(`/weather?${query}`).catch(() => null),
        request(`/risk-map?${query}`).catch(() => null),
        request(`/shelters/recommended?${recQuery}`).catch(() => null),
        request(`/emergency-facilities?${query}&radius_km=25.0`).catch(() => ({ facilities: [] })),
        request('/disaster-alerts').catch(() => []),
        request('/shelters').catch(() => ({ shelters: [] })),
        request('/road-conditions').catch(() => []),
        request('/gauges').catch(() => []),
        request(`/hydrology/water-level?${query}`).catch(() => null),
        request('/flood-hazards').catch(() => ({ hazards: [] })),
        request(`/flood-hazards/check-location?${query}`).catch(() => null)
      ])
      
      setApiStatus(health?.demo_mode ? 'API online - demo mode' : 'API online')
      setWeather(weatherData)
      setRiskData(riskRes)
      setRecommendationResponse(shelterRes)
      
      const allFacilities = facilityRes?.facilities || []
      setFacilities(allFacilities)
      
      // Auto-select recommended shelter if nothing selected yet
      if (shelterRes?.recommendations?.[0]) {
        setSelectedFacility(shelterRes.recommendations[0])
      } else if (allFacilities.length > 0) {
        setSelectedFacility(allFacilities[0])
      }
      
      setAlerts(alertData || [])
      setShelters(shelterList?.shelters || [])
      setRoads(roadList || [])
      setGauges(gaugeList || [])
      setHydrology(hydroData)
      setFloodHazards(hazardData?.hazards || [])
      setHazardWarning(locationWarningData)
      setRoute(null)
    } catch (loadError) {
      setApiStatus('API unavailable')
      setError(loadError.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!navigator.geolocation) {
      loadDashboard(hyderabadLocation)
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const currentLocation = { latitude: position.coords.latitude, longitude: position.coords.longitude }
        if (isInHyderabad(currentLocation)) {
          setLocation(currentLocation)
          setLocationStatus('Live location active')
          loadDashboard(currentLocation)
          return
        }
        setLocationStatus('Outside Hyderabad - center location active')
        loadDashboard(hyderabadLocation)
      },
      () => {
        setLocationStatus('Location unavailable - Hyderabad center active')
        loadDashboard(hyderabadLocation)
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 },
    )
  }, [])

  const handleLocationSelect = (newLocation) => {
    setLocation(newLocation)
    setLocationStatus('Map click location selected')
    loadDashboard(newLocation)
  }

  const handleFacilitySelect = (facility) => {
    setSelectedFacility(facility)
    // Clear previous route when selecting new destination
    setRoute(null)
  }

  const navigateAction = async () => {
    if (!selectedFacility) return
    try {
      setError('')
      const destLat = selectedFacility.latitude
      const destLon = selectedFacility.longitude
      const facId = selectedFacility.facility_id || selectedFacility.id
      
      const data = await request('/evacuation-route', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ 
          origin: { latitude: location.latitude, longitude: location.longitude },
          destination: { latitude: destLat, longitude: destLon },
          facility_id: facId ? String(facId) : undefined
        }) 
      })
      setRoute(data)
    } catch (routeError) {
      setError(routeError.message)
    }
  }

  const refreshDashboard = () => {
    setError('')
    if (!navigator.geolocation) {
      setLocationStatus('Location unavailable - Hyderabad center active')
      loadDashboard(hyderabadLocation)
      return
    }

    setLocationStatus('Refreshing live location...')
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const currentLocation = { latitude: position.coords.latitude, longitude: position.coords.longitude }
        if (isInHyderabad(currentLocation)) {
          setLocation(currentLocation)
          setLocationStatus('Live location active')
          loadDashboard(currentLocation)
          return
        }
        setLocationStatus('Outside Hyderabad - center location active')
        loadDashboard(hyderabadLocation)
      },
      () => {
        setLocationStatus('Location unavailable - Hyderabad center active')
        loadDashboard(hyderabadLocation)
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 },
    )
  }

  const filteredFacilities = useMemo(() => {
    if (facilityTypeFilter === 'ALL') return facilities
    return facilities.filter(f => f.facility_type === facilityTypeFilter)
  }, [facilities, facilityTypeFilter])

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">SAFEMAP AI · FLOOD RESPONSE SYSTEM</p>
          <h1>Flood Management & Evacuation</h1>
        </div>
        <div className="topbar-actions">
          <div className="view-switch" aria-label="Dashboard view">
            <button className={view === 'citizen' ? 'active' : ''} type="button" onClick={() => setView('citizen')}>Citizen</button>
            <button className={view === 'operations' ? 'active' : ''} type="button" onClick={() => setView('operations')}>Operations</button>
          </div>
          <span className="status-pill">{apiStatus}</span>
        </div>
      </header>

      <section className="alert-banner" aria-label="Current system state">
        <span className="alert-mark">!</span>
        <div>
          {riskData?.data_readiness_status === 'INSUFFICIENT_LOCAL_DATA' || riskData?.coverage_status === 'MODEL_UNSUPPORTED' ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '4px' }}>
                <strong>AUTOMATED PREDICTION INACTIVE (MODEL COVERAGE GUARD)</strong>
                <span style={{ fontSize: '10.5px', background: 'rgba(59,130,246,0.25)', color: '#93c5fd', padding: '1px 6px', borderRadius: '3px', fontWeight: '500' }}>
                  APPLICATION OPERATIONAL
                </span>
                <span style={{ fontSize: '10.5px', background: 'rgba(234,179,8,0.25)', color: '#fde047', padding: '1px 6px', borderRadius: '3px', fontWeight: '500' }}>
                  SAFEGUARD ACTIVE
                </span>
              </div>
              <p>{riskData?.provenance_note || 'The selected location is outside current INDOFLOODS model coverage (>50 km from nearest gauge). Automated prediction is intentionally suppressed to prevent unvalidated extrapolation.'}</p>
            </>
          ) : riskData?.data_readiness_status === 'DATA_UNAVAILABLE' ? (
            <>
              <strong>DATA UNAVAILABLE</strong>
              <p>{riskData?.provenance_note || 'External meteorological or hydrological telemetry could not be retrieved. Missing data does NOT imply safety.'}</p>
            </>
          ) : (
            <>
              <strong>DEMO HYDROLOGY & ROAD CONDITIONS</strong>
              <p>Simulated hazard conditions are explicitly labeled [DEMO]. Real-time live municipal telemetry is not active. Always follow official flood management and emergency directives during actual emergencies.</p>
            </>
          )}
        </div>
      </section>

      {error && <div className="error-banner" role="alert">{error}</div>}

      {/* Location-based Flood Hazard Intersection Warning */}
      {hazardWarning && hazardWarning.is_in_hazard_zone && (
        <section 
          className="alert-banner" 
          style={{ 
            background: 'rgba(239, 68, 68, 0.15)', 
            border: '1px solid #ef4444', 
            marginBottom: '16px' 
          }}
          aria-label="Active flood hazard at location"
        >
          <span className="alert-mark" style={{ background: '#ef4444', color: 'white' }}>⚠️</span>
          <div>
            <strong style={{ color: '#f87171', fontSize: '1.05rem' }}>
              ACTIVE FLOOD HAZARD AT YOUR LOCATION ({hazardWarning.highest_severity} SEVERITY)
            </strong>
            <p style={{ margin: '4px 0 6px 0', fontSize: '13px' }}>
              Your reported coordinates intersect {hazardWarning.hazard_count} active flood-prone or official alert zone(s):
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {hazardWarning.intersected_hazards.map((hz) => (
                <div key={hz.hazard_id} style={{ fontSize: '12px', background: 'rgba(0,0,0,0.25)', padding: '6px 10px', borderRadius: '4px' }}>
                  <strong>{hz.title}</strong> · <span style={{ color: '#fca5a5' }}>{hz.severity}</span> · <span style={{ color: '#f59e0b' }}>{hz.data_status}</span>
                  <div style={{ color: '#cbd5e1', fontSize: '11px', marginTop: '2px' }}>{hz.description}</div>
                </div>
              ))}
            </div>
            <p style={{ fontSize: '11px', color: '#fca5a5', marginTop: '8px', lineHeight: '1.4' }}>
              <strong>Safety Limitation Notice:</strong> {hazardWarning.disclaimer}
            </p>
          </div>
        </section>
      )}

      {view === 'operations' ? (
        <OperationsDashboard 
          apiBaseUrl={apiBaseUrl}
          apiStatus={apiStatus}
          weather={weather}
          riskData={riskData}
          shelters={shelters}
          facilities={facilities}
          roads={roads}
          location={location}
          route={route}
          gauges={gauges}
          hydrology={hydrology}
          alerts={alerts}
          floodHazards={floodHazards}
          hazardWarning={hazardWarning}
          onLocationSelect={handleLocationSelect}
        />

      ) : (
        <section className="workspace-grid">
          <div className="map-panel" aria-label="Flood risk map">
            <RiskMap 
              riskData={riskData} 
              location={location} 
              facilities={facilities}
              selectedFacility={selectedFacility}
              onFacilitySelect={handleFacilitySelect}
              roads={roads}
              route={route} 
              floodHazards={floodHazards}
              loading={loading} 
            />
            {!loading && !riskData && (
              <div className="map-copy">
                <span className="map-pin">!</span>
                <h2>Map data unavailable</h2>
                <p>Start the FastAPI backend to load the risk map.</p>
              </div>
            )}
            <div className="map-legend">
              <span><i className="legend-dot user" />Your location</span>
              <span><i className="legend-dot safe" style={{backgroundColor: '#10b981'}} />Shelter</span>
              <span><i className="legend-dot" style={{backgroundColor: '#a855f7'}} />Hospital</span>
              <span><i className="legend-dot" style={{backgroundColor: '#ef4444'}} />Flooded Road</span>
              <span><i className="legend-dot" style={{backgroundColor: '#ef4444', border: '1px solid #fff'}} />Authoritative Alert</span>
              <span><i className="legend-dot" style={{backgroundColor: '#f59e0b'}} />Municipal Flood Zone</span>
              <span><i className="legend-dot" style={{backgroundColor: '#c084fc'}} />[DEMO] Hazard</span>
              <span><i className="legend-dot route" style={{backgroundColor: '#38bdf8'}} />OSM Route</span>
              <span><i className="legend-dot" style={{backgroundColor: '#f59e0b'}} />Hazard Detour</span>
            </div>
          </div>

          <aside className="side-panel">
            {/* Current Location Card */}
            <article className="info-card location-card">
              <div>
                <p className="card-label">YOUR LOCATION</p>
                <strong>{locationStatus}</strong>
                <p className="muted">{location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}</p>
              </div>
              <button type="button" onClick={refreshDashboard} disabled={loading}>{loading ? 'Refreshing...' : 'Refresh'}</button>
            </article>

            {/* Location Hazard Assessment Card */}
            <article className="info-card">
              <p className="card-label">LOCATION FLOOD HAZARD STATUS</p>
              {hazardWarning ? (
                <>
                  <div className="metric-row" style={{ flexWrap: 'wrap', gap: '8px' }}>
                    <strong>{hazardWarning.is_in_hazard_zone ? 'Hazard Zone Intersection' : 'No Hazard Zone Intersected'}</strong>
                    <span 
                      className="neutral-badge" 
                      style={{ 
                        background: hazardWarning.is_in_hazard_zone ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.15)', 
                        color: hazardWarning.is_in_hazard_zone ? '#f87171' : '#34d399',
                        fontWeight: 'bold',
                        fontSize: '11px',
                        letterSpacing: '0.02em',
                        textAlign: 'right'
                      }}
                    >
                      {hazardWarning.is_in_hazard_zone ? `${hazardWarning.highest_severity} HAZARD` : 'NO KNOWN HAZARD INTERSECTS THIS LOCATION'}
                    </span>
                  </div>

                  {hazardWarning.is_in_hazard_zone && hazardWarning.intersected_hazards?.length > 0 && (
                    <div style={{ marginTop: '8px', padding: '8px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '6px' }}>
                      <p style={{ margin: '0 0 4px', fontSize: '11px', color: '#fca5a5', fontWeight: 'bold' }}>
                        Intersecting Flood Hazards ({hazardWarning.hazard_count}):
                      </p>
                      {hazardWarning.intersected_hazards.map((hz) => (
                        <div key={hz.hazard_id} style={{ fontSize: '11.5px', color: '#fecaca', marginBottom: '2px' }}>
                          • <strong>{hz.title}</strong> [{hz.hazard_type}] — {hz.severity}
                        </div>
                      ))}
                    </div>
                  )}

                  <p className="muted" style={{ margin: '8px 0 4px 0', fontSize: '12px' }}>
                    Spatial rule: {hazardWarning.spatial_rule}
                  </p>
                  <p style={{ margin: '6px 0 0 0', fontSize: '11px', color: '#94a3b8', fontStyle: 'italic' }}>
                    {hazardWarning.disclaimer}
                  </p>
                </>
              ) : (
                <p className="muted" style={{ margin: '8px 0', fontSize: '12px' }}>
                  Evaluating location coordinates against flood hazard boundaries...
                </p>
              )}
            </article>

            {/* Flood Prediction Status Card */}
            <article className="info-card">
              <p className="card-label">FLOOD PREDICTION & DATA READINESS</p>
              {riskData ? (
                <>
                  <div className="metric-row">
                    <strong>
                      {riskData.prediction_available 
                        ? 'Flood prediction available' 
                        : (riskData.data_readiness_status === 'INSUFFICIENT_LOCAL_DATA'
                            ? 'Prediction Withheld (Coverage Guard)'
                            : (riskData.data_readiness_status === 'DATA_UNAVAILABLE'
                                ? 'Data Unavailable'
                                : 'Flood prediction unavailable'))}
                    </strong>
                    <span className="neutral-badge" style={{
                      color: riskData.data_readiness_status === 'INSUFFICIENT_LOCAL_DATA' ? '#fde047' : undefined,
                      borderColor: riskData.data_readiness_status === 'INSUFFICIENT_LOCAL_DATA' ? 'rgba(234,179,8,0.4)' : undefined,
                      background: riskData.data_readiness_status === 'INSUFFICIENT_LOCAL_DATA' ? 'rgba(234,179,8,0.15)' : undefined
                    }}>
                      {riskData.data_readiness_status || riskData.coverage_status}
                    </span>
                  </div>
                  {riskData.prediction_available ? (
                    <>
                      <p className="muted" style={{marginTop: "8px", color: "white"}}>Risk level: {riskData.risk_level}</p>
                      {riskData.probability !== undefined && riskData.probability !== null && (
                        <p className="muted">Model severe-flood probability: {(riskData.probability * 100).toFixed(1)}%</p>
                      )}
                      <p className="muted">Model: INDOFLOODS flood severity model</p>
                      {riskData.provenance_note && (
                        <p style={{ fontSize: '11px', color: '#94a3b8', marginTop: '6px' }}>{riskData.provenance_note}</p>
                      )}
                    </>
                  ) : (
                    <div style={{ marginTop: '8px' }}>
                      <div style={{ padding: '7px 9px', background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.25)', borderRadius: '4px', marginBottom: '8px' }}>
                        <p style={{ margin: 0, fontSize: '11px', color: '#93c5fd', lineHeight: '1.4' }}>
                          ℹ️ <strong>System Operational:</strong> Prediction is unavailable because local hydrological evidence is insufficient—not because the application has crashed.
                        </p>
                      </div>
                      <p className="muted" style={{ fontSize: '12px', color: '#fca5a5', lineHeight: '1.4' }}>
                        {riskData.provenance_note || 'The selected location is outside the current INDOFLOODS model coverage.'}
                      </p>
                      <div style={{ marginTop: '6px', fontSize: '11.5px', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                        <div>• Nearest INDOFLOODS gauge: <strong>{riskData.gauge_id || 'INDOFLOODS-gauge-916'} ({riskData.distance_km} km)</strong></div>
                        <div>• Model coverage limit: <strong>{riskData.coverage_limit_km || 50.0} km</strong></div>
                        <div>• INDOFLOODS gauges within 50 km: <strong>{riskData.gauges_within_50km_count ?? riskData.catchment_gauges_count ?? 0}</strong></div>
                        <div>• Prediction status: <strong style={{ color: '#fde047' }}>{riskData.data_readiness_status || 'INSUFFICIENT_LOCAL_DATA'}</strong></div>
                      </div>
                    </div>
                  )}

                  {riskData.safety_disclaimer && (
                    <div style={{ marginTop: '8px', padding: '6px 8px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '4px' }}>
                      <p style={{ margin: 0, fontSize: '10.5px', color: '#fca5a5', lineHeight: '1.4' }}>
                        ⚠️ <strong>Safety Notice (Distinguish from Low-Risk):</strong> {riskData.safety_disclaimer}
                      </p>
                    </div>
                  )}
                  
                  <div style={{marginTop: "12px", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "8px"}}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <p className="muted" style={{ fontSize: '11px', margin: 0 }}>
                        {weather?.condition ?? (loading ? 'Loading weather...' : 'Weather data unavailable')} · {
                          !weather ? (loading ? 'Loading rainfall data...' : 'Rainfall data unavailable') : 
                          (weather.rainfall == null ? 'Rainfall data unavailable' : `Rainfall: ${weather.rainfall} mm`)
                        }
                      </p>
                      {weather?.is_stale && (
                        <span style={{ fontSize: '9.5px', padding: '1px 5px', background: 'rgba(234,179,8,0.2)', color: '#fde047', borderRadius: '3px' }}>
                          STALE
                        </span>
                      )}
                      {weather?.source === 'DEMO / SIMULATED DATA' && (
                        <span style={{ fontSize: '9.5px', padding: '1px 5px', background: 'rgba(59,130,246,0.2)', color: '#93c5fd', borderRadius: '3px' }}>
                          SIMULATED
                        </span>
                      )}
                    </div>
                    {weather?.warning && (
                      <p style={{ margin: '4px 0 0', fontSize: '10px', color: '#fde047' }}>
                        ⚠️ {weather.warning}
                      </p>
                    )}
                  </div>
                </>
              ) : (
                <p className="muted">Waiting for risk-zone data.</p>
              )}
            </article>
            
            {/* Evacuation Destination Selection Card */}
            <article className="info-card">
              <p className="card-label">EVACUATION DESTINATION</p>

              {/* Type Filter Tabs */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '16px' }}>
                <button
                  type="button"
                  style={{ 
                    padding: '6px 12px', 
                    borderRadius: '6px', 
                    border: '1px solid var(--border-panel)',
                    background: facilityTypeFilter === 'ALL' ? 'var(--accent-primary)' : 'rgba(255,255,255,0.05)',
                    color: 'white',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    cursor: 'pointer'
                  }}
                  onClick={() => setFacilityTypeFilter('ALL')}
                >
                  All ({facilities.length})
                </button>
                <button
                  type="button"
                  style={{ 
                    padding: '6px 12px', 
                    borderRadius: '6px', 
                    border: '1px solid var(--border-panel)',
                    background: facilityTypeFilter === 'HOSPITAL' ? '#a855f7' : 'rgba(255,255,255,0.05)',
                    color: 'white',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    cursor: 'pointer'
                  }}
                  onClick={() => setFacilityTypeFilter('HOSPITAL')}
                >
                  Hospitals ({facilities.filter(f => f.facility_type === 'HOSPITAL').length})
                </button>
                <button
                  type="button"
                  style={{ 
                    padding: '6px 12px', 
                    borderRadius: '6px', 
                    border: '1px solid var(--border-panel)',
                    background: facilityTypeFilter === 'SHELTER' ? '#10b981' : 'rgba(255,255,255,0.05)',
                    color: 'white',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    cursor: 'pointer'
                  }}
                  onClick={() => setFacilityTypeFilter('SHELTER')}
                >
                  Shelters ({facilities.filter(f => f.facility_type === 'SHELTER').length})
                </button>
              </div>

              {selectedFacility ? (
                <>
                  <div style={{ padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <strong style={{ fontSize: '1.1rem', margin: 0 }}>{selectedFacility.name}</strong>
                      <span style={{ 
                        fontSize: '11px', 
                        padding: '2px 8px', 
                        borderRadius: '4px',
                        background: selectedFacility.facility_type === 'HOSPITAL' ? 'rgba(168,85,247,0.2)' : 'rgba(16,185,129,0.2)',
                        color: selectedFacility.facility_type === 'HOSPITAL' ? '#c084fc' : '#34d399',
                        fontWeight: 'bold'
                      }}>
                        {selectedFacility.facility_type || 'FACILITY'}
                      </span>
                    </div>

                    <p className="muted" style={{ margin: '6px 0', fontSize: '13px' }}>
                      {selectedFacility.distance_km != null ? `${selectedFacility.distance_km.toFixed(2)} km away` : 'Distance calculating...'} · Capacity: {selectedFacility.capacity != null ? `${selectedFacility.capacity} beds/spaces` : 'Not live verified'}
                    </p>
                    
                    {/* Verification Audit Breakdown */}
                    <div style={{ margin: '8px 0', padding: '6px 8px', background: 'rgba(255,255,255,0.02)', borderRadius: '4px', fontSize: '11.5px', border: '1px solid rgba(255,255,255,0.05)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                        <span style={{ color: '#94a3b8' }}>Location & Identity:</span>
                        <span style={{ color: selectedFacility.location_verified ? '#34d399' : '#fde047', fontWeight: 'bold' }}>
                          {selectedFacility.location_verified ? 'Verified (Official Registry)' : 'Unverified Listing'}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                        <span style={{ color: '#94a3b8' }}>Live Emergency Status:</span>
                        <span style={{ color: selectedFacility.operational_status_verified ? '#34d399' : '#f87171' }}>
                          {selectedFacility.operational_status_verified
                            ? `Verified (${selectedFacility.operational_status || 'OPERATIONAL'})`
                            : `Unverified (${selectedFacility.operational_status || 'UNKNOWN'}) — Not confirmed operational`}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: '#94a3b8' }}>Bed Occupancy / Space:</span>
                        <span style={{ color: selectedFacility.capacity_verified ? '#34d399' : '#94a3b8' }}>
                          {selectedFacility.capacity_verified ? 'Verified' : 'Unverified (Contact facility directly)'}
                        </span>
                      </div>
                    </div>

                    <p className="muted" style={{ margin: '4px 0', fontSize: '12px' }}>
                      Source: {selectedFacility.source || 'Public directory'}
                    </p>

                    <div className="route-note" style={{fontSize: "0.85em", color: "var(--warning)", borderColor: "var(--warning)", textAlign: "left", marginTop: "10px"}}>
                      <strong style={{fontSize: "0.95em", margin: "0 0 2px 0", color: "var(--warning)"}}>
                        {selectedFacility.data_status || 'PUBLIC_UNVERIFIED'} · {selectedFacility.verification_scope || 'IDENTITY_ONLY'}
                      </strong>
                      <span style={{color: "var(--text-main)", display: "block", marginTop: "2px"}}>
                        {selectedFacility.verification_note || 'Safety not independently verified. Real-time emergency readiness not guaranteed.'}
                      </span>
                    </div>
                  </div>
                  
                  <button className="primary-button" type="button" onClick={navigateAction}>
                    Calculate Hazard-Aware Evacuation Route
                  </button>

                  {/* Route Status & Recalculation Results */}
                  {route && (
                    <div style={{ 
                      marginTop: "16px", 
                      padding: "16px", 
                      background: route.route_status === 'NO_SAFE_ROUTE' ? "rgba(239,68,68,0.1)" : "rgba(14,165,233,0.06)", 
                      borderRadius: "10px", 
                      border: route.route_status === 'NO_SAFE_ROUTE' ? "1px solid rgba(239,68,68,0.4)" : "1px solid rgba(14,165,233,0.25)" 
                    }}>
                      {route.route_status === 'NO_SAFE_ROUTE' ? (
                        <>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171' }}>
                            <span style={{ fontSize: '1.4rem' }}>🚨</span>
                            <strong style={{ fontSize: '1.05rem', color: '#f87171' }}>NO SAFE ROUTE AVAILABLE</strong>
                          </div>
                          <p style={{ margin: '8px 0', fontSize: '13px', color: '#fca5a5' }}>
                            All available paths to this destination traverse reported flooded or blocked roads. Do not attempt travel along these paths.
                          </p>
                          <p style={{ margin: '4px 0', fontSize: '12px', color: '#94a3b8' }}>
                            Road condition status: <strong style={{ color: '#ef4444' }}>{route.road_condition_status}</strong>
                          </p>
                        </>
                      ) : (
                        <>
                          {route.is_rerouted || route.road_condition_status === 'HAZARDS_AVOIDED' ? (
                            <div style={{ padding: '8px 12px', background: 'rgba(245,158,11,0.15)', borderRadius: '6px', border: '1px solid rgba(245,158,11,0.3)', marginBottom: '10px' }}>
                              <strong style={{ color: '#f59e0b', fontSize: '13px' }}>🛡️ HAZARDS AVOIDED — Alternate Detour Recalculated</strong>
                              <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#fde68a' }}>
                                The shortest physical path crossed reported flooded/blocked road segments. The route was recalculated to bypass them. Unmonitored roads are not guaranteed clear.
                              </p>
                            </div>
                          ) : (
                            <div style={{ padding: '6px 10px', background: 'rgba(14,165,233,0.12)', borderRadius: '6px', border: '1px solid rgba(14,165,233,0.25)', marginBottom: '10px' }}>
                              <strong style={{ color: '#38bdf8', fontSize: '12px' }}>ℹ️ Evaluated Road Status: NO REPORTED HAZARDS</strong>
                              <p style={{ margin: '2px 0 0 0', fontSize: '11px', color: '#94a3b8' }}>
                                No active blockages on evaluated path. Unmonitored roads are not confirmed clear.
                              </p>
                            </div>
                          )}

                          <strong style={{fontSize: "1.05rem", display: "block", marginBottom: "6px"}}>
                            {route.destination_name ? `Route to ${route.destination_name}` : 'Road-network evacuation route'}
                          </strong>
                          <p className="muted" style={{margin: "4px 0", fontSize: "13px"}}>Route distance: <strong>{route.route_distance_km?.toFixed(2) ?? '?'} km</strong></p>
                          <p className="muted" style={{margin: "4px 0", fontSize: "13px"}}>Road network source: OpenStreetMap</p>
                          <p className="muted" style={{margin: "4px 0", fontSize: "13px"}}>Condition evaluation: <strong>{route.road_condition_status}</strong></p>
                        </>
                      )}

                      {/* Explicit Route Limitations (Objective 7) */}
                      <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                        <span style={{ fontSize: '11px', color: '#f59e0b', fontWeight: 'bold', display: 'block', marginBottom: '4px' }}>
                          ⚠️ IMPORTANT ROUTE SAFETY LIMITATION
                        </span>
                        <p style={{ margin: 0, fontSize: '11px', color: '#94a3b8', lineHeight: '1.4' }}>
                          Routes are automated decision-support paths and are <strong>NOT guaranteed flood-safe</strong>. Real-time flash flooding, unmonitored street ponding, or changing storm conditions may occur.
                        </p>
                        {route.warnings && route.warnings.length > 0 && (
                          <div style={{ marginTop: '8px' }}>
                            {route.warnings.map((w, idx) => (
                              <p key={idx} style={{ margin: '2px 0', fontSize: '11px', color: '#cbd5e1' }}>• {w}</p>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Nearby Alternative Facilities List */}
                  {filteredFacilities.length > 1 && (
                    <div style={{marginTop: "20px"}}>
                      <p className="card-label">NEARBY EMERGENCY FACILITIES (CLICK TO SELECT)</p>
                      {filteredFacilities.slice(0, 5).map((fac) => {
                        const isThisSelected = selectedFacility && (selectedFacility.facility_id === fac.facility_id)
                        return (
                          <div 
                            key={fac.facility_id || fac.id || fac.name} 
                            style={{
                              padding: "10px", 
                              borderBottom: "1px solid rgba(255,255,255,0.05)",
                              background: isThisSelected ? "rgba(14,165,233,0.12)" : "transparent",
                              borderRadius: "6px",
                              cursor: "pointer",
                              transition: "background 0.2s"
                            }}
                            onClick={() => handleFacilitySelect(fac)}
                          >
                            <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
                              <span style={{color: "white", fontWeight: "600", fontSize: "13px"}}>
                                {fac.facility_type === 'HOSPITAL' ? '🏥 ' : '🏠 '}
                                {fac.name}
                              </span>
                              <span style={{color: "var(--text-highlight)", fontSize: "12px", fontWeight: "bold"}}>
                                {fac.distance_km != null ? `${fac.distance_km.toFixed(2)} km` : ''}
                              </span>
                            </div>
                            <div style={{display: "flex", gap: "8px", marginTop: "4px", fontSize: "11px"}}>
                              <span style={{color: fac.facility_type === 'HOSPITAL' ? '#c084fc' : '#34d399'}}>
                                {fac.facility_type}
                              </span>
                              <span style={{color: 'var(--warning)'}}>
                                {fac.data_status || 'PUBLIC_UNVERIFIED'}
                              </span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </>
              ) : (
                <p className="muted">No facility available for selection.</p>
              )}
            </article>
            
            {/* System Limitations Disclaimer */}
            <article className="info-card">
              <p className="card-label">DATA INTEGRITY & SAFETY BOUNDARIES</p>
              <ul style={{margin: 0, paddingLeft: "16px", color: "var(--text-muted)", fontSize: "0.85em", lineHeight: "1.5"}}>
                <li style={{marginBottom: "4px"}}>Facility listings are sourced from public municipal directories and are marked <strong>PUBLIC_UNVERIFIED</strong>.</li>
                <li style={{marginBottom: "4px"}}>Hospital beds, triage readiness, and shelter capacities are <strong>never fabricated</strong> when unverified.</li>
                <li style={{marginBottom: "4px"}}>Routing safely excludes known blocked road segments, but unmonitored road segments are not guaranteed clear.</li>
                <li style={{marginBottom: "4px"}}>Simulated conditions are explicitly labeled <strong>[DEMO]</strong>.</li>
                <li>Official flood management and emergency authorities remain the final source of truth.</li>
              </ul>
            </article>
          </aside>
        </section>
      )}

      <footer>Updated {weather?.timestamp ? new Date(weather.timestamp).toLocaleTimeString() : 'not yet'} · Decision-support prototype. Official emergency authorities remain the source of truth.</footer>
    </main>
  )
}

export default App
