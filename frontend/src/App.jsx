import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, Polygon, Polyline, Popup, TileLayer, ZoomControl } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

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
      const [health, weatherData, riskRes, shelterRes, alertData, shelterList, roadList] = await Promise.all([
        request('/health').catch(() => ({})),
        request(`/weather?${query}`).catch(() => null),
        request(`/risk-map?${query}`).catch(() => null),
        request(`/shelters/recommended?${recQuery}`).catch(() => null),
        request('/disaster-alerts').catch(() => []),
        request('/shelters').catch(() => ({ shelters: [] })),
        request('/road-conditions').catch(() => [])
      ])
      
      setApiStatus(health?.demo_mode ? 'API online - demo mode' : 'API online')
      setWeather(weatherData)
      setRiskData(riskRes)
      setRecommendationResponse(shelterRes)
      setAlerts(alertData || [])
      setShelters(shelterList?.shelters || [])
      setRoads(roadList || [])
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

      {alerts.length > 0 && (
        <section className="alert-banner" aria-label="Current system state">
          <span className="alert-mark">!</span>
          <div>
            <strong>{alerts[0]?.severity ?? 'FLOOD'} FLOOD ALERT</strong>
            <p>{alerts[0]?.description ?? 'Loading current disaster information...'}</p>
          </div>
          <span className="demo-label">{alerts[0]?.source ?? 'LOADING'}</span>
        </section>
      )}

      {error && <div className="error-banner" role="alert">{error}</div>}

      {view === 'operations' ? (
        <section className="operations-view">
          <div className="operations-heading">
            <div>
              <p className="eyebrow">RESPONSE OPERATIONS</p>
              <h2>Situation overview</h2>
            </div>
            {alerts.length > 0 && <span className="demo-label">{alerts[0]?.source ?? 'LOADING'}</span>}
          </div>
          <div className="operations-metrics">
            <article className="metric-card"><span>Active alerts</span><strong>{alerts.length}</strong><small>Latest reports</small></article>
            <article className="metric-card"><span>Tracked shelters</span><strong>{shelters.length}</strong><small>Total locations in DB</small></article>
            <article className="metric-card warning"><span>Monitored roads</span><strong>{roads.length}</strong><small>Condition reports</small></article>
          </div>
          <div className="operations-grid">
            <article className="operations-panel">
              <div className="panel-heading"><h3>Shelter status</h3><span>{shelters.length} total</span></div>
              {shelters.map((shelter) => (
                <div className="resource-row" key={shelter.shelter_id || shelter.id || shelter.name}>
                  <div>
                    <strong>{shelter.name}</strong>
                    <small>Status: {shelter.data_status || 'PUBLIC_UNVERIFIED'}</small>
                  </div>
                  <span className={`resource-status`}>{shelter.operational_status || 'UNKNOWN'}</span>
                  <b>Cap: {shelter.capacity || '?'}</b>
                </div>
              ))}
            </article>
            <article className="operations-panel">
              <div className="panel-heading"><h3>Road conditions</h3><span>{roads.length} monitored</span></div>
              {roads.map((road) => (
                <div className="resource-row" key={road.id}>
                  <div>
                    <strong>{road.road_name}</strong>
                    <small>{road.notes ?? 'No notes recorded'}</small>
                  </div>
                  <span className={`resource-status ${road.status?.toLowerCase() || ''}`}>{road.status || 'UNKNOWN'}</span>
                </div>
              ))}
            </article>
          </div>
        </section>
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
            <span><i className="legend-dot high" />High risk</span>
            <span><i className="legend-dot medium" />Medium risk</span>
            <span><i className="legend-dot safe" />Low risk</span>
            <span><i className="legend-dot user" />You</span>
          </div>
        </div>

        <aside className="side-panel">
          <article className="info-card">
            <p className="card-label">YOUR LOCATION RISK</p>
            {riskData ? (
              <>
                <div className="metric-row">
                  <strong>{riskData.prediction_available ? riskData.risk_level : 'UNKNOWN'}</strong>
                  <span className="neutral-badge">{riskData.coverage_status}</span>
                </div>
                {!riskData.prediction_available && (
                  <p className="muted" style={{marginTop: "5px"}}>Flood prediction unavailable.</p>
                )}
                <p className="muted">{weather?.condition ?? 'Weather loading'} · {weather ? `${weather.rainfall} mm rain` : 'Awaiting weather'}</p>
              </>
            ) : (
              <p className="muted">Waiting for risk-zone data.</p>
            )}
          </article>
          
          <article className="info-card">
            <p className="card-label">RECOMMENDED SHELTER</p>
            {recommendationResponse?.recommendations?.length > 0 ? (
              <>
                <strong>{recommendationResponse.recommendations[0].name}</strong>
                <p className="muted">
                   {recommendationResponse.recommendations[0].distance_km?.toFixed(2) ?? '?'} km · Capacity: {recommendationResponse.recommendations[0].capacity ?? 'Unknown'}
                </p>
                <p className="route-note" style={{fontSize: "0.8em", color: "var(--warning)", borderColor: "var(--warning)"}}>Status: {recommendationResponse.recommendations[0].data_status || 'PUBLIC_UNVERIFIED'}</p>
                <button className="primary-button" type="button" onClick={navigateAction}>Find OSM road-network route</button>
              </>
            ) : (
              <p className="muted">{recommendationResponse?.limitations?.[0] ?? 'No shelter found.'}</p>
            )}
            
            {route && (
              <p className="route-note">
                Shortest available road-network route: <br/>
                {route.route_distance_km?.toFixed(2) ?? '?'} km · {route.estimated_duration_min ? `${route.estimated_duration_min} min` : 'Travel time unavailable'}
                <br />
                <span style={{fontSize: "0.85em", color: "var(--text-muted)", display: "block", marginTop: "4px"}}>Road Condition Status: {route.road_condition_status || 'UNKNOWN'}</span>
              </p>
            )}
          </article>
          
          <article className="info-card location-card">
            <div>
              <p className="card-label">YOUR LOCATION</p>
              <strong>{locationStatus}</strong>
              <p className="muted">{location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}</p>
            </div>
            <button type="button" onClick={refreshDashboard} disabled={loading}>{loading ? 'Refreshing...' : 'Refresh'}</button>
          </article>
        </aside>
      </section>}

      <footer>Updated {weather?.timestamp ? new Date(weather.timestamp).toLocaleTimeString() : 'not yet'} · Decision-support prototype. Official emergency authorities remain the source of truth.</footer>
    </main>
  )
}

export default App
