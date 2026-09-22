import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, Polygon, Polyline, Popup, TileLayer, ZoomControl } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const hyderabadLocation = { latitude: 17.385, longitude: 78.486 }
const isInHyderabad = ({ latitude, longitude }) => latitude >= 17.2 && latitude <= 17.6 && longitude >= 78.2 && longitude <= 78.7

const riskColors = {
  HIGH: '#c95243',
  MEDIUM: '#e3a138',
  LOW: '#3b9674',
}

function pointIsInsidePolygon(latitude, longitude, polygon) {
  let inside = false
  for (let index = 0, previous = polygon.length - 1; index < polygon.length; previous = index++) {
    const [currentLongitude, currentLatitude] = polygon[index]
    const [previousLongitude, previousLatitude] = polygon[previous]
    const intersects = ((currentLatitude > latitude) !== (previousLatitude > latitude))
      && longitude < ((previousLongitude - currentLongitude) * (latitude - currentLatitude)) / (previousLatitude - currentLatitude) + currentLongitude
    if (intersects) inside = !inside
  }
  return inside
}

function RiskMap({ riskMap, location, recommendation, route, loading }) {
  const bounds = riskMap?.bounds ?? [17.2, 78.2, 17.6, 78.7]
  const center = [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2]
  const routePositions = route?.geometry?.map(([longitude, latitude]) => [latitude, longitude]) ?? []

  return (
    <MapContainer className="leaflet-map" center={center} zoom={11} scrollWheelZoom zoomControl={false}>
      <ZoomControl position="topright" />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {riskMap?.zones.map((zone) => {
        const color = riskColors[zone.risk_level]
        return (
          <Polygon
            key={zone.id}
            positions={zone.polygon.map(([longitude, latitude]) => [latitude, longitude])}
            pathOptions={{ color, fillColor: color, fillOpacity: 0.4, weight: 1 }}
          >
            <Popup>{zone.risk_level} risk · {(zone.flood_probability * 100).toFixed(0)}% probability</Popup>
          </Polygon>
        )
      })}
      <CircleMarker center={[location.latitude, location.longitude]} pathOptions={{ color: '#1f5d9a', fillColor: '#1f5d9a', fillOpacity: 1 }} radius={8}>
        <Popup>Your live location</Popup>
      </CircleMarker>
      {recommendation?.recommendation && (
        <CircleMarker
          center={[recommendation.recommendation.shelter.latitude, recommendation.recommendation.shelter.longitude]}
          pathOptions={{ color: '#2e7661', fillColor: '#2e7661', fillOpacity: 1 }}
          radius={8}
        >
          <Popup>{recommendation.recommendation.shelter.name}</Popup>
        </CircleMarker>
      )}
      {routePositions.length > 1 && <Polyline positions={routePositions} pathOptions={{ color: '#216e9e', weight: 5 }} />}
      {loading && <div className="leaflet-loading" aria-label="Loading map data">Loading map data...</div>}
    </MapContainer>
  )
}

function App() {
  const [apiStatus, setApiStatus] = useState('Checking API...')
  const [location, setLocation] = useState(hyderabadLocation)
  const [locationStatus, setLocationStatus] = useState('Hyderabad center location')
  const [weather, setWeather] = useState(null)
  const [riskMap, setRiskMap] = useState(null)
  const [recommendation, setRecommendation] = useState(null)
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
    try {
      const [health, weatherData, riskData, shelterData, alertData, shelterList, roadList] = await Promise.all([
        request('/health'),
        request(`/weather?${query}`),
        request('/risk-map'),
        request(`/shelters/recommended?${query}`),
        request('/disaster-alerts'),
        request('/shelters'),
        request('/road-conditions'),
      ])
      setApiStatus(health.demo_mode ? 'API online - demo mode' : 'API online')
      setWeather(weatherData)
      setRiskMap(riskData)
      setRecommendation(shelterData)
      setAlerts(alertData)
      setShelters(shelterList)
      setRoads(roadList)
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

  const riskSummary = useMemo(() => {
    if (!riskMap) return { high: 0, medium: 0, low: 0 }
    return riskMap.zones.reduce((summary, zone) => ({ ...summary, [zone.risk_level.toLowerCase()]: summary[zone.risk_level.toLowerCase()] + 1 }), { high: 0, medium: 0, low: 0 })
  }, [riskMap])

  const currentRiskZone = useMemo(() => {
    if (!riskMap) return null
    return riskMap.zones.find((zone) => pointIsInsidePolygon(location.latitude, location.longitude, zone.polygon)) ?? null
  }, [location, riskMap])

  const navigate = async () => {
    try {
      setError('')
      const data = await request('/evacuation-route', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_latitude: location.latitude, user_longitude: location.longitude }) })
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

  const openShelters = shelters.filter((shelter) => shelter.status === 'OPEN')
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
          <strong>{alerts[0]?.severity ?? 'FLOOD'} FLOOD ALERT</strong>
          <p>{alerts[0]?.description ?? 'Loading current disaster information...'}</p>
        </div>
        <span className="demo-label">{alerts[0]?.source ?? 'LOADING'}</span>
      </section>

      {error && <div className="error-banner" role="alert">{error}</div>}

      {view === 'operations' ? (
        <section className="operations-view">
          <div className="operations-heading">
            <div>
              <p className="eyebrow">RESPONSE OPERATIONS</p>
              <h2>Situation overview</h2>
            </div>
            <span className="demo-label">{alerts[0]?.source ?? 'LOADING'}</span>
          </div>
          <div className="operations-metrics">
            <article className="metric-card"><span>Active alerts</span><strong>{alerts.length}</strong><small>Latest reports</small></article>
            <article className="metric-card"><span>Open shelters</span><strong>{openShelters.length}</strong><small>{shelters.length} locations tracked</small></article>
            <article className="metric-card warning"><span>Roads requiring action</span><strong>{blockedRoads.length}</strong><small>Closed or flooded</small></article>
            <article className="metric-card"><span>Available capacity</span><strong>{openShelters.reduce((total, shelter) => total + shelter.available_capacity, 0)}</strong><small>Across open shelters</small></article>
          </div>
          <div className="operations-grid">
            <article className="operations-panel">
              <div className="panel-heading"><h3>Shelter status</h3><span>{shelters.length} total</span></div>
              {shelters.map((shelter) => <div className="resource-row" key={shelter.id}><div><strong>{shelter.name}</strong><small>{shelter.risk_level} risk · {shelter.accessibility} access</small></div><span className={`resource-status ${shelter.status.toLowerCase()}`}>{shelter.status}</span><b>{shelter.available_capacity}/{shelter.capacity}</b></div>)}
            </article>
            <article className="operations-panel">
              <div className="panel-heading"><h3>Road conditions</h3><span>{roads.length} monitored</span></div>
              {roads.map((road) => <div className="resource-row" key={road.id}><div><strong>{road.road_name}</strong><small>{road.notes ?? 'No notes recorded'}</small></div><span className={`resource-status ${road.status.toLowerCase()}`}>{road.status}</span></div>)}
            </article>
          </div>
        </section>
      ) : <section className="workspace-grid">
        <div className="map-panel" aria-label="Flood risk map">
          <RiskMap riskMap={riskMap} location={location} recommendation={recommendation} route={route} loading={loading} />
          {!loading && !riskMap && <div className="map-copy"><span className="map-pin">!</span><h2>Map data unavailable</h2><p>Start the FastAPI backend to load the risk map.</p></div>}
          <div className="map-legend">
            <span><i className="legend-dot high" />High risk</span>
            <span><i className="legend-dot medium" />Medium risk</span>
            <span><i className="legend-dot safe" />Safe zone</span>
            <span><i className="legend-dot user" />You</span>
          </div>
        </div>

        <aside className="side-panel">
          <article className="info-card">
            <p className="card-label">YOUR LOCATION RISK</p>
            <div className="metric-row"><strong>{currentRiskZone?.risk_level ?? 'UNKNOWN'}</strong><span className="neutral-badge">SIMULATED</span></div>
            <p className="muted">{currentRiskZone ? `${(currentRiskZone.flood_probability * 100).toFixed(0)}% simulated flood probability` : 'Waiting for risk-zone data.'}</p>
            <p className="muted">{weather?.condition ?? 'Weather loading'} · {weather ? `${weather.rainfall} mm rain` : 'Awaiting weather'}</p>
          </article>
          <article className="info-card">
            <p className="card-label">RECOMMENDED SHELTER</p>
            <strong>{recommendation?.recommendation?.shelter.name ?? 'No safe shelter found'}</strong>
            <p className="muted">{recommendation?.recommendation ? `${recommendation.recommendation.safety_score}/100 safety · ${recommendation.recommendation.distance_km} km · ${recommendation.recommendation.shelter.available_capacity} spaces` : recommendation?.warning ?? 'Waiting for shelter data.'}</p>
            {recommendation?.recommendation && <button className="primary-button" type="button" onClick={navigate}>Navigate to safety</button>}
            {route && <p className="route-note">Route: {route.distance_km} km · {route.duration_minutes} min · {route.route_risk} risk</p>}
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
