import { useEffect, useMemo, useState } from 'react'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

function App() {
  const [apiStatus, setApiStatus] = useState('Checking API...')
  const [location, setLocation] = useState({ latitude: 17.385, longitude: 78.486 })
  const [locationStatus, setLocationStatus] = useState('Demo location active')
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
      loadDashboard(location)
      return
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const currentLocation = { latitude: position.coords.latitude, longitude: position.coords.longitude }
        setLocation(currentLocation)
        setLocationStatus('Browser location active')
        loadDashboard(currentLocation)
      },
      () => {
        setLocationStatus('Permission denied - demo location active')
        loadDashboard(location)
      },
      { enableHighAccuracy: true, timeout: 8000 },
    )
  }, [])

  const riskSummary = useMemo(() => {
    if (!riskMap) return { high: 0, medium: 0, low: 0 }
    return riskMap.zones.reduce((summary, zone) => ({ ...summary, [zone.risk_level.toLowerCase()]: summary[zone.risk_level.toLowerCase()] + 1 }), { high: 0, medium: 0, low: 0 })
  }, [riskMap])

  const mapStyle = (polygon) => {
    if (!riskMap) return {}
    const [south, west, north, east] = riskMap.bounds
    const points = polygon.map(([longitude, latitude]) => `${((longitude - west) / (east - west)) * 100}% ${100 - ((latitude - south) / (north - south)) * 100}%`).join(', ')
    return { clipPath: `polygon(${points})` }
  }

  const markerStyle = (latitude, longitude) => {
    if (!riskMap) return {}
    const [south, west, north, east] = riskMap.bounds
    return { left: `${((longitude - west) / (east - west)) * 100}%`, top: `${100 - ((latitude - south) / (north - south)) * 100}%` }
  }

  const navigate = async () => {
    try {
      setError('')
      const data = await request('/evacuation-route', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_latitude: location.latitude, user_longitude: location.longitude }) })
      setRoute(data)
    } catch (routeError) {
      setError(routeError.message)
    }
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
          <div className="map-grid" />
          <div className="zone-layer">
            {riskMap?.zones.map((zone) => <div key={zone.id} className={`risk-zone ${zone.risk_level.toLowerCase()}`} style={mapStyle(zone.polygon)} title={`${zone.risk_level} risk: ${zone.flood_probability}`} />)}
            <div className="user-marker" style={markerStyle(location.latitude, location.longitude)}>YOU</div>
            {recommendation?.recommendation && <div className="shelter-marker" style={markerStyle(recommendation.recommendation.shelter.latitude, recommendation.recommendation.shelter.longitude)} title={recommendation.recommendation.shelter.name}>SHELTER</div>}
            {route && <div className="route-line" />}
          </div>
          {loading && <div className="map-copy"><span className="map-pin">...</span><h2>Loading situation</h2><p>Collecting current weather and risk data.</p></div>}
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
            <p className="card-label">CURRENT RISK</p>
            <div className="metric-row"><strong>{riskSummary.high ? 'HIGH' : riskSummary.medium ? 'MEDIUM' : 'LOW'}</strong><span className="neutral-badge">{riskSummary.high} HIGH ZONES</span></div>
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
            <button type="button" onClick={() => loadDashboard(location)}>Refresh</button>
          </article>
        </aside>
      </section>}

      <footer>Updated {weather?.timestamp ? new Date(weather.timestamp).toLocaleTimeString() : 'not yet'} · Decision-support prototype. Official emergency authorities remain the source of truth.</footer>
    </main>
  )
}

export default App
