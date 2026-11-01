import React, { useState } from 'react'
import RiskMap from '../RiskMap'

export default function OverviewTab({
  riskData,
  location,
  facilities,
  selectedFacility,
  onFacilitySelect,
  roads,
  route,
  floodHazards,
  loading,
  weather,
  hydrology,
  alerts,
  hazardWarning,
  onCalculateRoute,
  onOpenNavigation,
  isRouting,
  onLocationSelect,
  onMyLocation,
  onNavigateToTab,
  isSevereWeather = false,
  isDemoMode = false,
  dashboardStatus = {},
  t = {},
  incidents = []
}) {
  const [searchQuery, setSearchQuery] = useState('')
  const [gpsLoading, setGpsLoading] = useState(false)
  const [activeLayers, setActiveLayers] = useState({
    risk: true,
    shelters: true,
    hospitals: true,
    roads: true,
    route: true,
    incidents: true
  })
  const [tileMode, setTileMode] = useState('street')

  const toggleLayer = (layerKey) => {
    setActiveLayers(prev => ({ ...prev, [layerKey]: !prev[layerKey] }))
  }

  const isDetour = route?.is_rerouted || route?.road_condition_status === 'HAZARDS_AVOIDED'
  const isNoSafeRoute = route?.route_status === 'NO_SAFE_ROUTE'

  const nearestFacility = selectedFacility || (facilities && facilities.length > 0 ? facilities[0] : null)
  const statusOf = (name) => dashboardStatus[name] || (loading ? 'loading' : 'unavailable')
  const isAvailable = (name) => statusOf(name) === 'available'
  const statusLabel = (name) => ({
    loading: 'Loading',
    available: 'Available',
    unavailable: 'Unavailable',
    refreshing: 'Refreshing'
  }[statusOf(name)] || 'Degraded')
  const unavailableValue = (name) => statusOf(name) === 'loading' ? 'Loading…' : 'Unavailable'

  // The severe toggle is an explicit demo action; provider values are shown only when available.
  const currentTemp = isSevereWeather ? '24.2' : (weather?.temperature != null ? weather.temperature.toFixed(1) : unavailableValue('weather'))
  const currentRain = isSevereWeather ? '68.5' : (weather?.rainfall != null ? weather.rainfall.toFixed(1) : unavailableValue('weather'))
  const currentHumidity = isSevereWeather ? '96' : (weather?.humidity != null ? `${weather.humidity}` : unavailableValue('weather'))
  const currentWind = isSevereWeather ? '42.5' : (weather?.wind_speed != null ? weather.wind_speed.toFixed(1) : unavailableValue('weather'))
  const currentCondition = isSevereWeather ? 'Heavy Monsoon Deluge' : (weather?.description || unavailableValue('weather'))
  const musiWaterLevel = isSevereWeather
    ? '4.92m (High Hazard Warning)'
    : (hydrology?.water_level != null ? `${hydrology.water_level}m` : unavailableValue('hydrology'))
  const hazardStatus = statusOf('locationWarning')
  const hazardUnavailable = hazardStatus !== 'available'
  const hazardHeadline = isSevereWeather
    ? 'SEVERE MONSOON FLOODING ALERT — Greater Hyderabad Municipal Region'
    : hazardUnavailable
      ? 'FLOOD HAZARD STATUS UNAVAILABLE — Greater Hyderabad Municipal Region'
      : hazardWarning?.is_in_hazard_zone
        ? `FLOOD HAZARD INTERSECTION DETECTED (${hazardWarning.hazard_count} ZONES) — Greater Hyderabad Municipal Region`
        : 'NO CONFIRMED FLOOD HAZARD REPORTED AT THIS LOCATION'
  const hazardDescription = isSevereWeather
    ? 'Simulated severe flood conditions active: Musi river catchment experiencing heavy runoff. Low-lying arterial roads inundated. Stay indoors and heed disaster advisories.'
    : hazardUnavailable
      ? `${statusLabel('locationWarning')}: the location hazard service did not return a result. Absence of data does not indicate safety.`
      : hazardWarning?.is_in_hazard_zone
        ? `Current coordinates intersect designated flood polygons (${hazardWarning.intersected_hazards.map(h => h.title).join(', ')}). Seek elevated ground immediately.`
        : `${hazardWarning?.explanation || 'No confirmed flood hazard was returned for this location.'} Absence of an alert does not guarantee safety.`
  const globalFeedStatuses = ['shelters', 'alerts', 'roads', 'gauges', 'hazards', 'incidents']
    .map(name => dashboardStatus[name])
  const globalFeedsRefreshing = globalFeedStatuses.some(status => status === 'refreshing')
  const globalFeedsUnavailable = globalFeedStatuses.some(status => status === 'unavailable')

  const hyderabadPresets = [
    { name: 'Banjara Hills', lat: 17.4156, lon: 78.4350 },
    { name: 'Musi River (Chaderghat)', lat: 17.3789, lon: 78.4892 },
    { name: 'Secunderabad', lat: 17.4399, lon: 78.4983 },
    { name: 'Charminar', lat: 17.3616, lon: 78.4747 },
    { name: 'Hitec City', lat: 17.4474, lon: 78.3762 },
    { name: 'Khairatabad', lat: 17.4116, lon: 78.4593 }
  ]

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    const match = hyderabadPresets.find(p => p.name.toLowerCase().includes(searchQuery.toLowerCase().trim()))
    if (match) {
      onLocationSelect({ latitude: match.lat, longitude: match.lon })
    }
  }

  // "My Location" button: requests real GPS then zooms the map in
  const handleMyLocation = () => {
    if (onMyLocation) {
      // App-level handler: acquires GPS, updates dashboard, moves map
      onMyLocation()
      return
    }
    // Inline fallback if prop not provided
    if (!navigator.geolocation) {
      onLocationSelect({ latitude: 17.385, longitude: 78.4867 })
      return
    }
    setGpsLoading(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGpsLoading(false)
        const coords = { latitude: pos.coords.latitude, longitude: pos.coords.longitude }
        const inHyd = coords.latitude >= 17.2 && coords.latitude <= 17.6 && coords.longitude >= 78.2 && coords.longitude <= 78.7
        onLocationSelect(inHyd ? coords : { latitude: 17.385, longitude: 78.4867 })
      },
      () => {
        setGpsLoading(false)
        onLocationSelect({ latitude: 17.385, longitude: 78.4867 })
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
    )
  }

  return (
    <div className="tab-overview">
      {/* Top Flood Monitoring Status Banner (matching mini_project reference design) */}
      <section className={`command-status-banner ${isSevereWeather ? 'severe' : hazardUnavailable || !hazardWarning?.is_in_hazard_zone ? 'degraded' : 'danger'}`} aria-label="Regional Flood Status">
        <div className="banner-left-shield">
          <div className="banner-shield-icon" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
              <path d="M12 8v4"></path>
              <path d="M12 16h.01"></path>
            </svg>
          </div>
          <span className={`banner-status-badge ${isSevereWeather ? 'badge-severe' : hazardUnavailable || !hazardWarning?.is_in_hazard_zone ? 'badge-unknown' : 'badge-danger'}`}>
            {isSevereWeather ? 'HIGH HAZARD' : hazardUnavailable ? statusLabel('locationWarning').toUpperCase() : hazardWarning?.is_in_hazard_zone ? hazardWarning.highest_severity : 'NO CONFIRMED ALERT'}
          </span>
        </div>

        <div className="banner-center-text">
          <strong className="banner-main-title">
            {hazardHeadline}
          </strong>
          <p className="banner-sub-text">
            {hazardDescription}
          </p>
        </div>

        <div className="banner-right-meta">
          <span className="banner-system-tag">SafeMap AI Flood Early Warning System</span>
          <span className="banner-safeguard-note">🛡️ 50km Model Safeguard Active</span>
          {(globalFeedsRefreshing || globalFeedsUnavailable) && (
            <span className="banner-safeguard-note">
              {globalFeedsRefreshing ? 'Global feeds refreshing' : 'Global feed unavailable; retained data may be stale'}
            </span>
          )}
        </div>
      </section>

      {/* Main Workspace Grid (Left 63% Map, Right 37% Radar & Routing) */}
      <div className="overview-workspace-grid">
        {/* Left Column: Interactive Flood Map */}
        <div className="overview-map-col">
          <div className="map-viewport-card">
            {/* Floating Map Controls Top Bar */}
            <div className="map-floating-topbar">
              {/* Location Search Bar */}
              <form className="map-search-form" onSubmit={handleSearchSubmit}>
                <div className="search-input-wrapper">
                  <span className="search-icon" aria-hidden="true">🔍</span>
                  <input
                    type="text"
                    className="map-search-input"
                    placeholder={t.searchPlaceholder || "Search Hyderabad location (e.g. Banjara Hills, Musi River)..."}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    list="hyderabad-presets-list"
                  />
                  <datalist id="hyderabad-presets-list">
                    {hyderabadPresets.map(p => (
                      <option key={p.name} value={p.name} />
                    ))}
                  </datalist>
                </div>
              </form>

              {/* Quick Preset / GPS Buttons */}
              <div className="map-view-actions">
                <button
                  type="button"
                  className="map-action-pill-btn"
                  onClick={handleMyLocation}
                  disabled={gpsLoading}
                  title="Go to your current GPS location"
                >
                  <span aria-hidden="true">{gpsLoading ? '⏳' : '📍'}</span>{' '}
                  {gpsLoading ? 'Locating...' : (t.myLocation || 'My Location')}
                </button>
                <div className="map-mode-toggle">
                  <button 
                    type="button" 
                    className={`mode-toggle-btn ${tileMode === 'street' ? 'active' : ''}`}
                    onClick={() => setTileMode('street')}
                    title="OpenStreetMap Road View"
                  >
                    {t.streetMap || 'Street Map'}
                  </button>
                  <button 
                    type="button" 
                    className={`mode-toggle-btn ${tileMode === 'satellite' ? 'active' : ''}`}
                    onClick={() => setTileMode('satellite')}
                    title="Esri Satellite Imagery Overlay"
                  >
                    🛰️ {t.satelliteView || 'Satellite View'}
                  </button>
                </div>
              </div>
            </div>

            {/* Floating Layer Toggle Pills */}
            <div className="map-floating-layers-bar" aria-label="Map Layer Toggles">
              <span className="layers-bar-label">MAP LAYERS:</span>
              <button
                type="button"
                className={`layer-pill ${activeLayers.risk ? 'active risk' : ''}`}
                onClick={() => toggleLayer('risk')}
              >
                🛡️ {t.layerRisk || 'Risk Polygons'}
              </button>
              <button
                type="button"
                className={`layer-pill ${activeLayers.shelters ? 'active shelters' : ''}`}
                onClick={() => toggleLayer('shelters')}
              >
                🏕️ {t.layerShelters || 'Safe Shelters'}
              </button>
              <button
                type="button"
                className={`layer-pill ${activeLayers.hospitals ? 'active hospitals' : ''}`}
                onClick={() => toggleLayer('hospitals')}
              >
                🏥 {t.layerHospitals || 'Hospitals'}
              </button>
              <button
                type="button"
                className={`layer-pill ${activeLayers.roads ? 'active roads' : ''}`}
                onClick={() => toggleLayer('roads')}
              >
                🚗 {t.layerRoads || 'Road Conditions'}
              </button>
              <button
                type="button"
                className={`layer-pill ${activeLayers.route ? 'active route' : ''}`}
                onClick={() => toggleLayer('route')}
              >
                🏁 {t.layerRoute || 'Evac Route'}
              </button>
              <button
                type="button"
                className={`layer-pill ${activeLayers.incidents ? 'active incidents' : ''}`}
                onClick={() => toggleLayer('incidents')}
              >
                📢 {t.layerIncidents || 'Citizen Reports'}
              </button>
            </div>

            {/* Leaflet Map Canvas */}
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
              height="600px"
              activeLayers={activeLayers}
              tileMode={tileMode}
              showLayersControl={false}
              incidents={incidents}
            />

            {/* Bottom Quick Coordinates Inspector */}
            <div className="map-bottom-coords-bar">
              <span className="coords-tag">
                📍 INSPECTED: {location.latitude.toFixed(4)}° N, {location.longitude.toFixed(4)}° E
              </span>
              <span className="coords-hint">
                💡 Click anywhere on the map to inspect local flood hazards & recalculate route
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: Stacked Radar & Shelter Cards (matching reference layout) */}
        <div className="overview-sidebar-col">
          {/* Card 1: Atmospheric Radar */}
          <section className="card-panel radar-card-panel" aria-label="Hyderabad Atmospheric Radar">
            <div className="panel-header-row">
              <div className="header-title-wrap">
                <span className="panel-icon" aria-hidden="true">🌧️</span>
                <h2 className="panel-title-text">{t.radarTitle || 'HYDERABAD ATMOSPHERIC RADAR'}</h2>
              </div>
              <span className={`radar-status-badge ${isDemoMode ? 'badge-demo' : isSevereWeather ? 'badge-severe' : isAvailable('weather') ? 'badge-normal' : 'badge-unknown'}`}>
                {isDemoMode ? 'SIMULATED FLOOD [DEMO]' : isSevereWeather ? 'HEAVY FLOODING' : statusLabel('weather').toUpperCase()}
              </span>
            </div>

            <div className="radar-condition-line">
              <h3 className="condition-headline">
                {isDemoMode ? `${currentCondition} [DEMO SIMULATION]` : currentCondition}
              </h3>
            </div>

            {/* 2x2 Telemetry Grid */}
            <div className="radar-telemetry-grid">
              <div className="telemetry-tile">
                <div className="tile-label-row">
                  <span className="tile-icon" aria-hidden="true">🌡️</span>
                  <span className="tile-label">{t.temp || 'Temp'}</span>
                </div>
                <strong className="tile-value">{currentTemp}°C</strong>
              </div>

              <div className="telemetry-tile">
                <div className="tile-label-row">
                  <span className="tile-icon" aria-hidden="true">🌧️</span>
                  <span className="tile-label">{t.rainfall || 'Rainfall'}</span>
                </div>
                <strong className={`tile-value ${isSevereWeather ? 'danger-text' : ''}`}>
                  {currentRain} mm/h {isDemoMode ? '(DEMO)' : ''}
                </strong>
              </div>

              <div className="telemetry-tile">
                <div className="tile-label-row">
                  <span className="tile-icon" aria-hidden="true">💧</span>
                  <span className="tile-label">{t.humidity || 'Humidity'}</span>
                </div>
                <strong className="tile-value">{currentHumidity}%</strong>
              </div>

              <div className="telemetry-tile">
                <div className="tile-label-row">
                  <span className="tile-icon" aria-hidden="true">💨</span>
                  <span className="tile-label">{t.wind || 'Wind'}</span>
                </div>
                <strong className="tile-value">{currentWind} km/h</strong>
              </div>
            </div>

            {/* Musi River Gauge Bar */}
            <div className="radar-river-strip">
              <div className="river-info-row">
                <span className="river-icon" aria-hidden="true">🌊</span>
                <span className="river-name">{t.musiRiver || 'Musi River Telemetry'}:</span>
              </div>
              <strong className={`river-level ${isSevereWeather ? 'danger-text' : 'safe-text'}`}>
                {musiWaterLevel} {isDemoMode ? '[DEMO]' : ''} {!isSevereWeather && !isAvailable('hydrology') ? `(${statusLabel('hydrology')})` : ''}
              </strong>
            </div>
          </section>

          {/* Card 2: Recommended Safe Shelter & Routing Console */}
          <section className="card-panel shelter-card-panel" aria-label="Recommended Shelter Candidate">
            <div className="panel-header-row">
              <div className="header-title-wrap">
                <span className="panel-icon" aria-hidden="true">🛡️</span>
                <h2 className="panel-title-text">{t.shelterTitle || 'RECOMMENDED SHELTER CANDIDATE'}</h2>
              </div>
              <span className="shelter-count-badge">
                {isAvailable('shelters') || isAvailable('facilities') ? `${facilities.length} IDENTIFIED CENTERS` : `${statusLabel('shelters')} · facility data`}
              </span>
            </div>

            {nearestFacility ? (
              <div className="shelter-info-block">
                <h3 className="shelter-name-headline" title={nearestFacility.name}>
                  {nearestFacility.name}
                </h3>
                <p className="panel-subtitle">Candidate listing only; operational status, capacity, accessibility and flood safety are not independently verified.</p>

                {/* 2x2 Shelter Metric Grid */}
                <div className="shelter-metrics-grid">
                  <div className="shelter-metric-tile">
                    <span className="metric-tile-label">⛰️ Ground Elevation</span>
                    <strong className="metric-tile-value safe-text">
                      {nearestFacility.elevation_m ? `${nearestFacility.elevation_m} m` : (nearestFacility.distance_km != null ? `${nearestFacility.distance_km.toFixed(2)} km` : 'Unavailable')}
                    </strong>
                  </div>

                  <div className="shelter-metric-tile">
                    <span className="metric-tile-label">🛡️ Flood Risk</span>
                    <strong className="metric-tile-value safe-text">
                      {nearestFacility.flood_risk || 'Unavailable'}
                    </strong>
                  </div>

                  <div className="shelter-metric-tile">
                    <span className="metric-tile-label">♿ Accessibility</span>
                    <strong className="metric-tile-value">
                      {nearestFacility.accessibility || nearestFacility.road_accessibility || 'Unavailable'}
                    </strong>
                  </div>

                  <div className="shelter-metric-tile">
                    <span className="metric-tile-label">👥 Available Space</span>
                    <strong className="metric-tile-value">
                      {nearestFacility.available_capacity != null ? `${nearestFacility.available_capacity}` : (nearestFacility.capacity != null ? `${nearestFacility.capacity}` : 'Unavailable')}
                    </strong>
                  </div>
                </div>

                <div className="shelter-equipped-notes">
                  <span className="equipped-icon" aria-hidden="true">📦</span>
                  <span>Equipped: {nearestFacility.facilities || 'Unavailable in source data'}</span>
                </div>

                <div className="shelter-disclaimer-box">
                  <span aria-hidden="true">ℹ️</span>
                  <span>Truth-in-Facilities: Operational status & capacity are public unverified records. Confirm with local ward staff.</span>
                </div>

                {/* Big Vibrant Blue Evacuation Route Button */}
                <button
                  type="button"
                  className="btn-calculate-route-prominent"
                  onClick={onCalculateRoute}
                  disabled={isRouting}
                >
                  {isRouting ? (
                    <>
                      <span className="route-spinner" aria-hidden="true" />
                      <span>{t.calculatingRoute || 'Computing mapped evacuation route...'}</span>
                    </>
                  ) : (
                    <>
                      <span className="route-btn-icon" aria-hidden="true">🚗</span>
                      <span>{t.calculateRoute || 'Calculate Evacuation Route'}</span>
                    </>
                  )}
                </button>
                <button
                  type="button"
                  className="btn-external-navigation"
                  onClick={onOpenNavigation}
                  disabled={!nearestFacility}
                >
                  <span aria-hidden="true">🧭</span>
                  Open external directions (not flood-verified)
                </button>

                {/* Route Result Panel */}
                {route && (
                  <div className="route-result-embed">
                    {isNoSafeRoute ? (
                      <div className="route-no-safe-alert" role="alert">
                        <strong>⚠️ NO SAFE ROUTE FOUND</strong>
                        <p>{route.warning_note || 'All available road segments intersect confirmed flood zones. Seek elevated local shelter.'}</p>
                      </div>
                    ) : (
                      <div className="route-success-details">
                        <div className="route-quick-stats">
                          <div className="stat-unit">
                            <span className="stat-lbl">DISTANCE</span>
                            <strong className="stat-val">
                              {route.route_distance_km != null 
                                ? `${route.route_distance_km.toFixed(2)} km` 
                                : (route.distance_km != null ? `${route.distance_km.toFixed(2)} km` : 'N/A')}
                            </strong>
                          </div>
                          <div className="stat-unit">
                            <span className="stat-lbl">EST. TRAVEL</span>
                            <strong className="stat-val">
                              {route.estimated_duration_min != null 
                                ? `${Math.round(route.estimated_duration_min)} min` 
                                : (route.estimated_travel_time_minutes != null ? `${Math.round(route.estimated_travel_time_minutes)} min` : 'Not estimated')}
                            </strong>
                          </div>
                          <div className="stat-unit">
                            <span className="stat-lbl">ROAD CONDITION</span>
                            <strong className={`stat-val ${isDetour ? 'warning-text' : 'safe-text'}`}>
                              {isDetour
                                ? 'Detour computed (hazards avoided)'
                                : route.road_condition_status === 'CLEAR'
                                  ? 'Current status not verified'
                                  : (route.road_condition_status || 'Not reported')}
                            </strong>
                          </div>
                        </div>

                        {isDetour && (
                          <div className="route-detour-notice-small">
                            <strong>⚠️ Detour Active:</strong> Submerged primary roads avoided via OpenStreetMap detour.
                          </div>
                        )}
                        {route.alternatives && route.alternatives.length > 0 && (
                          <div className="route-detour-notice-small" style={{ borderColor: '#a855f7', color: '#d8b4fe' }}>
                            <strong>🔀 Alternatives:</strong> {route.alternatives.length} alternative route(s) computed.
                          </div>
                        )}
                        <p className="route-limitation-tiny">
                          {route.safety_disclaimer || 'Calculated on static OSM drive network. Real-time water depth unmodelled. Never cross moving floodwaters.'}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="shelter-loading-placeholder">
                {statusOf('shelters') === 'loading' || statusOf('facilities') === 'loading'
                  ? <span className="route-spinner" aria-hidden="true" />
                  : <span aria-hidden="true">⚠️</span>}
                <p>
                  {statusOf('shelters') === 'loading' || statusOf('facilities') === 'loading'
                    ? 'Loading emergency facility data...'
                    : 'No emergency facility data is currently available. Confirm destinations directly with local authorities.'}
                </p>
              </div>
            )}

            {/* Quick Link to Browse Full Directory */}
            <div className="panel-footer-actions">
              <button
                type="button"
                className="btn-link-action"
                onClick={() => onNavigateToTab('directory')}
              >
                Browse All {facilities.length || 'available'} Centers & Hospitals →
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
