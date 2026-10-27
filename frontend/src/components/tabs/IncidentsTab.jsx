import React, { useState } from 'react'

const HYDERABAD_PRESETS = [
  { name: 'Current Location', latitude: null, longitude: null },
  { name: 'Khairatabad Underpass', latitude: 17.4125, longitude: 78.4590 },
  { name: 'Tolichowki Flyover', latitude: 17.3971, longitude: 78.4118 },
  { name: 'Musi River Causeway (Chaderghat)', latitude: 17.3789, longitude: 78.4871 },
  { name: 'Begumpet Rasoolpura Canal', latitude: 17.4412, longitude: 78.4719 },
  { name: 'Old City / Charminar Corridor', latitude: 17.3616, longitude: 78.4747 },
  { name: 'Malakpet Nala Bridge', latitude: 17.3752, longitude: 78.5028 },
]

const FLOOD_CATEGORIES = [
  { value: 'WATERLOGGING', label: 'Street Waterlogging (Stagnant Water)' },
  { value: 'ROAD_SUBMERGED', label: 'Road Submerged / Impassable' },
  { value: 'DRAINAGE_OVERFLOW', label: 'Drainage / Stormwater Nala Overflow' },
  { value: 'RIVER_SPILL', label: 'Musi River Bank Spillover' },
  { value: 'FLASH_FLOOD', label: 'Flash Flood Runoff' },
  { value: 'STRANDED_PERSONS', label: 'Stranded Persons Needing Rescue' },
  { value: 'INFRASTRUCTURE_DAMAGE', label: 'Damaged Bridge / Culvert / Road Breach' },
  { value: 'OTHER_FLOOD', label: 'Other Flood Hazard' },
]

const SEVERITY_LEVELS = [
  { value: 'LOW', label: 'Low (Puddles, Slow Traffic)', color: '#38bdf8' },
  { value: 'MODERATE', label: 'Moderate (Knee-deep, Stalls 2-Wheelers)', color: '#f59e0b' },
  { value: 'HIGH', label: 'High (Over 2 Feet, Cars Floating/Stalled)', color: '#ea580c' },
  { value: 'CRITICAL', label: 'Critical (Rapid Current, Homes Inundated)', color: '#ef4444' },
]

export default function IncidentsTab({
  location,
  incidents = [],
  onRefreshIncidents,
  apiBaseUrl = 'http://127.0.0.1:8000',
  t = {}
}) {
  const [selectedPreset, setSelectedPreset] = useState(0)
  const [customLat, setCustomLat] = useState(location?.latitude?.toFixed(4) || '17.3850')
  const [customLon, setCustomLon] = useState(location?.longitude?.toFixed(4) || '78.4867')
  const [locationName, setLocationName] = useState('')
  const [category, setCategory] = useState('WATERLOGGING')
  const [severity, setSeverity] = useState('MODERATE')
  const [description, setDescription] = useState('')
  const [reporterContact, setReporterContact] = useState('')
  const [privacyConsent, setPrivacyConsent] = useState(true)
  const [imagePreview, setImagePreview] = useState(null)
  const [imagePayload, setImagePayload] = useState(null)

  // Status & Feedback state
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submissionSuccess, setSubmissionSuccess] = useState(null)
  const [submissionError, setSubmissionError] = useState('')

  // Incident list filtering
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [categoryFilter, setCategoryFilter] = useState('ALL')
  const [updatingId, setUpdatingId] = useState(null)

  const handlePresetChange = (idx) => {
    setSelectedPreset(idx)
    const preset = HYDERABAD_PRESETS[idx]
    if (preset.latitude !== null && preset.longitude !== null) {
      setCustomLat(preset.latitude.toFixed(4))
      setCustomLon(preset.longitude.toFixed(4))
      setLocationName(preset.name)
    } else {
      setCustomLat(location?.latitude?.toFixed(4) || '17.3850')
      setCustomLon(location?.longitude?.toFixed(4) || '78.4867')
      setLocationName('')
    }
  }

  const handleImageUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > 5 * 1024 * 1024) {
      setSubmissionError('Photo size must be under 5 MB.')
      return
    }

    if (!['image/jpeg', 'image/png', 'image/webp', 'image/jpg'].includes(file.type)) {
      setSubmissionError('Please select a valid JPEG, PNG, or WebP photo.')
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      setImagePreview(reader.result)
      setImagePayload(reader.result)
      setSubmissionError('')
    }
    reader.onerror = () => {
      setSubmissionError('Failed to read image file.')
    }
    reader.readAsDataURL(file)
  }

  const handleRemoveImage = () => {
    setImagePreview(null)
    setImagePayload(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmissionError('')
    setSubmissionSuccess(null)

    const latNum = parseFloat(customLat)
    const lonNum = parseFloat(customLon)

    if (isNaN(latNum) || isNaN(lonNum)) {
      setSubmissionError('Please provide valid latitude and longitude coordinates.')
      return
    }

    // Boundary check
    if (latNum < 17.2 || latNum > 17.6 || lonNum < 78.2 || lonNum > 78.7) {
      setSubmissionError('Coordinates are outside Greater Hyderabad bounds (17.20°N-17.60°N, 78.20°E-78.70°E).')
      return
    }

    if (!description || description.trim().length < 10) {
      setSubmissionError('Please provide a descriptive report of at least 10 characters.')
      return
    }

    if (!privacyConsent) {
      setSubmissionError('Please confirm the privacy statement before submitting.')
      return
    }

    setIsSubmitting(true)

    const payload = {
      latitude: latNum,
      longitude: lonNum,
      address: locationName || 'Hyderabad Municipal Area',
      location_name: locationName || 'Hyderabad Municipal Area',
      incident_category: category,
      severity: severity,
      description: description.trim(),
      reporter_contact: reporterContact.trim() || undefined,
      image_data: imagePayload || undefined,
    }

    try {
      const response = await fetch(`${apiBaseUrl}/incidents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (response.status === 429) {
        throw new Error('Submission rate limit reached: maximum 5 reports per minute per device. Please wait a moment.')
      }

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || `Submission failed with status ${response.status}`)
      }

      const created = await response.json()
      setSubmissionSuccess({
        id: created.id,
        status: created.verification_status || created.status,
        duplicate_of: created.duplicate_of || created.duplicate_of_id,
        report_count: created.report_count || 1,
        message: 'Your report has been submitted to SafeMap AI. It is queued as PUBLIC_UNVERIFIED_REPORT for review by GHMC Disaster Response Force (DRF).'
      })

      // Reset form fields
      setDescription('')
      setImagePreview(null)
      setImagePayload(null)
      setReporterContact('')

      if (onRefreshIncidents) {
        onRefreshIncidents()
      }
    } catch (err) {
      setSubmissionError(err.message || 'An error occurred while submitting your report.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleUpdateStatus = async (incidentId, newStatus, note) => {
    setUpdatingId(incidentId)
    try {
      const resp = await fetch(`${apiBaseUrl}/incidents/${incidentId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          verification_status: newStatus,
          verification_note: note
        })
      })
      if (!resp.ok) {
        throw new Error(`Failed to update status: HTTP ${resp.status}`)
      }
      if (onRefreshIncidents) {
        onRefreshIncidents()
      }
    } catch (err) {
      alert(`Error updating report: ${err.message}`)
    } finally {
      setUpdatingId(null)
    }
  }

  // Filtered incidents
  const filteredIncidents = incidents.filter(inc => {
    const incStatus = inc.verification_status || inc.status || 'PENDING_REVIEW'
    const incCat = inc.incident_category || inc.category || ''

    if (statusFilter !== 'ALL' && incStatus !== statusFilter) return false
    if (categoryFilter !== 'ALL' && incCat !== categoryFilter) return false
    return true
  })

  return (
    <div className="incidents-workspace">
      {/* Top Banner Notice */}
      <div className="incidents-hero-banner">
        <div className="hero-banner-content">
          <div className="hero-icon" aria-hidden="true">📢</div>
          <div>
            <h2 className="hero-title">Crowdsourced Flood Incident Center</h2>
            <p className="hero-subtitle">
              Report live street waterlogging, impassable flooded roads, or open drain overflows in Hyderabad. 
              <strong> All submissions are strictly classified as UNVERIFIED CITIZEN REPORTS</strong> until confirmed on-site by GHMC Disaster Response Force (DRF) or municipal emergency units.
            </p>
          </div>
        </div>
        <div className="hero-privacy-badge">
          🛡️ Privacy Protected · Automated Phone/Email Redaction Active
        </div>
      </div>

      <div className="incidents-layout-grid">
        {/* Left Column: Submission Form */}
        <div className="incident-form-card">
          <div className="form-card-header">
            <h3>📝 Report a Flood Hazard</h3>
            <span className="form-scope-badge">HYDERABAD MUNICIPAL AREA ONLY</span>
          </div>

          {submissionSuccess && (
            <div className="submission-alert success" role="alert">
              <div className="alert-header">
                <strong>✅ Report Logged: {submissionSuccess.id}</strong>
                <span className="status-badge pending">PENDING REVIEW</span>
              </div>
              <p>{submissionSuccess.message}</p>
              {submissionSuccess.duplicate_of && (
                <div className="duplicate-alert-note">
                  ℹ️ Correlated with existing nearby report <strong>{submissionSuccess.duplicate_of}</strong> within 150m.
                </div>
              )}
            </div>
          )}

          {submissionError && (
            <div className="submission-alert error" role="alert">
              ⚠️ {submissionError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="incident-submit-form">
            {/* Location selector */}
            <div className="form-group">
              <label htmlFor="incident-preset-select">Location / Landmark in Hyderabad</label>
              <select
                id="incident-preset-select"
                value={selectedPreset}
                onChange={(e) => handlePresetChange(Number(e.target.value))}
                className="form-control"
              >
                {HYDERABAD_PRESETS.map((preset, idx) => (
                  <option key={preset.name} value={idx}>
                    {preset.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-row coords-row">
              <div className="form-group half">
                <label htmlFor="incident-lat">Latitude (°N)</label>
                <input
                  id="incident-lat"
                  type="number"
                  step="0.0001"
                  value={customLat}
                  onChange={(e) => setCustomLat(e.target.value)}
                  className="form-control"
                  required
                />
              </div>
              <div className="form-group half">
                <label htmlFor="incident-lon">Longitude (°E)</label>
                <input
                  id="incident-lon"
                  type="number"
                  step="0.0001"
                  value={customLon}
                  onChange={(e) => setCustomLon(e.target.value)}
                  className="form-control"
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="incident-location-name">Street / Colony / Landmark Name</label>
              <input
                id="incident-location-name"
                type="text"
                placeholder="e.g. Underpass near Rasoolpura metro station, Begumpet"
                value={locationName}
                onChange={(e) => setLocationName(e.target.value)}
                maxLength={200}
                className="form-control"
              />
            </div>

            {/* Category and Severity */}
            <div className="form-row">
              <div className="form-group half">
                <label htmlFor="incident-category-select">Flood Category</label>
                <select
                  id="incident-category-select"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="form-control"
                  required
                >
                  {FLOOD_CATEGORIES.map(cat => (
                    <option key={cat.value} value={cat.value}>{cat.label}</option>
                  ))}
                </select>
              </div>

              <div className="form-group half">
                <label htmlFor="incident-severity-select">Severity Level</label>
                <select
                  id="incident-severity-select"
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                  className="form-control"
                  required
                >
                  {SEVERITY_LEVELS.map(sev => (
                    <option key={sev.value} value={sev.value}>{sev.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Description */}
            <div className="form-group">
              <label htmlFor="incident-description">
                Observation Description <span className="char-count">({description.length}/1000)</span>
              </label>
              <textarea
                id="incident-description"
                rows={3}
                placeholder="Describe current water depth, road passability, stalled vehicles, or hazards observed..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                maxLength={1000}
                className="form-control textarea"
                required
              />
            </div>

            {/* Optional Photo Attachment */}
            <div className="form-group">
              <label>Optional Field Photo (Max 5 MB)</label>
              {!imagePreview ? (
                <div className="file-upload-box">
                  <input
                    type="file"
                    id="incident-photo-input"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={handleImageUpload}
                    className="file-input-hidden"
                  />
                  <label htmlFor="incident-photo-input" className="file-upload-label">
                    📷 Choose photo of flooded location (JPEG, PNG, WebP)
                  </label>
                </div>
              ) : (
                <div className="image-preview-wrapper">
                  <img src={imagePreview} alt="Field flood condition" className="uploaded-thumb" />
                  <button type="button" onClick={handleRemoveImage} className="remove-photo-btn">
                    ✕ Remove Photo
                  </button>
                </div>
              )}
            </div>

            {/* Optional Reporter Contact */}
            <div className="form-group">
              <label htmlFor="incident-reporter-contact">
                Contact (Optional · Redacted for Public Privacy)
              </label>
              <input
                id="incident-reporter-contact"
                type="text"
                placeholder="Mobile number or email (never shown publicly)"
                value={reporterContact}
                onChange={(e) => setReporterContact(e.target.value)}
                maxLength={50}
                className="form-control"
              />
              <span className="field-hint">
                Phone numbers & emails are automatically sanitized with [REDACTED] to prevent harassment.
              </span>
            </div>

            {/* Privacy Checkbox */}
            <div className="form-checkbox-group">
              <input
                type="checkbox"
                id="incident-privacy-check"
                checked={privacyConsent}
                onChange={(e) => setPrivacyConsent(e.target.checked)}
              />
              <label htmlFor="incident-privacy-check">
                I confirm this report reflects an observed flood hazard in Hyderabad. I understand unverified reports do not replace dialing 112 for acute emergencies.
              </label>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className={`submit-incident-btn ${isSubmitting ? 'submitting' : ''}`}
            >
              {isSubmitting ? 'Submitting Report...' : '🚀 Submit Incident Report'}
            </button>
          </form>
        </div>

        {/* Right Column: Active Community Flood Feed */}
        <div className="incident-feed-card">
          <div className="feed-header">
            <div>
              <h3>📋 Hyderabad Flood Incident Reports</h3>
              <p className="feed-caption">
                Crowdsourced observations verified against municipal inundation zones.
              </p>
            </div>
            <button
              type="button"
              onClick={onRefreshIncidents}
              className="refresh-incidents-btn"
              title="Refresh reports"
            >
              🔄 Refresh
            </button>
          </div>

          {/* Filter Bar */}
          <div className="incident-filter-bar">
            <div className="filter-chips">
              <button
                type="button"
                className={`chip ${statusFilter === 'ALL' ? 'active' : ''}`}
                onClick={() => setStatusFilter('ALL')}
              >
                All ({incidents.length})
              </button>
              <button
                type="button"
                className={`chip ${statusFilter === 'PENDING_REVIEW' ? 'active' : ''}`}
                onClick={() => setStatusFilter('PENDING_REVIEW')}
              >
                Pending Review
              </button>
              <button
                type="button"
                className={`chip ${statusFilter === 'VERIFIED_MUNICIPAL' ? 'active' : ''}`}
                onClick={() => setStatusFilter('VERIFIED_MUNICIPAL')}
              >
                DRF Verified
              </button>
              <button
                type="button"
                className={`chip ${statusFilter === 'RESOLVED' ? 'active' : ''}`}
                onClick={() => setStatusFilter('RESOLVED')}
              >
                Resolved
              </button>
            </div>

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="category-filter-select"
            >
              <option value="ALL">All Categories</option>
              {FLOOD_CATEGORIES.map(cat => (
                <option key={cat.value} value={cat.value}>{cat.label}</option>
              ))}
            </select>
          </div>

          {/* Incidents List */}
          <div className="incident-cards-scroll">
            {filteredIncidents.length === 0 ? (
              <div className="no-incidents-placeholder">
                <span className="placeholder-icon">🌊</span>
                <p>No reports match the selected filters.</p>
                <span className="placeholder-sub">
                  Be the first to report waterlogging or road submersion in this area.
                </span>
              </div>
            ) : (
              filteredIncidents.map(inc => {
                const incStatus = inc.verification_status || inc.status || 'PENDING_REVIEW'
                const incCat = inc.incident_category || inc.category || 'FLOOD_REPORT'
                const isVerified = incStatus === 'VERIFIED_MUNICIPAL'
                const isResolved = incStatus === 'RESOLVED'
                const isCorroborated = incStatus === 'COMMUNITY_CORROBORATED'
                const isRecedingObserved = incStatus === 'COMMUNITY_RESOLUTION_OBSERVED'
                const isPending = incStatus === 'PENDING_REVIEW'

                return (
                  <div key={inc.id} className={`incident-item-card ${incStatus.toLowerCase()}`}>
                    <div className="item-card-top">
                      <div className="item-id-and-cat">
                        <span className="item-incident-id">{inc.id}</span>
                        <span className="item-cat-badge">{incCat.replace(/_/g, ' ')}</span>
                      </div>
                      <div className="item-status-badges">
                        {isVerified && (
                          <span className="badge verified">
                            ✅ VERIFIED BY DRF
                          </span>
                        )}
                        {isPending && (
                          <span className="badge pending">
                            ⚠️ CITIZEN REPORT · UNVERIFIED
                          </span>
                        )}
                        {isCorroborated && (
                          <span className="badge corroborated" style={{ background: 'rgba(168,85,247,0.15)', color: '#c084fc', border: '1px solid rgba(168,85,247,0.3)', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold' }}>
                            👥 CORROBORATED
                          </span>
                        )}
                        {isRecedingObserved && (
                          <span className="badge receding" style={{ background: 'rgba(56,189,248,0.15)', color: '#38bdf8', border: '1px solid rgba(56,189,248,0.3)', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold' }}>
                            🌊 RECEDING OBSERVED
                          </span>
                        )}
                        {isResolved && (
                          <span className="badge resolved">
                            ✔️ RESOLVED
                          </span>
                        )}
                        <span className={`badge-severity ${inc.severity?.toLowerCase() || 'moderate'}`}>
                          {inc.severity || 'MODERATE'}
                        </span>
                      </div>
                    </div>

                    <div className="item-location-line">
                      📍 <strong>{inc.location_name || inc.address || 'Hyderabad'}</strong>
                      <span className="item-coords">
                        ({inc.latitude?.toFixed(4)}°N, {inc.longitude?.toFixed(4)}°E)
                      </span>
                    </div>

                    <p className="item-description">{inc.description}</p>

                    {inc.verification_note && (
                      <div className="item-verification-note">
                        <strong>Review Note:</strong> {inc.verification_note}
                      </div>
                    )}

                    <div className="item-card-footer">
                      <span className="item-meta">
                        🕒 {inc.created_at ? new Date(inc.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' }) : 'Recently'}
                        {inc.report_count > 1 && (
                          <span className="report-count-tag">
                            · {inc.report_count} correlated reports
                          </span>
                        )}
                      </span>

                      {/* Community Corroboration & Observation Actions */}
                      <div className="item-actions">
                        {!isResolved && (
                          <button
                            type="button"
                            disabled={updatingId === inc.id}
                            onClick={() => handleUpdateStatus(inc.id, 'COMMUNITY_CORROBORATED', 'Community corroboration: additional citizen observed active flooding.')}
                            className="btn-action verify"
                            title="Corroborate that this flood condition is active"
                          >
                            👍 Corroborate
                          </button>
                        )}
                        {!isResolved && !isRecedingObserved && (
                          <button
                            type="button"
                            disabled={updatingId === inc.id}
                            onClick={() => handleUpdateStatus(inc.id, 'COMMUNITY_RESOLUTION_OBSERVED', 'Citizen observation: floodwater observed receding or cleared.')}
                            className="btn-action resolve"
                            title="Report that floodwaters are receding or cleared (community observation)"
                          >
                            🌊 Report Receding
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
