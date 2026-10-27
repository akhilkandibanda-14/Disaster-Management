import React, { useState } from 'react'

export default function AlertsTab({ alerts, floodHazards, hazardWarning }) {
  const [filter, setFilter] = useState('ALL')

  // Combine alerts and flood hazards
  const combinedAlerts = [
    ...alerts.map(a => ({
      id: a.alert_id || a.id || a.title,
      title: a.title,
      severity: a.severity || 'HIGH',
      data_status: a.is_authoritative ? 'AUTHORITATIVE' : (a.data_status || 'OFFICIAL_ALERT'),
      source: a.source || 'NDMA SACHET',
      description: a.description,
      timestamp: a.timestamp || a.issued_at || 'Recent',
      is_authoritative: a.is_authoritative
    })),
    ...floodHazards.map(h => ({
      id: h.hazard_id,
      title: h.title,
      severity: h.severity,
      data_status: h.data_status,
      source: h.source_name || 'Municipal Flood Survey',
      description: h.description,
      timestamp: 'Active Bulletin',
      is_authoritative: h.data_status === 'AUTHORITATIVE'
    }))
  ]

  const filteredAlerts = combinedAlerts.filter((item) => {
    if (filter === 'ALL') return true
    if (filter === 'AUTHORITATIVE') return item.is_authoritative || item.data_status === 'AUTHORITATIVE'
    if (filter === 'DEMO') return item.data_status === 'DEMO'
    if (filter === 'MUNICIPAL') return item.data_status === 'PUBLIC_UNVERIFIED' || item.data_status === 'MUNICIPAL'
    return true
  })

  return (
    <div className="tab-alerts">
      <div className="card-panel alerts-header-panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Active Disaster & Flood Bulletins</h2>
            <p className="panel-subtitle">Official Common Alerting Protocol (CAP) and municipal flood advisories.</p>
          </div>
          <div className="filter-pill-group">
            <button 
              type="button" 
              className={`filter-pill ${filter === 'ALL' ? 'active' : ''}`}
              onClick={() => setFilter('ALL')}
            >
              All Bulletins ({combinedAlerts.length})
            </button>
            <button 
              type="button" 
              className={`filter-pill ${filter === 'AUTHORITATIVE' ? 'active' : ''}`}
              onClick={() => setFilter('AUTHORITATIVE')}
            >
              Authoritative
            </button>
            <button 
              type="button" 
              className={`filter-pill ${filter === 'DEMO' ? 'active' : ''}`}
              onClick={() => setFilter('DEMO')}
            >
              Demo Records
            </button>
          </div>
        </div>

        {/* Hazard Warning at Current Location */}
        {hazardWarning && hazardWarning.is_in_hazard_zone && (
          <div className="hazard-warning-banner" role="alert">
            <span className="warning-icon" aria-hidden="true">⚠️</span>
            <div className="warning-content">
              <strong>ACTIVE HAZARD INTERSECTED AT REPORTED LOCATION</strong>
              <p>Your coordinates intersect {hazardWarning.hazard_count} active flood hazard boundary zones. Please consult the safety advice below.</p>
            </div>
          </div>
        )}
      </div>

      <div className="alerts-cards-list">
        {filteredAlerts.length === 0 ? (
          <div className="empty-state-card card-panel">
            <span className="empty-icon">🔔</span>
            <h3>No Active Bulletins In This Category</h3>
            <p className="muted">No disaster bulletins currently match the selected filter category.</p>
          </div>
        ) : (
          filteredAlerts.map((alert) => {
            const isAuth = alert.is_authoritative || alert.data_status === 'AUTHORITATIVE'
            const isDemo = alert.data_status === 'DEMO'
            const severityColor = alert.severity === 'CRITICAL' || alert.severity === 'HIGH' ? '#ef4444' : '#f59e0b'

            return (
              <div 
                key={alert.id}
                className={`alert-bulletin-card card-panel ${isAuth ? 'authoritative' : (isDemo ? 'demo' : '')}`}
              >
                <div className="bulletin-header">
                  <div className="bulletin-title-row">
                    <span className="bulletin-severity-dot" style={{ backgroundColor: severityColor }} />
                    <h3 className="bulletin-title">{alert.title}</h3>
                  </div>
                  <div className="bulletin-badges-row">
                    <span className={`status-badge ${isAuth ? 'authoritative' : (isDemo ? 'demo' : 'unverified')}`}>
                      {alert.data_status}
                    </span>
                    <span className="severity-badge" style={{ color: severityColor, borderColor: severityColor }}>
                      {alert.severity}
                    </span>
                  </div>
                </div>

                <p className="bulletin-desc">{alert.description}</p>

                <div className="bulletin-footer">
                  <div className="bulletin-meta">
                    <span><strong>Source:</strong> {alert.source}</span>
                    <span><strong>Issued:</strong> {alert.timestamp}</span>
                  </div>
                  {isAuth ? (
                    <span className="badge-verified">✓ Official Authority Bulletin</span>
                  ) : (
                    <span className="badge-unverified">Unverified / Simulation</span>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
