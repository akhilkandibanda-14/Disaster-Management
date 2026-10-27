import React, { useState, useMemo } from 'react'

export default function SheltersTab({
  facilities,
  selectedFacility,
  onFacilitySelect,
  onPlanRouteToFacility
}) {
  const [filterType, setFilterType] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredFacilities = useMemo(() => {
    return facilities.filter((f) => {
      const matchesType = filterType === 'ALL' || f.facility_type === filterType
      const matchesSearch = !searchQuery || f.name.toLowerCase().includes(searchQuery.toLowerCase())
      return matchesType && matchesSearch
    })
  }, [facilities, filterType, searchQuery])

  return (
    <div className="tab-shelters">
      <div className="shelters-header-panel card-panel">
        <div className="shelters-header-top">
          <div>
            <h2 className="panel-title">Emergency Facilities & Shelter Directory</h2>
            <p className="panel-subtitle">
              Public shelters, hospitals, and designated relief points across Hyderabad.
            </p>
          </div>
          <div className="shelters-count-badge">
            <strong>{filteredFacilities.length}</strong>
            <span>Facilities Found</span>
          </div>
        </div>

        {/* Truth-in-Facilities Disclaimer */}
        <div className="facilities-truth-box">
          <strong>⚠️ Truth-in-Facilities Disclosure:</strong> Facility listings are derived from open municipal geospatial surveys. Structural safety classifications and real-time live bed capacities are <strong>PUBLIC_UNVERIFIED</strong> unless explicitly confirmed by state disaster health authorities.
        </div>

        {/* Filters & Search Bar */}
        <div className="shelters-filter-bar">
          <div className="search-input-wrap">
            <span className="search-icon" aria-hidden="true">🔍</span>
            <input
              type="text"
              placeholder="Search facility by name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search facility by name"
            />
            {searchQuery && (
              <button 
                type="button" 
                className="clear-search-btn" 
                onClick={() => setSearchQuery('')}
              >
                ✕
              </button>
            )}
          </div>

          <div className="type-filter-tabs">
            <button
              type="button"
              className={`filter-tab ${filterType === 'ALL' ? 'active' : ''}`}
              onClick={() => setFilterType('ALL')}
            >
              All Types ({facilities.length})
            </button>
            <button
              type="button"
              className={`filter-tab ${filterType === 'SHELTER' ? 'active' : ''}`}
              onClick={() => setFilterType('SHELTER')}
            >
              Shelters ({facilities.filter(f => f.facility_type === 'SHELTER').length})
            </button>
            <button
              type="button"
              className={`filter-tab ${filterType === 'HOSPITAL' ? 'active' : ''}`}
              onClick={() => setFilterType('HOSPITAL')}
            >
              Hospitals ({facilities.filter(f => f.facility_type === 'HOSPITAL').length})
            </button>
          </div>
        </div>
      </div>

      {/* Facilities Cards Grid */}
      <div className="shelters-cards-grid">
        {filteredFacilities.length === 0 ? (
          <div className="empty-state-card card-panel">
            <span className="empty-icon">🏛️</span>
            <h3>No Facilities Match Your Filter</h3>
            <p className="muted">Try adjusting your search query or reset the type filter to "All Types".</p>
            <button 
              type="button" 
              className="btn-secondary" 
              onClick={() => { setFilterType('ALL'); setSearchQuery(''); }}
            >
              Reset Filters
            </button>
          </div>
        ) : (
          filteredFacilities.map((fac) => {
            const isSelected = selectedFacility && (
              (selectedFacility.facility_id && selectedFacility.facility_id === fac.facility_id) ||
              (selectedFacility.id && selectedFacility.id === fac.id)
            )
            const isHospital = fac.facility_type === 'HOSPITAL'

            return (
              <div 
                key={fac.facility_id || fac.id || fac.name}
                className={`shelter-card card-panel ${isSelected ? 'selected' : ''}`}
              >
                <div className="shelter-card-top">
                  <div className="shelter-title-wrap">
                    <span className="facility-avatar" aria-hidden="true">
                      {isHospital ? '🏥' : '🏛️'}
                    </span>
                    <div>
                      <h3 className="shelter-name">{fac.name}</h3>
                      <span className={`facility-type-badge ${isHospital ? 'hospital' : 'shelter'}`}>
                        {fac.facility_type || 'SHELTER'}
                      </span>
                    </div>
                  </div>
                  {fac.distance_km != null && (
                    <div className="shelter-distance-chip">
                      <strong>{fac.distance_km.toFixed(2)} km</strong>
                      <span>From Location</span>
                    </div>
                  )}
                </div>

                <div className="shelter-details-grid">
                  <div className="detail-item">
                    <span className="detail-label">OPERATIONAL STATUS</span>
                    <strong className="detail-val unverified-status">
                      {fac.operational_status_verified ? 'Verified Active' : 'Unverified (UNKNOWN)'}
                    </strong>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">BED CAPACITY</span>
                    <strong className="detail-val unverified-status">
                      {fac.capacity_verified && fac.capacity ? `${fac.capacity} Beds` : 'Capacity Unknown'}
                    </strong>
                  </div>
                  <div className="detail-item full-width">
                    <span className="detail-label">SAFETY CLASSIFICATION</span>
                    <span className="detail-val">
                      {fac.verification_note || 'Safety condition: Not verified. Structural safety not confirmed.'}
                    </span>
                  </div>
                </div>

                <div className="shelter-card-actions">
                  <button
                    type="button"
                    className={`btn-select-facility ${isSelected ? 'active' : ''}`}
                    onClick={() => onFacilitySelect(fac)}
                  >
                    {isSelected ? '✓ Selected Destination' : 'Select Destination'}
                  </button>
                  <button
                    type="button"
                    className="btn-plan-route"
                    onClick={() => {
                      onFacilitySelect(fac)
                      if (onPlanRouteToFacility) onPlanRouteToFacility(fac)
                    }}
                  >
                    Plan Evac Route →
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
