import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, Polygon, Polyline, Popup, TileLayer, ZoomControl } from 'react-leaflet'
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

function RiskMap({ riskData, location, recommendedShelter, route, loading }) {
  const center = [(17.2 + 17.6) / 2, (78.2 + 78.7) / 2]
  const routePositions = route?.geometry?.map(([longitude, latitude]) => [latitude, longitude]) ?? []

  return (
    <MapContainer className="leaflet-map" center={center} zoom={11} scrollWheelZoom zoomControl={false}>
      <ZoomControl position="topright" />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      
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

      <CircleMarker center={[location.latitude, location.longitude]} pathOptions={{ color: '#0ea5e9', fillColor: '#0ea5e9', fillOpacity: 1, weight: 3 }} radius={7}>
        <Popup>Your live location</Popup>
      </CircleMarker>
      
      {recommendedShelter && (
        <CircleMarker
          center={[recommendedShelter.latitude, recommendedShelter.longitude]}
          pathOptions={{ color: '#10b981', fillColor: '#10b981', fillOpacity: 1, weight: 3 }}
          radius={7}
        >
          <Popup>{recommendedShelter.name} ({recommendedShelter.data_status || 'PUBLIC_UNVERIFIED'})</Popup>
        </CircleMarker>
      )}
      {routePositions.length > 1 && <Polyline positions={routePositions} pathOptions={{ color: '#38bdf8', weight: 4, opacity: 0.8 }} />}
      {loading && <div className="leaflet-loading" aria-label="Loading map data">Loading map data...</div>}
    </MapContainer>
  )
}

function App() {
  const [apiStatus, setApiStatus] = useState('Checking API...')
  const [location, setLocation] = useState(hyderabadLocation)
  const [locationStatus, setLocationStatus] = useState('Hyderabad center location')
  const [weather, setWeather] = useState(null)
  const [riskData, setRiskData] = useState(null)
  const [recommendationResponse, setRecommendationResponse] = useState(null)
  const [route, setRoute] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [shelters, setShelters] = useState([])
  const [roads, setRoads] = useState([])
  const [gauges, setGauges] = useState([])
  const [hydrology, setHydrology] = useState(null)
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
      const [health, weatherData, riskRes, shelterRes, alertData, shelterList, roadList, gaugeList, hydroData] = await Promise.all([
        request('/health').catch(() => ({})),
        request(`/weather?${query}`).catch(() => null),
        request(`/risk-map?${query}`).catch(() => null),
        request(`/shelters/recommended?${recQuery}`).catch(() => null),
        request('/disaster-alerts').catch(() => []),
        request('/shelters').catch(() => ({ shelters: [] })),
        request('/road-conditions').catch(() => []),
        request('/gauges').catch(() => []),
        request(`/hydrology/water-level?${query}`).catch(() => null)
      ])
      
      setApiStatus(health?.demo_mode ? 'API online - demo mode' : 'API online')
      setWeather(weatherData)
      setRiskData(riskRes)
      setRecommendationResponse(shelterRes)
      setAlerts(alertData || [])
      setShelters(shelterList?.shelters || [])
      setRoads(roadList || [])
      setGauges(gaugeList || [])
      setHydrology(hydroData)
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

  const navigateAction = async () => {
    if (!recommendationResponse?.recommendations?.[0]) return
    try {
      setError('')
      const dest = recommendationResponse.recommendations[0]
      const data = await request('/evacuation-route', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ 
          origin: { latitude: location.latitude, longitude: location.longitude },
          destination: { latitude: dest.latitude, longitude: dest.longitude } 
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

  const openShelters = shelters.filter((shelter) => shelter.operational_status === 'OPEN')
  const blockedRoads = roads.filter((road) => road.status !== 'OPEN')

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">FLOOD RESPONSE SYSTEM</p>
          <h1>Disaster Management</h1>
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
          {riskData?.coverage_status === 'MODEL_UNSUPPORTED' ? (
            <>
              <strong>FLOOD PREDICTION UNAVAILABLE</strong>
              <p>The selected location is outside the current INDOFLOODS model coverage.</p>
            </>
          ) : (
            <>
              <strong>DEMO HYDROLOGY DATA</strong>
              <p>Water-level information is currently simulated for demonstration purposes. Follow official disaster-management instructions for real emergencies.</p>
            </>
          )}
        </div>
      </section>

      {error && <div className="error-banner" role="alert">{error}</div>}

      {view === 'operations' ? (
        <OperationsDashboard 
          apiStatus={apiStatus}
          weather={weather}
          riskData={riskData}
          shelters={shelters}
          roads={roads}
          location={location}
          route={route}
          gauges={gauges}
          hydrology={hydrology}
          alerts={alerts}
          onLocationSelect={handleLocationSelect}
        />
      ) : <section className="workspace-grid">
        <div className="map-panel" aria-label="Flood risk map">
          <RiskMap 
            riskData={riskData} 
            location={location} 
            recommendedShelter={recommendationResponse?.recommendations?.[0]} 
            route={route} 
            loading={loading} 
          />
          {!loading && !riskData && <div className="map-copy"><span className="map-pin">!</span><h2>Map data unavailable</h2><p>Start the FastAPI backend to load the risk map.</p></div>}
          <div className="map-legend">
            <span><i className="legend-dot user" />Your location</span>
            <span><i className="legend-dot safe" style={{backgroundColor: '#10b981'}} />Shelter</span>
            <span><i className="legend-dot route" style={{backgroundColor: '#38bdf8'}} />OSM road-network route</span>
            <span><i className="legend-dot unknown" style={{backgroundColor: '#94a3b8'}} />Prediction unavailable</span>
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

          {/* Flood Prediction Status Card */}
          <article className="info-card">
            <p className="card-label">FLOOD PREDICTION STATUS</p>
            {riskData ? (
              <>
                <div className="metric-row">
                  <strong>{riskData.prediction_available ? 'Flood prediction available' : 'Flood prediction unavailable'}</strong>
                  <span className="neutral-badge">{riskData.coverage_status}</span>
                </div>
                {riskData.prediction_available ? (
                  <>
                    <p className="muted" style={{marginTop: "8px", color: "white"}}>Risk level: {riskData.risk_level}</p>
                    {riskData.probability !== undefined && riskData.probability !== null && (
                      <p className="muted">Model severe-flood probability: {(riskData.probability * 100).toFixed(1)}%</p>
                    )}
                    <p className="muted">Model: INDOFLOODS flood severity model</p>
                  </>
                ) : (
                  <p className="muted" style={{marginTop: "8px"}}>The selected location is outside the current INDOFLOODS model coverage.</p>
                )}
                
                <div style={{marginTop: "16px", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "12px"}}>
                  <p className="muted">
                    {weather?.condition ?? 'Weather data unavailable'} · {
                      !weather ? 'Loading rainfall data...' : 
                      (weather.rainfall == null ? 'Rainfall data unavailable' : `Historical/reanalysis rainfall: ${weather.rainfall} mm`)
                    }
                  </p>
                </div>
              </>
            ) : (
              <p className="muted">Waiting for risk-zone data.</p>
            )}
          </article>
          
          {/* Recommended Shelter Card */}
          <article className="info-card">
            <p className="card-label">RECOMMENDED SHELTER</p>
            {recommendationResponse?.recommendations?.length > 0 ? (
              <>
                <strong>{recommendationResponse.recommendations[0].name}</strong>
                <p className="muted">
                   {recommendationResponse.recommendations[0].distance_km?.toFixed(2) ?? '?'} km · Capacity: {recommendationResponse.recommendations[0].capacity ?? 'Unknown'}
                </p>
                <p className="muted">
                   Operational status: {recommendationResponse.recommendations[0].operational_status || 'Unknown'}
                </p>
                <div className="route-note" style={{fontSize: "0.85em", color: "var(--warning)", borderColor: "var(--warning)", textAlign: "left", marginTop: "12px"}}>
                  <strong style={{fontSize: "1em", margin: "0 0 4px 0", color: "var(--warning)"}}>PUBLIC_UNVERIFIED</strong>
                  <span style={{color: "var(--text-main)", display: "block", marginTop: "4px"}}>Safety not verified. Not confirmed as an emergency flood shelter.</span>
                </div>
                
                <button className="primary-button" type="button" onClick={navigateAction}>Find OSM Road-Network Route</button>
                
                {route && (
                  <div style={{marginTop: "16px", padding: "12px", background: "rgba(14,165,233,0.05)", borderRadius: "8px", border: "1px solid rgba(14,165,233,0.2)"}}>
                    <strong style={{fontSize: "1.1rem", display: "block", marginBottom: "8px"}}>Shortest available road-network route</strong>
                    <p className="muted" style={{margin: "4px 0"}}>Route distance: {route.route_distance_km?.toFixed(2) ?? '?'} km</p>
                    <p className="muted" style={{margin: "4px 0"}}>Estimated duration: {route.estimated_duration_min ? `${route.estimated_duration_min} minutes` : 'Travel time unavailable'}</p>
                    <p className="muted" style={{margin: "4px 0"}}>Road source: OpenStreetMap</p>
                    <p className="muted" style={{margin: "4px 0"}}>Road condition: {route.road_condition_status || 'UNKNOWN'}</p>
                    <p style={{fontSize: "0.85em", color: "var(--warning)", margin: "8px 0 0 0"}}>Live traffic and temporary road closures are not currently integrated.</p>
                  </div>
                )}
                
                {recommendationResponse.recommendations.length > 1 && (
                  <div style={{marginTop: "20px"}}>
                    <p className="card-label">OTHER RECOMMENDED SHELTERS</p>
                    {recommendationResponse.recommendations.slice(1).map((s, idx) => (
                      <div key={idx} style={{padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.05)"}}>
                        <div style={{display: "flex", justifyContent: "space-between"}}>
                          <span style={{color: "white", fontWeight: "600"}}>{s.name}</span>
                          <span style={{color: "var(--text-muted)", fontSize: "0.9em"}}>{s.distance_km?.toFixed(2)} km</span>
                        </div>
                        <div style={{fontSize: "0.8em", color: "var(--warning)", marginTop: "2px"}}>{s.data_status || 'PUBLIC_UNVERIFIED'}</div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <p className="muted">{recommendationResponse?.limitations?.[0] ?? 'No shelter found.'}</p>
            )}
          </article>
          
          {/* Limitations Disclaimer */}
          <article className="info-card">
            <p className="card-label">IMPORTANT LIMITATIONS</p>
            <ul style={{margin: 0, paddingLeft: "16px", color: "var(--text-muted)", fontSize: "0.85em", lineHeight: "1.5"}}>
              <li style={{marginBottom: "4px"}}>Flood prediction is only available within the current INDOFLOODS geographic coverage.</li>
              <li style={{marginBottom: "4px"}}>Shelter records are currently PUBLIC_UNVERIFIED.</li>
              <li style={{marginBottom: "4px"}}>Road routing uses the local OpenStreetMap road network.</li>
              <li style={{marginBottom: "4px"}}>Live traffic and temporary road closures are not integrated.</li>
              <li style={{marginBottom: "4px"}}>Hydrology information is currently demonstration data.</li>
              <li style={{marginBottom: "4px"}}>Routes are not guaranteed flood-safe.</li>
              <li>Follow official emergency instructions during real disasters.</li>
            </ul>
          </article>
        </aside>
      </section>}

      <footer>Updated {weather?.timestamp ? new Date(weather.timestamp).toLocaleTimeString() : 'not yet'} · Decision-support prototype. Official emergency authorities remain the source of truth.</footer>
    </main>
  )
}

export default App
