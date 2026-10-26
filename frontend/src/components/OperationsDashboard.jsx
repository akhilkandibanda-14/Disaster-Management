import React, { useState, useEffect } from 'react';
import { CircleMarker, MapContainer, Polygon, Polyline, Popup, TileLayer, ZoomControl, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';


const riskColors = {
  HIGH: '#ef4444',
  MEDIUM: '#f59e0b',
  LOW: '#10b981',
};

function MapAutoResizer({ routePositions }) {
  const map = useMap();

  useEffect(() => {
    if (!map) return;

    window._leaflet_map = map;
    map.invalidateSize({ pan: false });

    const t1 = setTimeout(() => map.invalidateSize({ pan: false }), 150);
    const t2 = setTimeout(() => map.invalidateSize({ pan: false }), 500);
    const t3 = setTimeout(() => map.invalidateSize({ pan: false }), 1200);

    const container = map.getContainer();
    let observer = null;
    if (typeof ResizeObserver !== 'undefined' && container) {
      observer = new ResizeObserver(() => {
        map.invalidateSize({ pan: false });
      });
      observer.observe(container);
      if (container.parentElement) {
        observer.observe(container.parentElement);
      }
    }

    const onResize = () => {
      map.invalidateSize({ pan: false });
    };
    window.addEventListener('resize', onResize);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      if (observer) observer.disconnect();
      window.removeEventListener('resize', onResize);
    };
  }, [map]);

  useEffect(() => {
    if (!map) return;
    if (routePositions && routePositions.length > 1) {
      try {
        map.fitBounds(routePositions, { padding: [40, 40], maxZoom: 14 });
      } catch {
        // Safe fallback
      }
    }
  }, [map, routePositions]);

  return null;
}

function MapTileLayer({ onTileErrorChange }) {
  const map = useMap();

  useEffect(() => {
    if (!map) return;
    let errCount = 0;
    let timer = null;

    const onTileError = () => {
      errCount += 1;
      if (errCount >= 3) {
        if (onTileErrorChange) onTileErrorChange(true);
      }
    };

    const onTileLoad = () => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        errCount = 0;
        if (onTileErrorChange) onTileErrorChange(false);
      }, 600);
    };

    map.on('tileerror', onTileError);
    map.on('tileload', onTileLoad);

    return () => {
      map.off('tileerror', onTileError);
      map.off('tileload', onTileLoad);
      if (timer) clearTimeout(timer);
    };
  }, [map, onTileErrorChange]);

  return (
    <TileLayer
      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      maxZoom={19}
    />
  );
}

function MapClickHandler({ onLocationSelect }) {
  useMapEvents({
    click(e) {
      if (onLocationSelect) {
        onLocationSelect({ latitude: e.latlng.lat, longitude: e.latlng.lng });
      }
    }
  });
  return null;
}

function OperationsMap({ riskData, location, route, gauges, facilities, roads, floodHazards, onLocationSelect }) {
  const [hasTileError, setHasTileError] = useState(false);
  const center = [(17.2 + 17.6) / 2, (78.2 + 78.7) / 2];
  const routePositions = route?.geometry?.map(([longitude, latitude]) => [latitude, longitude]) ?? [];
  const isDetour = route?.is_rerouted || route?.road_condition_status === 'HAZARDS_AVOIDED';

  const handleRetry = () => {
    setHasTileError(false);
    if (window._leaflet_map) {
      window._leaflet_map.eachLayer((layer) => {
        if (layer && typeof layer.redraw === 'function') {
          layer.redraw();
        }
      });
      window._leaflet_map.invalidateSize({ pan: false });
    }
  };

  return (
    <>
      <MapContainer className="leaflet-map" center={center} zoom={11} scrollWheelZoom zoomControl={false}>
        <ZoomControl position="topright" />
        <MapAutoResizer routePositions={routePositions} />
        <MapTileLayer onTileErrorChange={setHasTileError} />
        <MapClickHandler onLocationSelect={onLocationSelect} />
      
      {/* Flood Hazard Zones (Polygons) */}
      {floodHazards && floodHazards.map((hazard) => {
        const isAuth = hazard.data_status === 'AUTHORITATIVE';
        const isDemo = hazard.data_status === 'DEMO';
        const isStale = hazard.data_status === 'STALE' || hazard.is_stale;

        let strokeColor = '#f59e0b';
        let fillColor = '#f59e0b';
        let fillOpacity = 0.22;
        let dashArray = '6, 6';

        if (isAuth) {
          strokeColor = '#ef4444';
          fillColor = '#ef4444';
          fillOpacity = 0.35;
          dashArray = undefined;
        } else if (isDemo) {
          strokeColor = '#c084fc';
          fillColor = '#c084fc';
          fillOpacity = 0.25;
          dashArray = '4, 4';
        } else if (isStale) {
          strokeColor = '#64748b';
          fillColor = '#64748b';
          fillOpacity = 0.15;
          dashArray = '4, 4';
        }

        if (hazard.geometry?.type === 'Polygon' && hazard.geometry.coordinates?.[0]) {
          const latLngs = hazard.geometry.coordinates[0].map(([lon, lat]) => [lat, lon]);
          return (
            <Polygon
              key={hazard.hazard_id}
              positions={latLngs}
              pathOptions={{
                color: strokeColor,
                fillColor: fillColor,
                fillOpacity: fillOpacity,
                weight: isAuth ? 2.5 : 2,
                dashArray: dashArray
              }}
            >
              <Popup>
                <div style={{ minWidth: '220px' }}>
                  <strong>{hazard.title}</strong>
                  <div style={{ fontSize: '11px', margin: '3px 0' }}>
                    <span style={{ color: strokeColor, fontWeight: 'bold' }}>{hazard.data_status}</span> · {hazard.severity}
                  </div>
                  <p style={{ fontSize: '12px', margin: '4px 0' }}>{hazard.description}</p>
                  <small style={{ color: '#94a3b8' }}>Source: {hazard.source_name}</small>
                </div>
              </Popup>
            </Polygon>
          );
        }
        return null;
      })}

      {/* Risk Point */}
      {riskData && riskData.prediction_available && riskData.risk_level && (
        <CircleMarker
          center={[riskData.latitude, riskData.longitude]}
          pathOptions={{ 
            color: riskColors[riskData.risk_level] || '#94a3b8', 
            fillColor: riskColors[riskData.risk_level] || '#94a3b8', 
            fillOpacity: 0.35, 
            weight: 2 
          }}
          radius={40}
        >
          <Popup>Selected Location: {riskData.risk_level} risk</Popup>
        </CircleMarker>
      )}

      {/* Selected Location */}
      <CircleMarker center={[location.latitude, location.longitude]} pathOptions={{ color: '#0ea5e9', fillColor: '#0ea5e9', fillOpacity: 1, weight: 3 }} radius={7}>
        <Popup>Selected Location</Popup>
      </CircleMarker>
      
      {/* Route */}
      {routePositions.length > 1 && (
        <Polyline 
          positions={routePositions} 
          pathOptions={{ 
            color: isDetour ? '#f59e0b' : '#38bdf8', 
            weight: 4, 
            opacity: 0.85,
            dashArray: isDetour ? '6, 6' : undefined
          }} 
        />
      )}
      
      {/* Official Gauges */}
      {gauges && gauges.map(gauge => (
        <CircleMarker 
          key={gauge.id} 
          center={[gauge.latitude, gauge.longitude]} 
          pathOptions={{ color: '#f97316', fillColor: '#f97316', fillOpacity: 0.8, weight: 2 }} 
          radius={5}
        >
          <Popup>Official Gauge: {gauge.id}</Popup>
        </CircleMarker>
      ))}

      {/* Reported Road Hazards / Blockages */}
      {roads && roads.map((road, idx) => {
        const isHazard = ['FLOODED', 'BLOCKED', 'DANGEROUS'].includes(road.status?.toUpperCase());
        if (!isHazard) return null;
        return (
          <CircleMarker
            key={`op-hazard-${idx}`}
            center={[road.latitude, road.longitude]}
            pathOptions={{ color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.85, weight: 2 }}
            radius={5}
          >
            <Popup>
              <strong>Hazard ({road.status}): {road.road_name}</strong>
              <p style={{ margin: '2px 0', fontSize: '11px' }}>{road.notes || 'Flooded/blocked segment'}</p>
            </Popup>
          </CircleMarker>
        );
      })}

      {/* Emergency Facilities & Shelters */}
      {facilities && facilities.map(fac => {
        const isHospital = fac.facility_type === 'HOSPITAL';
        const color = isHospital ? '#a855f7' : '#10b981';
        return (
          <CircleMarker 
            key={fac.facility_id || fac.id || `${fac.name}-${fac.latitude}-${fac.longitude}`} 
            center={[fac.latitude, fac.longitude]} 
            pathOptions={{ color, fillColor: color, fillOpacity: 0.65, weight: 1 }} 
            radius={isHospital ? 6 : 4}
          >
            <Popup>
              <strong>{fac.name}</strong>
              <div style={{ fontSize: '11px', marginTop: '2px' }}>
                Type: <b>{fac.facility_type}</b> · Status: <b>{fac.data_status || 'PUBLIC_UNVERIFIED'}</b>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
      </MapContainer>
      {hasTileError && (
        <div className="map-tile-error-banner" role="alert">
          <span>⚠️ Basemap tile provider issue detected. Map data may be degraded.</span>
          <button type="button" onClick={handleRetry} className="map-tile-retry-btn">
            Retry Tiles
          </button>
        </div>
      )}
    </>
  );
}

export default function OperationsDashboard({
  apiBaseUrl = 'http://127.0.0.1:8000',
  apiStatus,
  weather,
  riskData,
  shelters,
  facilities,
  roads,
  location,
  route,
  gauges,
  hydrology,
  alerts,
  floodHazards,
  hazardWarning,
  onLocationSelect
}) {
  const [historicalEvents, setHistoricalEvents] = useState([]);
  const [readinessAudit, setReadinessAudit] = useState(null);
  const [sourcesInventory, setSourcesInventory] = useState(null);
  const [intakeLog, setIntakeLog] = useState([]);
  const [negativeControlSummary, setNegativeControlSummary] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [apiKey, setApiKey] = useState(() => {
    try {
      return sessionStorage.getItem('safemap_operator_key') || '';
    } catch {
      return '';
    }
  });
  const [validatorInput, setValidatorInput] = useState(
    'timestamp,station_id,latitude,longitude,rainfall,rainfall_unit,discharge,discharge_unit\n2020-10-14T08:00:00Z,TSDPS-GHATKESAR,17.442,78.682,320.0,mm,850.0,m^3/s\n2020-10-14T08:00:00Z,TSDPS-BEGUMPET,17.442,78.475,19.18,cm,12000,cusec'
  );
  const [validationResult, setValidationResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState(null);
  const [verifyFacilityId, setVerifyFacilityId] = useState('');
  const [verifyEvidence, setVerifyEvidence] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationFeedback, setVerificationFeedback] = useState(null);

  const handleApiKeyChange = (val) => {
    setApiKey(val);
    try {
      sessionStorage.setItem('safemap_operator_key', val);
    } catch (e) {
      console.warn('Could not store key in sessionStorage:', e);
    }
  };

  const getAuthHeaders = () => {
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey && apiKey.trim()) {
      headers['X-API-Key'] = apiKey.trim();
    }
    return headers;
  };

  useEffect(() => {
    fetch(`${apiBaseUrl}/health`)
      .then(res => res.ok ? res.json() : null)
      .then(data => setHealthData(data))
      .catch(err => console.error('Failed to load system health:', err));

    fetch(`${apiBaseUrl}/data-curation/historical-events`)
      .then(res => res.ok ? res.json() : [])
      .then(data => setHistoricalEvents(data))
      .catch(err => console.error('Failed to load historical events:', err));

    fetch(`${apiBaseUrl}/data-curation/readiness-audit`)
      .then(res => res.ok ? res.json() : null)
      .then(data => setReadinessAudit(data))
      .catch(err => console.error('Failed to load readiness audit:', err));

    fetch(`${apiBaseUrl}/data-curation/intake/sources`, { headers: getAuthHeaders() })
      .then(res => res.ok ? res.json() : null)
      .then(data => setSourcesInventory(data))
      .catch(err => console.error('Failed to load intake sources:', err));

    fetch(`${apiBaseUrl}/data-curation/intake/log`, { headers: getAuthHeaders() })
      .then(res => res.ok ? res.json() : [])
      .then(data => setIntakeLog(data))
      .catch(err => console.error('Failed to load intake log:', err));

    fetch(`${apiBaseUrl}/data-curation/negative-controls/summary`)
      .then(res => res.ok ? res.json() : null)
      .then(data => setNegativeControlSummary(data))
      .catch(err => console.error('Failed to load negative control summary:', err));
  }, [apiBaseUrl, apiKey]);

  const handleRunValidation = () => {
    setIsValidating(true);
    setCommitResult(null);
    fetch(`${apiBaseUrl}/data-curation/intake/validate`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        filename: 'manual_intake_test.csv',
        content: validatorInput,
        metadata: {
          provider: 'TSDPS',
          source_reference: 'TELEMETRY-REQUISITION-M8',
          retrieval_date: '2026-10-25T00:00:00Z',
          data_owner: 'Telangana State Development Planning Society',
          usage_restrictions: 'RESTRICTED_RESEARCH_ONLY',
          measurement_classification: 'OBSERVED'
        }
      })
    })
      .then(async res => {
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || `Validation rejected (HTTP ${res.status})`);
        }
        return data;
      })
      .then(data => {
        setValidationResult(data);
        setIsValidating(false);
      })
      .catch(err => {
        setValidationResult({ valid: false, errors: [{ field: 'authentication_or_network', error: String(err.message || err) }] });
        setIsValidating(false);
      });
  };

  const handleCommitBatch = () => {
    if (!validationResult || !validationResult.valid) return;
    setIsCommitting(true);
    setCommitResult(null);

    fetch(`${apiBaseUrl}/data-curation/intake/commit`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        filename: 'manual_intake_test.csv',
        content: validatorInput,
        metadata: {
          provider: 'TSDPS',
          source_reference: 'TELEMETRY-REQUISITION-M8',
          retrieval_date: '2026-10-25T00:00:00Z',
          data_owner: 'Telangana State Development Planning Society',
          usage_restrictions: 'RESTRICTED_RESEARCH_ONLY',
          measurement_classification: 'OBSERVED'
        }
      })
    })
      .then(async res => {
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || `Batch commit rejected (HTTP ${res.status})`);
        }
        return data;
      })
      .then(data => {
        setCommitResult({ success: true, data });
        setIsCommitting(false);
        // Refresh log
        fetch(`${apiBaseUrl}/data-curation/intake/log`, { headers: getAuthHeaders() })
          .then(r => r.ok ? r.json() : [])
          .then(log => setIntakeLog(log));
      })
      .catch(err => {
        setCommitResult({ success: false, error: err.message });
        setIsCommitting(false);
      });
  };

  const handlePromoteVerification = (facilityId) => {
    if (!facilityId) return;
    if (!verifyEvidence || verifyEvidence.trim().length < 5) {
      setVerificationFeedback({ success: false, error: 'Documented evidence citation is mandatory (min 5 characters).' });
      return;
    }
    setIsVerifying(true);
    setVerificationFeedback(null);

    fetch(`${apiBaseUrl}/emergency-facilities/${encodeURIComponent(facilityId)}/verify`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        data_status: 'VERIFIED',
        operational_status_verified: true,
        capacity_verified: true,
        operational_status: 'OPERATIONAL',
        verification_evidence_source: verifyEvidence.trim(),
        verification_note: 'Verified via operator promotion terminal'
      })
    })
      .then(async res => {
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || `Verification promotion failed (HTTP ${res.status})`);
        }
        return data;
      })
      .then(data => {
        setVerificationFeedback({ success: true, facility: data });
        setIsVerifying(false);
      })
      .catch(err => {
        setVerificationFeedback({ success: false, error: err.message });
        setIsVerifying(false);
      });
  };

  const allFacilities = facilities && facilities.length > 0 ? facilities : (shelters || []);
  const hospitalsCount = allFacilities.filter(f => f.facility_type === 'HOSPITAL').length;
  const sheltersCount = allFacilities.filter(f => f.facility_type === 'SHELTER' || !f.facility_type).length;
  const verifiedCount = allFacilities.filter(s => s.data_status === 'VERIFIED').length;
  const unverifiedCount = allFacilities.length - verifiedCount;
  const blockedRoadsCount = (roads || []).filter(r => ['FLOODED', 'BLOCKED', 'DANGEROUS'].includes(r.status?.toUpperCase())).length;
  const activeHazardsCount = (floodHazards || []).length;
  const authoritativeHazardsCount = (floodHazards || []).filter(h => h.data_status === 'AUTHORITATIVE').length;

  return (
    <section className="operations-view">
      <div className="operations-heading" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <p className="eyebrow">SAFEMAP AI · OPERATIONS CONTROL</p>
          <h2>Operations Dashboard</h2>
        </div>
        {/* Operator RBAC Authentication Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255,255,255,0.1)', padding: '6px 12px', borderRadius: '8px' }}>
          <span style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 'bold' }}>OPERATOR KEY:</span>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => handleApiKeyChange(e.target.value)}
            placeholder="Admin or Analyst Key"
            style={{
              background: 'rgba(0,0,0,0.5)',
              border: '1px solid rgba(255,255,255,0.15)',
              color: '#f8fafc',
              fontSize: '11px',
              padding: '4px 8px',
              borderRadius: '4px',
              width: '160px'
            }}
          />
          {apiKey ? (
            <button
              onClick={() => handleApiKeyChange('')}
              style={{ fontSize: '10px', padding: '3px 8px', background: 'rgba(239,68,68,0.2)', color: '#f87171', border: '1px solid rgba(239,68,68,0.4)', borderRadius: '4px', cursor: 'pointer' }}
            >
              Clear
            </button>
          ) : (
            <span style={{ fontSize: '10px', color: '#cbd5e1', fontStyle: 'italic' }}>Public Mode</span>
          )}
        </div>
      </div>

      <div className="operations-metrics" style={{ marginBottom: '24px' }}>
        <article className="metric-card">
          <span>SYSTEM STATUS</span>
          <strong style={{ fontSize: '1.5rem', marginTop: '12px', color: apiStatus.includes('online') ? 'var(--success)' : 'var(--danger)' }}>
            {apiStatus.includes('online') ? 'API ONLINE' : 'API OFFLINE'}
          </strong>
          <small>ML Model: INDOFLOODS flood severity model</small>
          <small style={{display: 'block'}}>Feature contract: 118 raw, 130 processed</small>
        </article>

        <article className="metric-card">
          <span>FEED OBSERVABILITY</span>
          <strong style={{ fontSize: '1.5rem', marginTop: '12px', color: healthData?.external_feeds?.weather?.is_stale ? '#fbbf24' : 'var(--success)' }}>
            {healthData?.external_feeds?.weather?.status || 'OPERATIONAL'}
          </strong>
          <small>Road Graph: {healthData?.external_feeds?.road_network?.status || 'LOADED'}</small>
          <small style={{display: 'block', color: healthData?.external_feeds?.weather?.is_stale ? '#fbbf24' : '#38bdf8'}}>
            Weather: {healthData?.external_feeds?.weather?.is_stale ? 'STALE (>3h)' : (healthData?.external_feeds?.weather?.is_simulated ? 'DEMO SIMULATED' : 'LIVE')}
          </small>
        </article>

        <article className="metric-card">
          <span>EMERGENCY FACILITIES</span>
          <strong style={{ fontSize: '1.5rem', marginTop: '12px' }}>{allFacilities.length}</strong>
          <small>Hospitals: {hospitalsCount} · Shelters: {sheltersCount}</small>
          <small style={{display: 'block', color: 'var(--warning)'}}>Unverified: {unverifiedCount} (Public listings)</small>
        </article>

        <article className="metric-card">
          <span>ACTIVE ROAD HAZARDS</span>
          <strong style={{ fontSize: '1.5rem', marginTop: '12px', color: blockedRoadsCount > 0 ? '#ef4444' : 'var(--success)' }}>
            {blockedRoadsCount}
          </strong>
          <small>Hazard-Aware Routing: ACTIVE</small>
          <small style={{display: 'block'}}>Excluded by router automatically</small>
        </article>

        <article className="metric-card">
          <span>FLOOD HAZARD ZONES</span>
          <strong style={{ fontSize: '1.5rem', marginTop: '12px', color: authoritativeHazardsCount > 0 ? '#ef4444' : '#f59e0b' }}>
            {activeHazardsCount}
          </strong>
          <small>Authoritative: {authoritativeHazardsCount} · Municipal: {activeHazardsCount - authoritativeHazardsCount}</small>
          <small style={{display: 'block'}}>NDMA / GloFAS / GHMC</small>
        </article>

        <article className="metric-card warning">
          <span>LOCAL DATA READINESS</span>
          <strong style={{ fontSize: '1.5rem', marginTop: '12px', color: '#fca5a5' }}>INSUFFICIENT</strong>
          <small>50 km Guard Enforced · Musi Telemetry Absent</small>
          <small style={{display: 'block', color: '#38bdf8'}}>Curated Events: {historicalEvents.length || 8}</small>
        </article>
      </div>

      <div className="workspace-grid">
        <div className="map-panel">
          <OperationsMap 
            riskData={riskData} 
            location={location} 
            route={route} 
            gauges={gauges} 
            facilities={allFacilities} 
            roads={roads}
            floodHazards={floodHazards}
            onLocationSelect={onLocationSelect} 
          />
          <div className="map-legend">
            <span><i className="legend-dot user" />Selected</span>
            <span><i className="legend-dot" style={{backgroundColor: '#f97316'}} />Official Gauge</span>
            <span><i className="legend-dot safe" style={{backgroundColor: '#10b981'}} />Shelter</span>
            <span><i className="legend-dot" style={{backgroundColor: '#a855f7'}} />Hospital</span>
            <span><i className="legend-dot" style={{backgroundColor: '#ef4444'}} />Road Hazard</span>
            <span><i className="legend-dot" style={{backgroundColor: '#ef4444', border: '1px solid #fff'}} />Live Alert</span>
            <span><i className="legend-dot" style={{backgroundColor: '#f59e0b'}} />Flood Zone</span>
            <span><i className="legend-dot route" style={{backgroundColor: '#38bdf8'}} />OSM Route</span>
            <span><i className="legend-dot" style={{backgroundColor: '#f59e0b'}} />Hazard Detour</span>
          </div>
        </div>

        <aside className="side-panel">
          <article className="info-card">
            <p className="card-label">RISK / PREDICTION OVERVIEW</p>
            {riskData ? (
              riskData.prediction_available ? (
                <>
                  <div className="metric-row">
                    <strong style={{fontSize: '1.2rem'}}>Flood prediction available</strong>
                  </div>
                  <p className="muted" style={{color: 'white', marginTop: '8px'}}>Risk level: {riskData.risk_level}</p>
                  {riskData.probability !== undefined && riskData.probability !== null && (
                    <p className="muted">Model severe-flood probability: {(riskData.probability * 100).toFixed(1)}%</p>
                  )}
                  <p className="muted" style={{fontSize: '0.85em', marginTop: '8px'}}>Model: INDOFLOODS</p>
                </>
              ) : (
                <>
                  <div className="metric-row">
                    <strong style={{fontSize: '1.2rem', color: 'var(--warning)'}}>
                      {riskData.data_readiness_status || riskData.coverage_status}
                    </strong>
                    <span style={{ fontSize: '10px', background: 'rgba(59,130,246,0.2)', color: '#93c5fd', padding: '1px 5px', borderRadius: '3px' }}>
                      OPERATIONAL
                    </span>
                  </div>
                  <div style={{ marginTop: '8px', padding: '6px 8px', background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: '4px' }}>
                    <p style={{ margin: 0, fontSize: '10.5px', color: '#93c5fd', lineHeight: '1.3' }}>
                      ℹ️ <strong>System Operational:</strong> Prediction is suppressed due to insufficient local hydrological evidence (coverage guard), not a system error or software defect.
                    </p>
                  </div>
                  <p className="muted" style={{ fontSize: '12px', color: '#fca5a5', marginTop: '6px', lineHeight: '1.4' }}>
                    {riskData.provenance_note || 'Flood prediction unavailable: Outside INDOFLOODS coverage.'}
                  </p>
                  <div style={{ marginTop: '6px', fontSize: '11px', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <div>• Nearest INDOFLOODS gauge: <strong>{riskData.gauge_id || 'INDOFLOODS-gauge-916'} ({riskData.distance_km} km)</strong></div>
                    <div>• Model coverage limit: <strong>{riskData.coverage_limit_km || 50.0} km</strong></div>
                    <div>• INDOFLOODS gauges within 50 km: <strong>{riskData.gauges_within_50km_count ?? riskData.catchment_gauges_count ?? 0}</strong></div>
                    <div>• Prediction status: <strong style={{ color: '#fde047' }}>{riskData.data_readiness_status || 'INSUFFICIENT_LOCAL_DATA'}</strong></div>
                  </div>
                  {riskData.safety_disclaimer && (
                    <div style={{ marginTop: '8px', padding: '6px 8px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '4px' }}>
                      <p style={{ margin: 0, fontSize: '10.5px', color: '#fca5a5', lineHeight: '1.3' }}>
                        ⚠️ <strong>Safety Notice (Distinguish from Low-Risk):</strong> {riskData.safety_disclaimer}
                      </p>
                    </div>
                  )}
                </>
              )
            ) : (
              <p className="muted">Select a location.</p>
            )}
            <div style={{marginTop: "16px", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "12px"}}>
              <p className="muted" style={{fontSize: '0.85em', margin: 0}}>
                Source: {weather?.source || 'Open-Meteo Historical/Reanalysis'}<br/>
                {weather?.condition ?? 'Weather data unavailable'} · {
                  !weather ? 'Rainfall data unavailable' : 
                  (weather.rainfall == null ? 'Rainfall data unavailable' : `${weather.rainfall} mm`)
                }
              </p>
              {weather?.warning && (
                <p style={{ margin: '4px 0 0', fontSize: '10px', color: '#fde047' }}>
                  ⚠️ {weather.warning}
                </p>
              )}
            </div>
          </article>

          <article className="info-card">
            <p className="card-label">ROADS & HAZARD ROUTING</p>
            <div className="metric-row">
              <strong style={{fontSize: '1.2rem'}}>OSM Graph + Hazard Exclusion</strong>
            </div>
            {route ? (
              <div style={{marginTop: '12px'}}>
                {route.route_status === 'NO_SAFE_ROUTE' ? (
                  <div style={{ padding: '8px', background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)', borderRadius: '6px' }}>
                    <strong style={{ color: '#ef4444', fontSize: '13px' }}>🚨 NO SAFE ROUTE AVAILABLE</strong>
                    <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#fca5a5' }}>
                      All paths traverse reported flooded/blocked road segments.
                    </p>
                  </div>
                ) : (
                  <>
                    <p className="muted" style={{margin: '4px 0'}}>
                      Status: <strong>{route.route_status}</strong>
                    </p>
                    <p className="muted" style={{margin: '4px 0'}}>
                      Distance: <strong>{route.route_distance_km?.toFixed(2) ?? '?'} km</strong>
                    </p>
                    <p className="muted" style={{margin: '4px 0'}}>
                      Road condition: <strong style={{ color: route.road_condition_status === 'HAZARDS_AVOIDED' ? '#f59e0b' : '#38bdf8' }}>
                        {route.road_condition_status}
                      </strong>
                    </p>
                    {route.is_rerouted && (
                      <p style={{ color: '#f59e0b', fontSize: '12px', margin: '4px 0', fontWeight: 'bold' }}>
                        Detour recalculated around reported hazards.
                      </p>
                    )}
                  </>
                )}
              </div>
            ) : (
              <p className="muted" style={{marginTop: '8px'}}>No active route evaluated.</p>
            )}
            <div style={{marginTop: "12px", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "8px"}}>
              <p className="muted" style={{margin: '2px 0', fontSize: '0.85em'}}>Network: Hyderabad Drive MultiDiGraph</p>
              <p className="muted" style={{margin: '2px 0', fontSize: '0.85em'}}>Hazard Exclusion: ACTIVE (nx.restricted_view)</p>
              <p className="muted" style={{margin: '2px 0', fontSize: '0.85em'}}>Live Traffic: NOT INTEGRATED</p>
            </div>
          </article>
        </aside>
      </div>

      {/* Operations Panels: Historical Flood Events & Data Readiness */}
      <div className="operations-grid" style={{ marginTop: '24px' }}>
        <article className="operations-panel">
          <div className="panel-heading" style={{flexDirection: 'column', alignItems: 'flex-start'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', width: '100%', marginBottom: '4px', flexWrap: 'wrap', gap: '8px'}}>
              <h3>Hyderabad Historical Flood Catalogue (1908–2023)</h3>
              <div style={{ display: 'flex', gap: '6px' }}>
                <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', background: 'rgba(245, 158, 11, 0.18)', color: '#f59e0b', border: '1px solid rgba(245, 158, 11, 0.4)', fontWeight: 'bold' }}>
                  8 Audited Events · 8 Partially Verified · 0 Fully Verified
                </span>
              </div>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: 0 }}>
              Milestone 7 Evidence Audit: Distinguishing physical observations, secondary reports, hydraulic dam estimates, and unsupported claims.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', padding: '12px 16px', maxHeight: '520px', overflowY: 'auto' }}>
            {historicalEvents.map(ev => {
              const isObs = ev.data_classification === 'OBSERVATION';
              const isInundation = ev.data_classification === 'HISTORICAL_INUNDATION';
              const isAlert = ev.data_classification === 'OFFICIAL_ALERT';
              const badgeColor = isObs ? '#34d399' : (isInundation ? '#c084fc' : (isAlert ? '#38bdf8' : '#94a3b8'));

              const rainTypeColor = ev.rainfall_measurement_type === 'OBSERVED' ? '#34d399' : '#38bdf8';
              const dischargeTypeColor = ev.discharge_measurement_type === 'ESTIMATED' ? '#f59e0b' : (ev.discharge_measurement_type === 'MODELLED' ? '#c084fc' : '#ef4444');

              return (
                <div 
                  key={ev.event_id} 
                  style={{
                    padding: '12px 14px',
                    borderRadius: '8px',
                    background: 'rgba(255,255,255,0.025)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                    <strong style={{ fontSize: '13.5px', color: '#f1f5f9' }}>{ev.event_name}</strong>
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                      <span style={{
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: `${badgeColor}22`,
                        color: badgeColor,
                        fontWeight: 'bold',
                        border: `1px solid ${badgeColor}55`
                      }}>
                        {ev.data_classification}
                      </span>
                      <span style={{
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: 'rgba(245, 158, 11, 0.15)',
                        color: '#fbbf24',
                        fontWeight: '600',
                        border: '1px solid rgba(245, 158, 11, 0.35)'
                      }}>
                        {ev.verification_state || 'PARTIALLY_VERIFIED'}
                      </span>
                      <span style={{
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: 'rgba(148, 163, 184, 0.15)',
                        color: '#cbd5e1',
                        border: '1px solid rgba(148, 163, 184, 0.3)'
                      }}>
                        Conf: {ev.confidence_level}
                      </span>
                    </div>
                  </div>

                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                    <strong>Date:</strong> {ev.start_date_iso?.slice(0, 10)} · <strong>Type:</strong> {ev.flood_type}
                  </div>

                  {/* Physical Telemetry / Measurement Row */}
                  <div style={{ display: 'flex', gap: '14px', fontSize: '11.5px', marginTop: '2px', flexWrap: 'wrap', background: 'rgba(0,0,0,0.2)', padding: '6px 8px', borderRadius: '4px' }}>
                    {ev.max_24h_rainfall_mm != null && (
                      <span style={{ color: '#38bdf8' }}>
                        Rain: <b>{ev.max_24h_rainfall_mm} mm</b> ({ev.rainfall_station}){' '}
                        <span style={{ fontSize: '9.5px', padding: '1px 4px', borderRadius: '3px', background: `${rainTypeColor}22`, color: rainTypeColor, border: `1px solid ${rainTypeColor}44` }}>
                          {ev.rainfall_measurement_type || 'OBSERVED'}
                        </span>
                      </span>
                    )}

                    {ev.peak_river_discharge_cumec != null ? (
                      <span style={{ color: '#f59e0b' }}>
                        Discharge: <b>{ev.peak_river_discharge_cumec} m³/s</b>{' '}
                        <span style={{ fontSize: '9.5px', padding: '1px 4px', borderRadius: '3px', background: `${dischargeTypeColor}22`, color: dischargeTypeColor, border: `1px solid ${dischargeTypeColor}44` }}>
                          {ev.discharge_measurement_type || 'ESTIMATED'}
                        </span>
                      </span>
                    ) : (
                      <span style={{ color: '#94a3b8' }}>
                        Discharge: <i style={{ color: '#f87171' }}>Null (No Stream Gauge Telemetry)</i>{' '}
                        <span style={{ fontSize: '9.5px', padding: '1px 4px', borderRadius: '3px', background: 'rgba(239,68,68,0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' }}>
                          {ev.discharge_measurement_type || 'UNVERIFIED'}
                        </span>
                      </span>
                    )}
                  </div>

                  {/* Evidence Note & Provenance */}
                  {ev.provenance?.evidence_note && (
                    <div style={{ fontSize: '11px', color: '#cbd5e1', background: 'rgba(30, 41, 59, 0.4)', padding: '6px 8px', borderRadius: '4px', borderLeft: '3px solid #38bdf8' }}>
                      <strong style={{ color: '#38bdf8' }}>Evidence Note: </strong>
                      {ev.provenance.evidence_note}
                    </div>
                  )}

                  {/* Audit Trail Correction */}
                  {ev.audit_trail?.correction_rationale && (
                    <div style={{ fontSize: '10.5px', color: '#fbbf24', background: 'rgba(245, 158, 11, 0.08)', padding: '4px 8px', borderRadius: '4px', borderLeft: '3px solid #f59e0b' }}>
                      <strong>Audit Trail: </strong>
                      {ev.audit_trail.correction_rationale}
                      {ev.audit_trail.original_reported_discharge_cumec && (
                        <span> (Prior unverified discharge: {ev.audit_trail.original_reported_discharge_cumec} m³/s preserved in audit trail).</span>
                      )}
                    </div>
                  )}

                  {/* Citation & Source Info */}
                  <div style={{ fontSize: '10px', color: '#64748b', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '4px' }}>
                    <span>Source: {ev.provenance?.source_title || ev.source_agency}</span>
                    {ev.provenance?.direct_url && (
                      <a 
                        href={ev.provenance.direct_url} 
                        target="_blank" 
                        rel="noreferrer" 
                        style={{ color: '#38bdf8', textDecoration: 'underline' }}
                      >
                        Source Document Link ↗
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </article>

        <article className="operations-panel">
          <div className="panel-heading"><h3>Local Data Readiness & Statistical Audit</h3></div>
          <div style={{padding: '20px', lineHeight: '1.5', color: 'var(--text-muted)', fontSize: '12.5px'}}>
            <div style={{ padding: '10px 12px', background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '6px', marginBottom: '14px' }}>
              <strong style={{ color: '#f87171', display: 'block', marginBottom: '4px', fontSize: '13px' }}>
                STATUS: INSUFFICIENT_LOCAL_DATA (MODEL_UNSUPPORTED)
              </strong>
              <span>
                Automated predictive models are suppressed for Hyderabad. Successful data import must never be confused with model readiness.
              </span>
            </div>

            <p style={{ margin: '6px 0' }}>
              <strong>50 km Coverage Guard:</strong> Nearest INDOFLOODS gauge is <strong>INDOFLOODS-gauge-916 at 71.77 km</strong> (Singur Dam). Exceeds the 50.0 km model-coverage boundary.
            </p>
            <p style={{ margin: '6px 0' }}>
              <strong>Catchment Basin Disconnection:</strong> Nearest gauge monitors River Manjra in the <em>Godavari Basin</em>, whereas Hyderabad lies in the <em>Musi River (Krishna Basin)</em>.
            </p>
            <p style={{ margin: '6px 0' }}>
              <strong>Statistical Power Limit:</strong> Curated N=8 sample size yields Wilson 95% Confidence Interval width of <strong>51.9%</strong>. Statistical power is &lt; 0.12, rendering machine learning validation statistically indefensible.
            </p>
            <p style={{ margin: '6px 0' }}>
              <strong>Exploratory Heuristic Disclaimer:</strong> The 120 mm rainfall baseline is strictly an exploratory retrospective heuristic, NOT a predictive model or operational hydrological threshold.
            </p>
            <p style={{ margin: '6px 0' }}>
              <strong>Undefined Specificity:</strong> Because the catalogue records positive flood events without negative control non-flood days, false positive rate and specificity cannot be measured.
            </p>
            <p style={{ margin: '6px 0' }}>
              <strong>Missing Continuous Telemetry:</strong> Musi River lacks open continuous river stage telemetry; discharges are episodic dam gate outflow conversions or hydraulic slope-area calculations.
            </p>

            <hr style={{borderColor: 'rgba(255,255,255,0.08)', margin: '12px 0'}} />
            <strong style={{ color: '#cbd5e1', fontSize: '12px' }}>Required Before Local Modeling:</strong>
            <ul style={{ margin: '6px 0 0 0', paddingLeft: '18px', fontSize: '11px', color: '#94a3b8' }}>
              <li>TSDPS AWS 15-minute raw telemetry data-sharing agreement (~100+ stations).</li>
              <li>Telangana Irrigation &amp; CAD Musi River gauge digitization &amp; gate schedules.</li>
              <li>ISRO NRSC Bhuvan high-resolution SAR flood inundation GeoTIFF rasters.</li>
              <li>Continuous multi-year daily observation matrix (negative non-flood days) for ROC-AUC evaluation.</li>
            </ul>
          </div>
        </article>
      </div>

      {/* Operations Panels: Milestone 8 Institutional Data Acquisition & Evidence Intake */}
      <div className="operations-grid" style={{ marginTop: '24px' }}>
        <article className="operations-panel">
          <div className="panel-heading" style={{flexDirection: 'column', alignItems: 'flex-start'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', width: '100%', marginBottom: '4px', flexWrap: 'wrap', gap: '8px'}}>
              <h3>Institutional Acquisition Inventory &amp; Requisition Protocols</h3>
              <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.35)', fontWeight: 'bold' }}>
                Milestone 8 · Intake Ready
              </span>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: 0 }}>
              Tracking available vs restricted sources, draft institutional request templates, and unsupported measurement gaps.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', padding: '16px', maxHeight: '520px', overflowY: 'auto' }}>
            {/* Source Status Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
              <div style={{ background: 'rgba(52, 211, 153, 0.1)', border: '1px solid rgba(52, 211, 153, 0.3)', padding: '8px 10px', borderRadius: '6px' }}>
                <span style={{ fontSize: '10px', color: '#34d399', fontWeight: 'bold' }}>DOWNLOADED &amp; VERIFIED</span>
                <strong style={{ display: 'block', fontSize: '17px', color: '#f1f5f9', marginTop: '2px' }}>6 Sources</strong>
                <small style={{ fontSize: '9.5px', color: '#94a3b8' }}>DES, GloFAS, ERA5, Zones, Alerts, Catalogue</small>
              </div>
              <div style={{ background: 'rgba(192, 132, 252, 0.1)', border: '1px solid rgba(192, 132, 252, 0.3)', padding: '8px 10px', borderRadius: '6px' }}>
                <span style={{ fontSize: '10px', color: '#c084fc', fontWeight: 'bold' }}>VIEWER / REPORT ONLY</span>
                <strong style={{ display: 'block', fontSize: '17px', color: '#f1f5f9', marginTop: '2px' }}>1 Source</strong>
                <small style={{ fontSize: '9.5px', color: '#94a3b8' }}>ISRO NRSC Bhuvan Oct 2020 WMS</small>
              </div>
              <div style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', padding: '8px 10px', borderRadius: '6px' }}>
                <span style={{ fontSize: '10px', color: '#f59e0b', fontWeight: 'bold' }}>RESTRICTED ACCESS</span>
                <strong style={{ display: 'block', fontSize: '17px', color: '#f1f5f9', marginTop: '2px' }}>2 Sources</strong>
                <small style={{ fontSize: '9.5px', color: '#94a3b8' }}>TSDPS AWS (~100 stn) &amp; I&amp;CAD Dam Logs</small>
              </div>
              <div style={{ background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '8px 10px', borderRadius: '6px' }}>
                <span style={{ fontSize: '10px', color: '#38bdf8', fontWeight: 'bold' }}>DRAFT REQUISITIONS</span>
                <strong style={{ display: 'block', fontSize: '17px', color: '#f1f5f9', marginTop: '2px' }}>4 Templates</strong>
                <small style={{ fontSize: '9.5px', color: '#94a3b8' }}>Documented &amp; ready for formal submission</small>
              </div>
            </div>

            {/* Draft Request Templates Overview */}
            <div style={{ marginTop: '6px' }}>
              <strong style={{ fontSize: '12px', color: '#cbd5e1' }}>Draft Institutional Requisitions (docs/data_requests/):</strong>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '6px' }}>
                <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)', padding: '8px 10px', borderRadius: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <b style={{ fontSize: '11.5px', color: '#f1f5f9' }}>1. TSDPS AWS Sub-Daily Telemetry Requisition</b>
                    <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(245,158,11,0.15)', color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)' }}>DRAFT REQUEST</span>
                  </div>
                  <small style={{ fontSize: '10.5px', color: '#94a3b8', display: 'block', marginTop: '2px' }}>
                    10-year (2014–2024) 15-minute tipping-bucket rainfall across ~100+ GHMC AWS stations with QC flags.
                  </small>
                </div>

                <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)', padding: '8px 10px', borderRadius: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <b style={{ fontSize: '11.5px', color: '#f1f5f9' }}>2. Telangana I&amp;CAD Musi Reservoir Gate Outflows</b>
                    <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(245,158,11,0.15)', color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)' }}>DRAFT REQUEST</span>
                  </div>
                  <small style={{ fontSize: '10.5px', color: '#94a3b8', display: 'block', marginTop: '2px' }}>
                    Hourly sluice gate opening schedules &amp; reservoir stage levels for Osman Sagar and Himayat Sagar.
                  </small>
                </div>

                <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)', padding: '8px 10px', borderRadius: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <b style={{ fontSize: '11.5px', color: '#f1f5f9' }}>3. ISRO / NRSC Sentinel-1 SAR GeoTIFF Inundation Rasters</b>
                    <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(245,158,11,0.15)', color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)' }}>DRAFT REQUEST</span>
                  </div>
                  <small style={{ fontSize: '10.5px', color: '#94a3b8', display: 'block', marginTop: '2px' }}>
                    Level-3 cloud-penetrating SAR and Cartosat flood inundation extent rasters (10 m grid) for 2016, 2020, 2022, and 2023.
                  </small>
                </div>

                <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)', padding: '8px 10px', borderRadius: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <b style={{ fontSize: '11.5px', color: '#f1f5f9' }}>4. Multi-Year Non-Flood Control Matrix (IMD &amp; GHMC DRF)</b>
                    <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(245,158,11,0.15)', color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)' }}>DRAFT REQUEST</span>
                  </div>
                  <small style={{ fontSize: '10.5px', color: '#94a3b8', display: 'block', marginTop: '2px' }}>
                    Continuous daily observation matrix matched with DRF zero-dewatering deployment logs for false-positive validation.
                  </small>
                </div>
              </div>
            </div>

            {/* Unsupported Measurements Gaps */}
            <div style={{ marginTop: '6px', background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.25)', padding: '8px 10px', borderRadius: '6px' }}>
              <b style={{ fontSize: '11.5px', color: '#f87171' }}>Unsupported River Discharges (Nullified in Audited Catalogue):</b>
              <p style={{ fontSize: '10.5px', color: '#cbd5e1', margin: '4px 0 0 0' }}>
                Events in <b>2000</b> (prior: 1250 cumec), <b>2016</b> (prior: 210 cumec), <b>2021</b> (prior: 95 cumec), and <b>2023</b> (prior: 85 cumec) lacked physical stream gauge telemetry. Discharges remain <code>null</code> until open in-stream telemetry is digitized.
              </p>
            </div>
          </div>
        </article>

        <article className="operations-panel">
          <div className="panel-heading" style={{flexDirection: 'column', alignItems: 'flex-start'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', width: '100%', marginBottom: '4px', flexWrap: 'wrap', gap: '8px'}}>
              <h3>Validated Data-Intake Engine &amp; Negative Controls</h3>
              <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', background: 'rgba(52, 211, 153, 0.15)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.35)', fontWeight: 'bold' }}>
                API Ready · /data-curation/intake
              </span>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: 0 }}>
              Interactive dry-run validator for CSV/JSON payloads; enforces coordinates, timestamps, unit conversions, and missing-value sentinels.
            </p>
          </div>

          <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {/* Interactive Validator Tool */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '6px' }}>
                <span style={{ fontSize: '11.5px', fontWeight: 'bold', color: '#cbd5e1' }}>Test Intake Payload (CSV):</span>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button 
                    onClick={() => setValidatorInput('timestamp,station_id,latitude,longitude,rainfall,rainfall_unit,discharge,discharge_unit\n2020-10-14T08:00:00Z,TSDPS-GHATKESAR,17.442,78.682,320.0,mm,850.0,m^3/s\n2020-10-14T08:00:00Z,TSDPS-BEGUMPET,17.442,78.475,19.18,cm,12000,cusec')}
                    style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '4px', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.2)', color: '#38bdf8', cursor: 'pointer' }}
                  >
                    Load Valid Sample (Unit Normalization)
                  </button>
                  <button 
                    onClick={() => setValidatorInput('timestamp,station_id,latitude,longitude,rainfall,rainfall_unit\nINVALID_DATE,TSDPS-001,195.4,78.475,-15.0,mm\n2020-10-14T08:00:00Z,*,17.442,78.475,50.0,unknown_unit')}
                    style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '4px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', cursor: 'pointer' }}
                  >
                    Load Malformed Sample (Error Check)
                  </button>
                </div>
              </div>

              <textarea 
                value={validatorInput} 
                onChange={(e) => setValidatorInput(e.target.value)}
                rows={4}
                style={{
                  width: '100%',
                  background: 'rgba(0,0,0,0.35)',
                  border: '1px solid rgba(255,255,255,0.12)',
                  borderRadius: '6px',
                  color: '#f1f5f9',
                  fontFamily: 'monospace',
                  fontSize: '11px',
                  padding: '8px',
                  boxSizing: 'border-box'
                }}
              />

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                <button
                  onClick={handleRunValidation}
                  disabled={isValidating}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '5px',
                    background: isValidating ? 'rgba(56, 189, 248, 0.3)' : 'var(--accent, #0284c7)',
                    color: '#fff',
                    border: 'none',
                    fontWeight: 'bold',
                    fontSize: '11.5px',
                    cursor: isValidating ? 'not-allowed' : 'pointer'
                  }}
                >
                  {isValidating ? 'Validating...' : '▶ Run Ingestion Validation'}
                </button>
                <small style={{ fontSize: '10px', color: '#94a3b8' }}>
                  Target: <code>POST /data-curation/intake/validate</code>
                </small>
              </div>
            </div>

            {/* Validation Diagnostic Output */}
            {validationResult && (
              <div style={{
                background: validationResult.valid ? 'rgba(52, 211, 153, 0.08)' : 'rgba(239, 68, 68, 0.08)',
                border: `1px solid ${validationResult.valid ? 'rgba(52, 211, 153, 0.35)' : 'rgba(239, 68, 68, 0.35)'}`,
                padding: '10px 12px',
                borderRadius: '6px',
                fontSize: '11px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <b style={{ color: validationResult.valid ? '#34d399' : '#f87171' }}>
                    {validationResult.valid ? '✓ VALIDATION PASSED' : '✕ VALIDATION REJECTED (Contract Violations Found)'}
                  </b>
                  <span style={{ fontSize: '10px', color: '#94a3b8' }}>
                    Processed: {validationResult.total_records_processed} | Valid: {validationResult.valid_records_count}
                  </span>
                </div>

                {validationResult.errors && validationResult.errors.length > 0 && (
                  <div style={{ marginTop: '6px' }}>
                    <span style={{ color: '#f87171', fontWeight: 'bold' }}>Errors ({validationResult.errors.length}):</span>
                    <ul style={{ margin: '4px 0 0 0', paddingLeft: '18px', color: '#fca5a5', maxHeight: '100px', overflowY: 'auto' }}>
                      {validationResult.errors.map((err, idx) => (
                        <li key={idx}>
                          Row {err.row || '?'}: {err.field} — {err.error}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {validationResult.sample_records && validationResult.sample_records.length > 0 && (
                  <div style={{ marginTop: '6px' }}>
                    <span style={{ color: '#34d399', fontWeight: 'bold' }}>Sample Normalized Record (Units Preserved):</span>
                    <pre style={{ margin: '4px 0 0 0', background: 'rgba(0,0,0,0.4)', padding: '6px', borderRadius: '4px', fontSize: '9.5px', color: '#cbd5e1', overflowX: 'auto' }}>
                      {JSON.stringify(validationResult.sample_records[0], null, 2)}
                    </pre>
                  </div>
                )}

                {/* Commit Action when Validation Passes */}
                {validationResult.valid && (
                  <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid rgba(52, 211, 153, 0.25)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                      <div>
                        <b style={{ color: '#f1f5f9', fontSize: '11px' }}>Authorized Repository Ingestion:</b>
                        <small style={{ display: 'block', color: '#94a3b8', fontSize: '10px' }}>
                          Commit normalized records to repository storage and append to intake ledger (Admin key required).
                        </small>
                      </div>
                      <button
                        onClick={handleCommitBatch}
                        disabled={isCommitting}
                        style={{
                          padding: '6px 14px',
                          borderRadius: '5px',
                          background: isCommitting ? 'rgba(52, 211, 153, 0.3)' : '#059669',
                          color: '#fff',
                          fontWeight: 'bold',
                          border: 'none',
                          fontSize: '11px',
                          cursor: isCommitting ? 'not-allowed' : 'pointer'
                        }}
                      >
                        {isCommitting ? 'Committing...' : '⚡ Commit Batch to Storage'}
                      </button>
                    </div>

                    {commitResult && (
                      <div style={{
                        marginTop: '8px',
                        padding: '8px 10px',
                        borderRadius: '4px',
                        fontSize: '10.5px',
                        background: commitResult.success ? 'rgba(52, 211, 153, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                        color: commitResult.success ? '#34d399' : '#f87171',
                        border: `1px solid ${commitResult.success ? 'rgba(52, 211, 153, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
                      }}>
                        {commitResult.success ? (
                          <span>
                            ✓ <b>Batch committed successfully!</b> Added {commitResult.data?.curated_records_count} records. File SHA-256: <code>{commitResult.data?.file_checksum_sha256?.slice(0, 16)}...</code>
                          </span>
                        ) : (
                          <span>✕ <b>Commit Rejected:</b> {commitResult.error}</span>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Negative Control Standard Summary */}
            <div style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(255, 255, 255, 0.08)', padding: '10px 12px', borderRadius: '6px', marginTop: '4px' }}>
              <b style={{ fontSize: '11.5px', color: '#cbd5e1', display: 'block', marginBottom: '3px' }}>
                Negative-Control Evidence Taxonomy (docs/negative_control_data_requirements.md):
              </b>
              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', margin: '4px 0' }}>
                <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(239,68,68,0.15)', color: '#f87171' }}>CONFIRMED_FLOOD</span>
                <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(52,211,153,0.15)', color: '#34d399' }}>DOCUMENTED_NON_FLOOD</span>
                <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(245,158,11,0.15)', color: '#fbbf24' }}>UNKNOWN_OR_UNCLASSIFIED</span>
                <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(148,163,184,0.15)', color: '#94a3b8' }}>MISSING_OBSERVATION</span>
                <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(192,132,252,0.15)', color: '#c084fc' }}>MODELLED_ESTIMATE</span>
              </div>
              <p style={{ fontSize: '10.5px', color: '#94a3b8', margin: '4px 0 0 0', lineHeight: '1.4' }}>
                <strong>Strict Evidence Rule:</strong> Days without an official flood declaration are classified as <code>UNKNOWN_OR_UNCLASSIFIED</code> unless confirmed with verified rainfall + DRF zero-dewatering deployment logs. Synthetic controls are strictly prohibited.
              </p>
            </div>
          </div>
        </article>
      </div>

      <div className="operations-grid" style={{ marginTop: '24px' }}>
        <article className="operations-panel">
          <div className="panel-heading" style={{flexDirection: 'column', alignItems: 'flex-start'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', width: '100%', marginBottom: '8px'}}>
              <h3>Emergency Facilities & Shelters</h3>
              <span>{allFacilities.length} total records</span>
            </div>
            <div style={{display: 'flex', gap: '12px', fontSize: '0.85em', color: 'var(--text-muted)'}}>
              <span>Hospitals: {hospitalsCount}</span>
              <span>Shelters: {sheltersCount}</span>
              <span>Unverified: {unverifiedCount}</span>
            </div>
          </div>
          {allFacilities.slice(0, 10).map((fac) => (
            <div className="resource-row" key={fac.facility_id || fac.id || fac.name}>
              <div>
                <strong>{fac.facility_type === 'HOSPITAL' ? '🏥 ' : '🏠 '}{fac.name}</strong>
                <small style={{display: 'block', color: 'var(--warning)'}}>
                  {fac.data_status || 'PUBLIC_UNVERIFIED'} · {fac.verification_note || 'Status not verified'}
                </small>
                <small style={{display: 'block'}}>Source: {fac.source || 'Public directory'}</small>
              </div>
              <div style={{display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-end'}}>
                <span className={`resource-status`}>{fac.operational_status || 'UNKNOWN'}</span>
                <b>Cap: {fac.capacity != null ? fac.capacity : '?'} | Occ: {fac.current_occupancy != null ? fac.current_occupancy : '?'}</b>
              </div>
            </div>
          ))}
          {allFacilities.length > 10 && (
            <div style={{padding: '12px 24px', textAlign: 'center', color: 'var(--text-muted)'}}>
              Showing 10 of {allFacilities.length} emergency facilities
            </div>
          )}
        </article>

        <article className="operations-panel">
          <div className="panel-heading"><h3>Data Limitations & Sources</h3></div>
          <div style={{padding: '24px', lineHeight: '1.6', color: 'var(--text-muted)'}}>
            <p><strong>Flood Model:</strong> INDOFLOODS severity model</p>
            <p><strong>Hospitals:</strong> Public Health & Vaidya Vidhana Parishad Directories (PUBLIC_UNVERIFIED)</p>
            <p><strong>Shelters:</strong> GHMC community listings (PUBLIC_UNVERIFIED)</p>
            <p><strong>Road Network:</strong> OpenStreetMap + Hazard-Aware Rerouting</p>
            <p><strong>Hydrology / Road Hazards:</strong> DEMO Simulation Data</p>
            <hr style={{borderColor: 'rgba(255,255,255,0.05)', margin: '16px 0'}} />
            <p style={{fontSize: '0.9em'}}>
              <strong>Integrity Guard:</strong> Bed availability, shelter capacity, and operational status are left <code>null</code> / <code>UNKNOWN</code> unless officially verified. Never fabricate emergency triage readiness.
            </p>
          </div>
        </article>
      </div>
    </section>
  );
}

