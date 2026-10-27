import React from 'react'

export default function Header({
  activeTab,
  onSelectTab,
  language,
  onSelectLanguage,
  isSevereWeather,
  onToggleWeather,
  highContrast,
  onToggleHighContrast,
  onOpenSOS,
  apiStatus,
  alertsCount,
  t
}) {
  const tabs = [
    { id: 'citizen', label: t.citizenTab || 'Citizen Dashboard', icon: '📖' },
    { id: 'map', label: t.mapTab || 'Interactive Flood Map', icon: '🗺️' },
    { id: 'routes', label: t.routesTab || 'Evacuation Routes', icon: '🚗' },
    { id: 'directory', label: t.directoryTab || 'Emergency Directory', icon: '🚨' },
    { id: 'protocols', label: t.protocolsTab || 'Safety Protocols', icon: '🛡️' },
    { id: 'operations', label: t.operationsTab || 'Operations Control', icon: '⚙️' },
    { id: 'about', label: t.aboutTab || 'Data Sources & Limits', icon: 'ℹ️' },
  ]

  return (
    <header className="command-header">
      {/* Top Banner Row */}
      <div className="command-header-top">
        <div className="brand-zone">
          <div className="brand-shield-icon" aria-hidden="true">
            <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
              <path d="M12 8v4"></path>
              <path d="M12 16h.01"></path>
            </svg>
          </div>
          <div>
            <div className="brand-title-line">
              <h1>{t.appTitle || 'SafeMap AI Hyderabad'}</h1>
            </div>
            <p className="brand-sub-line">{t.appSubtitle || 'HYDERABAD FLOOD DISASTER MANAGEMENT & EMERGENCY OPERATIONS'}</p>
          </div>
        </div>

        <div className="header-system-pill">
          <span className="wave-icon" aria-hidden="true">🌊</span>
          <span>{t.systemBadge || 'FLOOD EARLY WARNING & EVACUATION SYSTEM · HYDERABAD URBAN DRAINAGE & MUSI RIVER BASIN'}</span>
        </div>
      </div>

      {/* Control Actions Row */}
      <div className="command-controls-row">
        <div className="control-switches-left">
          {/* Weather Simulation Toggle */}
          <div className="weather-toggle-group">
            <button
              type="button"
              className={`weather-mode-btn ${!isSevereWeather ? 'active normal' : ''}`}
              onClick={() => onToggleWeather(false)}
            >
              ☀️ {t.normalWeather || 'Normal Weather'}
            </button>
            <button
              type="button"
              className={`weather-mode-btn ${isSevereWeather ? 'active severe' : ''}`}
              onClick={() => onToggleWeather(true)}
            >
              🌧️ {t.severeWeather || 'Severe Flood Weather'}
            </button>
          </div>

          {/* Language Selector */}
          <div className="lang-selector-group">
            <button
              type="button"
              className={`lang-btn ${language === 'en' ? 'active' : ''}`}
              onClick={() => onSelectLanguage('en')}
            >
              EN
            </button>
            <button
              type="button"
              className={`lang-btn ${language === 'te' ? 'active' : ''}`}
              onClick={() => onSelectLanguage('te')}
            >
              తెలుగు
            </button>
            <button
              type="button"
              className={`lang-btn ${language === 'hi' ? 'active' : ''}`}
              onClick={() => onSelectLanguage('hi')}
            >
              हिन्दी
            </button>
          </div>

          {/* High Contrast Toggle */}
          <button
            type="button"
            className={`contrast-toggle-btn ${highContrast ? 'active' : ''}`}
            onClick={onToggleHighContrast}
            title="Toggle high contrast accessibility view"
            aria-label="Toggle high contrast"
          >
            👁️
          </button>
        </div>

        {/* SOS Emergency Button */}
        <div className="control-actions-right">
          <button
            type="button"
            className="header-sos-emergency-btn"
            onClick={onOpenSOS}
            aria-label="Submit SOS Emergency Alert"
          >
            <span className="sos-flare-icon" aria-hidden="true">🚨</span>
            <span>{t.sosButton || 'SUBMIT SOS EMERGENCY'}</span>
          </button>
        </div>
      </div>

      {/* Navigation Bar */}
      <nav className="command-nav-bar" aria-label="Dashboard views">
        <div className="nav-tabs-scroll">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                type="button"
                className={`command-nav-tab ${isActive ? 'active' : ''}`}
                onClick={() => onSelectTab(tab.id)}
                aria-current={isActive ? 'page' : undefined}
              >
                <span className="nav-tab-icon" aria-hidden="true">{tab.icon}</span>
                <span className="nav-tab-text">{tab.label}</span>
              </button>
            )
          })}
        </div>

        <div className="nav-status-indicator">
          <span className={`status-led ${apiStatus.includes('Online') || apiStatus.includes('online') ? 'online' : 'offline'}`} />
          <span className="nav-status-text">{apiStatus}</span>
        </div>
      </nav>
    </header>
  )
}
