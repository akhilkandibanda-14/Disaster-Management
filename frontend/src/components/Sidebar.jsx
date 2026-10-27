import React from 'react'

export default function Sidebar({ 
  activeTab, 
  onSelectTab, 
  location, 
  locationStatus, 
  alertsCount, 
  hazardsCount, 
  facilitiesCount, 
  hasActiveRoute,
  onOpenSOS,
  isMobileOpen,
  onCloseMobile
}) {
  const navItems = [
    {
      id: 'overview',
      label: 'Overview',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="7"></rect>
          <rect x="14" y="3" width="7" height="7"></rect>
          <rect x="14" y="14" width="7" height="7"></rect>
          <rect x="3" y="14" width="7" height="7"></rect>
        </svg>
      )
    },
    {
      id: 'map',
      label: 'Flood Map',
      badge: hazardsCount > 0 ? `${hazardsCount}` : null,
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon>
          <line x1="8" y1="2" x2="8" y2="18"></line>
          <line x1="16" y1="6" x2="16" y2="22"></line>
        </svg>
      )
    },
    {
      id: 'routes',
      label: 'Evacuation Routes',
      badge: hasActiveRoute ? 'Active' : null,
      badgeType: hasActiveRoute ? 'badge-success' : '',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="6" cy="19" r="3"></circle>
          <path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"></path>
          <circle cx="18" cy="5" r="3"></circle>
        </svg>
      )
    },
    {
      id: 'shelters',
      label: 'Shelters & Facilities',
      badge: facilitiesCount > 0 ? `${facilitiesCount}` : null,
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
          <polyline points="9 22 9 12 15 12 15 22"></polyline>
        </svg>
      )
    },
    {
      id: 'alerts',
      label: 'Disaster Alerts',
      badge: alertsCount > 0 ? `${alertsCount}` : null,
      badgeType: alertsCount > 0 ? 'badge-danger' : '',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
        </svg>
      )
    },
    {
      id: 'operations',
      label: 'Operations Command',
      badge: 'Admin',
      badgeType: 'badge-accent',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
      )
    },
    {
      id: 'about',
      label: 'Data Sources & Limits',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>
      )
    }
  ]

  return (
    <>
      {isMobileOpen && (
        <div 
          className="sidebar-backdrop" 
          onClick={onCloseMobile} 
          aria-hidden="true" 
        />
      )}
      <aside className={`app-sidebar ${isMobileOpen ? 'mobile-open' : ''}`} aria-label="Main Navigation">
        <div className="sidebar-brand">
          <div className="brand-logo-wrap">
            <span className="brand-icon" aria-hidden="true">🛡️</span>
            <div>
              <span className="brand-title">SafeMap AI</span>
              <span className="brand-subtitle">Flood Decision Support</span>
            </div>
          </div>
          {isMobileOpen && (
            <button 
              type="button" 
              className="sidebar-mobile-close" 
              onClick={onCloseMobile} 
              aria-label="Close sidebar"
            >
              ✕
            </button>
          )}
        </div>

        <nav className="sidebar-nav">
          <span className="sidebar-section-title">Navigation</span>
          <ul className="sidebar-menu">
            {navItems.map((item) => {
              const isActive = activeTab === item.id
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className={`sidebar-nav-btn ${isActive ? 'active' : ''}`}
                    onClick={() => {
                      onSelectTab(item.id)
                      if (onCloseMobile) onCloseMobile()
                    }}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <span className="nav-btn-icon">{item.icon}</span>
                    <span className="nav-btn-label">{item.label}</span>
                    {item.badge && (
                      <span className={`nav-btn-badge ${item.badgeType || ''}`}>
                        {item.badge}
                      </span>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
        </nav>

        <div className="sidebar-footer">
          <button 
            type="button" 
            className="sidebar-sos-btn" 
            onClick={onOpenSOS}
            aria-label="Emergency protocols and contacts"
          >
            <span className="sos-pulse" aria-hidden="true">🚨</span>
            <span className="sos-btn-text">
              <strong>Emergency SOS</strong>
              <small>Hotlines & Protocols</small>
            </span>
          </button>

          <div className="sidebar-location-chip" title={`${location.latitude}, ${location.longitude}`}>
            <div className="location-chip-indicator" />
            <div className="location-chip-info">
              <span className="location-chip-status">{locationStatus}</span>
              <span className="location-chip-coords">
                {location.latitude.toFixed(4)}°N, {location.longitude.toFixed(4)}°E
              </span>
            </div>
          </div>

          <div className="sidebar-meta">
            <span>SafeMap AI · Pilot Prototype</span>
            <span className="sidebar-scope">Hyderabad Service Region</span>
          </div>
        </div>
      </aside>
    </>
  )
}
