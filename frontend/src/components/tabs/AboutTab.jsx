import React from 'react'

export default function AboutTab() {
  return (
    <div className="tab-about">
      {/* Hero Overview */}
      <div className="card-panel about-hero-panel">
        <h2 className="panel-title">SafeMap AI — System Specifications & Data Provenance</h2>
        <p className="about-intro">
          SafeMap AI is an academic and engineering prototype engineered for flood decision-support, shelter recommendation, and graph-based evacuation routing in Hyderabad, Telangana.
        </p>
      </div>

      {/* Model Coverage Safeguard Explanation */}
      <div className="card-panel">
        <h3 className="section-title">1. The 50 km Model Coverage Safeguard</h3>
        <p>
          Unlike synthetic simulators, SafeMap AI refuses to fabricate machine learning predictions where valid training data does not exist.
        </p>
        <div className="about-callout warning">
          <strong>Why Hyderabad Returns <code>MODEL_UNSUPPORTED</code>:</strong>
          <p>
            The underlying Random Forest flood severity classifier is calibrated against the Indian INDOFLOODS streamflow gauge dataset under a strict 118-raw-feature contract. The model enforces a maximum allowable extrapolation distance of <strong>50.0 km</strong> from a calibrated physical gauge.
          </p>
          <p>
            The nearest calibrated INDOFLOODS station to Hyderabad is <strong>INDOFLOODS-gauge-916</strong> (River Manjra, Godavari Basin) located at <strong>71.77 km</strong>. Because the Musi River catchment lacks an official INDOFLOODS gauge, the system intentionally returns <code>MODEL_UNSUPPORTED</code> / <code>INSUFFICIENT_LOCAL_DATA</code> rather than producing ungrounded, fabricated numbers.
          </p>
        </div>
      </div>

      {/* Provenance Table */}
      <div className="card-panel">
        <h3 className="section-title">2. Ingested Data Sources & Provenance Matrix</h3>
        <div className="table-responsive">
          <table className="provenance-table">
            <thead>
              <tr>
                <th>Data Domain</th>
                <th>Source Entity</th>
                <th>Classification</th>
                <th>Ingestion Role</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Hydrological Model</strong></td>
                <td>INDOFLOODS Catchment Dataset</td>
                <td><span className="badge-verified">AUTHORITATIVE</span></td>
                <td>155 river gauges across India; catchment flood event training data.</td>
              </tr>
              <tr>
                <td><strong>Antecedent Rainfall</strong></td>
                <td>Open-Meteo Historical Archive</td>
                <td><span className="badge-model">MODELLED REANALYSIS</span></td>
                <td>10-day antecedent daily precipitation (T1d–T10d) at query coordinates.</td>
              </tr>
              <tr>
                <td><strong>Road Network Graph</strong></td>
                <td>OpenStreetMap Contributors</td>
                <td><span className="badge-osm">OPEN DATA (ODbL)</span></td>
                <td>NetworkX drive graph for Hyderabad shortest-path evacuation routing.</td>
              </tr>
              <tr>
                <td><strong>Emergency Shelters</strong></td>
                <td>GHMC / OSM Open Datasets</td>
                <td><span className="badge-unverified">PUBLIC_UNVERIFIED</span></td>
                <td>Geographic coordinates of candidate public shelters and hospitals.</td>
              </tr>
              <tr>
                <td><strong>Disaster Bulletins</strong></td>
                <td>NDMA SACHET / State SDMA</td>
                <td><span className="badge-verified">OFFICIAL_ALERT</span></td>
                <td>Common Alerting Protocol (CAP) emergency warning feeds.</td>
              </tr>
              <tr>
                <td><strong>River Stage Telemetry</strong></td>
                <td>Musi River Catchment Station</td>
                <td><span className="badge-demo">SIMULATED / DEMO</span></td>
                <td>Simulated water level (m) and discharge (m³/s) demonstration records.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Non-Negotiable Safety Invariants */}
      <div className="card-panel">
        <h3 className="section-title">3. Non-Negotiable Safety & Presentation Invariants</h3>
        <ul className="invariants-list">
          <li>
            <strong>No Fake Guarantees:</strong> Roads without intersecting hazard polygons are designated <em>"NO KNOWN HAZARD INTERSECTS THIS LOCATION"</em>. Unmonitored roads are never described as "confirmed clear" or "guaranteed safe".
          </li>
          <li>
            <strong>Truth in Facility Capacity:</strong> Hospital bed occupancies and structural safety ratings remain <code>PUBLIC_UNVERIFIED</code> until verified by state health officials.
          </li>
          <li>
            <strong>Detour vs Shortest Path:</strong> When roads intersect flood hazards, the system calculates a detour (<code>HAZARDS_AVOIDED</code>). If all access links are submerged, it returns <code>NO_SAFE_ROUTE</code> with explicit warnings.
          </li>
        </ul>
      </div>

      {/* Persistent Disclaimer */}
      <div className="card-panel disclaimer-card">
        <h3>Academic Prototype Legal Notice</h3>
        <p>
          SafeMap AI is an academic and engineering decision-support prototype. It is <strong>NOT</strong> an operational civil defense alert system or certified emergency navigation software. In any real-world monsoon disaster or flood situation, always defer strictly to official directives from the National Disaster Management Authority (NDMA), Telangana State Disaster Management Authority (TG-SDMA), Greater Hyderabad Municipal Corporation (GHMC), and local police.
        </p>
      </div>
    </div>
  )
}
