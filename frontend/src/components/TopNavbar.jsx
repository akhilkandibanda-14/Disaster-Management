import React, { useState } from 'react'

const HYDERABAD_PRESETS = [
  { name: 'Central Hyderabad (Abids)', lat: 17.3850, lon: 78.4867 },
  { name: 'Musi River Basin (Purana Pul)', lat: 17.3670, lon: 78.4720 },
  { name: 'Khairatabad / Hussain Sagar', lat: 17.4123, lon: 78.4608 },
  { name: 'Secunderabad Station', lat: 17.4399, lon: 78.4983 },
  { name: 'Charminar / Old City', lat: 17.3616, lon: 78.4747 },
  { name: 'Hitec City / Madhapur', lat: 17.4483, lon: 78.3808 },
  { name: 'Uppal / Ramanthapur', lat: 17.4018, lon: 78.5580 },
  { name: 'Gachibowli Financial Dist.', lat: 17.4401, lon: 78.3489 },
]

export default function TopNavbar({
  activeTab,
  location,
  locationStatus,
  apiStatus,
  loading,
  hazardWarning,
  onLocationSelect,
  onRefreshLocation,
  onToggleMobileSidebar,
  onOpenSOS
}) {
  const [customLat, setCustomLat] = useState('')
  const [customLon, setCustomLon] = useState('')
  const [showCoordDialog, setShowCoordDialog] = useState(false)
  const [coordError, setCoordError] = useState('')

  const handlePresetChange = (e) => {
    const val = e.target.value
    if (!val) return
    const [latStr, lonStr] = val.split(',')
    const lat = parseFloat(latStr)
    const lon = parseFloat(lonStr)
    if (!isNaN(lat) && !isNaN(lon)) {
      onLocationSelect({ latitude: lat, longitude: lon })
    }
  }

  const handleCustomSubmit = (e) => {
    e.preventDefault()
    setCoordError('')
    const lat = parseFloat(customLat)
    const lon = parseFloat(customLon)
    if (isNaN(lat) || isNaN(lon)) {
      setCoordError('Please enter valid numeric latitude and longitude.')
      return
    }
    if (lat < 17.2 || lat > 17.6 || lon < 78.2 || lon > 78.7) {
      setCoordError('Coordinates must be inside Hyderabad study bounds (Lat: 17.2–17.6, Lon: 78.2–78.7).')
      return
    }
    onLocationSelect({ latitude: lat, longitude: lon })
    setShowCoordDialog(false)
    setCustomLat('')
    setCustomLon('')
  }

  const pageTitles = {
    overview: 'Operations Overview',
    map: 'Interactive Flood Hazard Map',
    routes: 'Safe Evacuation Route Planner',
    shelters: 'Shelter & Medical Directory',
    alerts: 'Live Disaster Advisories',
    operations: 'INDOFLOODS Telemetry Command',
    about: 'Data Provenance & System Specifications'
  }

  return (
    <header className="app-topbar">
      <div className="topbar-left">
        <button 
          type="button" 
          className="topbar-menu-toggle" 
          onClick={onToggleMobileSidebar}
          aria-label="Toggle navigation menu"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
        <div className="topbar-title-wrap">
          <span className="topbar-page-eyebrow">HYDERABAD METROPOLITAN AREA</span>
          <h1 className="topbar-page-title">{pageTitles[activeTab] || 'Flood Management'}</h1>
        </div>
      </div>

      <div className="topbar-center">
        <div className="location-search-wrap">
          <span className="search-icon" aria-hidden="true">📍</span>
          <select 
            className="location-preset-select" 
            onChange={handlePresetChange}
            value=""
            aria-label="Select Hyderabad region"
          >
            <option value="" disabled>Jump to Hyderabad Location...</option>
            {HYDERABAD_PRESETS.map((preset) => (
              <option key={preset.name} value={`${preset.lat},${preset.lon}`}>
                {preset.name}
              </option>
            ))}
          </select>
          <button 
            type="button" 
            className="coord-input-trigger" 
            onClick={() => setShowCoordDialog(!showCoordDialog)}
            title="Enter custom coordinates"
          >
            Custom Lat/Lon
          </button>
        </div>

        {showCoordDialog && (
          <div className="coord-dialog">
            <form onSubmit={handleCustomSubmit}>
              <div className="coord-dialog-title">
                <strong>Enter Hyderabad Coordinates</strong>
                <button type="button" onClick={() => setShowCoordDialog(false)} aria-label="Close">✕</button>
              </div>
              <div className="coord-inputs">
                <input 
                  type="text" 
                  placeholder="Lat (17.20 - 17.60)" 
                  value={customLat}
                  onChange={(e) => setCustomLat(e.target.value)}
                />
                <input 
                  type="text" 
                  placeholder="Lon (78.20 - 78.70)" 
                  value={customLon}
                  onChange={(e) => setCustomLon(e.target.value)}
                />
              </div>
              {coordError && <p className="coord-error">{coordError}</p>}
              <div className="coord-actions">
                <button type="button" className="btn-text" onClick={() => setShowCoordDialog(false)}>Cancel</button>
                <button type="submit" className="btn-primary-small">Set Location</button>
              </div>
            </form>
          </div>
        )}
      </div>

      <div className="topbar-right">
        {hazardWarning && hazardWarning.is_in_hazard_zone && (
          <div className="topbar-hazard-pill" role="alert" title={hazardWarning.disclaimer}>
            <span className="hazard-pill-dot" />
            <span>Hazard Active: {hazardWarning.highest_severity}</span>
          </div>
        )}

        <button 
          type="button" 
          className="topbar-refresh-btn" 
          onClick={onRefreshLocation}
          disabled={loading}
          title="Refresh current location and telemetry"
          aria-label="Refresh telemetry"
        >
          <svg 
            className={loading ? 'spinning' : ''} 
            width="16" 
            height="16" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round"
          >
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
          <span className="refresh-text">{loading ? 'Updating...' : 'Live GPS'}</span>
        </button>

        <div className="topbar-status-badge">
          <span className={`status-dot ${apiStatus.includes('online') || apiStatus.includes('Online') ? 'online' : 'offline'}`} />
          <span className="status-label">{apiStatus}</span>
        </div>
      </div>
    </header>
  )
}
