import React from 'react'

export default function SOSModal({ isOpen, onClose }) {
  if (!isOpen) return null

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="sos-modal-title">
      <div className="modal-container">
        <div className="modal-header">
          <div className="modal-title-wrap">
            <span className="modal-icon-badge" aria-hidden="true">🚨</span>
            <div>
              <h2 id="sos-modal-title">Emergency Flood Assistance</h2>
              <p className="modal-subtitle">Official Emergency Contacts & Critical Safety Protocols</p>
            </div>
          </div>
          <button 
            type="button" 
            className="modal-close-btn" 
            onClick={onClose} 
            aria-label="Close emergency modal"
          >
            ✕
          </button>
        </div>

        <div className="modal-body">
          <div className="sos-disclaimer-box">
            <strong>⚠️ Prototype Notice:</strong> SafeMap AI is an academic decision-support prototype. In a live life-safety emergency, do NOT rely on this application. Immediately dial the official emergency numbers below.
          </div>

          <div className="sos-contact-grid">
            <div className="sos-contact-card emergency">
              <span className="contact-icon">📞</span>
              <div className="contact-details">
                <span className="contact-label">National Emergency (All-in-One)</span>
                <strong className="contact-number">112</strong>
              </div>
              <a href="tel:112" className="contact-call-btn">Call 112</a>
            </div>

            <div className="sos-contact-card">
              <span className="contact-icon">🌊</span>
              <div className="contact-details">
                <span className="contact-label">GHMC Disaster Response Force (DRF)</span>
                <strong className="contact-number">040-21111111</strong>
              </div>
              <a href="tel:04021111111" className="contact-call-btn">Call GHMC</a>
            </div>

            <div className="sos-contact-card">
              <span className="contact-icon">🚑</span>
              <div className="contact-details">
                <span className="contact-label">Telangana Emergency Ambulance</span>
                <strong className="contact-number">108</strong>
              </div>
              <a href="tel:108" className="contact-call-btn">Call 108</a>
            </div>

            <div className="sos-contact-card">
              <span className="contact-icon">👮</span>
              <div className="contact-details">
                <span className="contact-label">Telangana State Police</span>
                <strong className="contact-number">100</strong>
              </div>
              <a href="tel:100" className="contact-call-btn">Call 100</a>
            </div>

            <div className="sos-contact-card">
              <span className="contact-icon">📻</span>
              <div className="contact-details">
                <span className="contact-label">Emergency VHF Radio Channel</span>
                <strong className="contact-number">Channel 1 (146.520 MHz)</strong>
              </div>
              <span className="contact-badge">Civil Defense</span>
            </div>
          </div>

          <div className="sos-protocol-section">
            <h3>Immediate Flood Survival Rules</h3>
            <ul className="sos-protocol-list">
              <li><strong>Turn Around, Don't Drown:</strong> Just 15 cm (6 inches) of moving flood water can sweep an adult off their feet; 30 cm can float a vehicle.</li>
              <li><strong>Disconnect Power:</strong> Switch off main electricity and LPG cylinders if water enters your home.</li>
              <li><strong>Seek Higher Ground:</strong> If stranded, move to the top floor or terrace with drinking water and a flashlight. Do not climb into closed attics.</li>
              <li><strong>Avoid Drain Nalas:</strong> Stay clear of open drains, overflowing manholes, and stormwater channels (nalas).</li>
            </ul>
          </div>
        </div>

        <div className="modal-footer">
          <button type="button" className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}
