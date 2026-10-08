import React from 'react';
import { CircleMarker, MapContainer, Polygon, Polyline, Popup, TileLayer, ZoomControl, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const riskColors = {
  HIGH: '#ef4444',
  MEDIUM: '#f59e0b',
  LOW: '#10b981',
};

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

function OperationsMap({ riskData, location, route, gauges, shelters, onLocationSelect }) {
  const center = [(17.2 + 17.6) / 2, (78.2 + 78.7) / 2];
  const routePositions = route?.geometry?.map(([longitude, latitude]) => [latitude, longitude]) ?? [];

  return (
    <MapContainer className="leaflet-map" center={center} zoom={11} scrollWheelZoom zoomControl={false}>
      <ZoomControl position="topright" />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MapClickHandler onLocationSelect={onLocationSelect} />
      
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
      {routePositions.length > 1 && <Polyline positions={routePositions} pathOptions={{ color: '#38bdf8', weight: 4, opacity: 0.8 }} />}
      
      {/* Gauges */}
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

      {/* Shelters */}
      {shelters && shelters.map(shelter => (
        <CircleMarker 
          key={shelter.id || shelter.name} 
          center={[shelter.latitude, shelter.longitude]} 
          pathOptions={{ color: '#10b981', fillColor: '#10b981', fillOpacity: 0.6, weight: 1 }} 
          radius={4}
        >
          <Popup>{shelter.name} ({shelter.data_status || 'PUBLIC_UNVERIFIED'})</Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}

export default function OperationsDashboard({
  apiStatus,
  weather,
  riskData,
  shelters,
  roads,
  location,
  route,
  gauges,
  hydrology,
  alerts,
  onLocationSelect
}) {
  const verifiedSheltersCount = shelters.filter(s => s.data_status === 'VERIFIED').length;
  const unverifiedSheltersCount = shelters.length - verifiedSheltersCount;
  const unknownOpStatusCount = shelters.filter(s => !s.operational_status || s.operational_status === 'UNKNOWN').length;
  const unknownCapacityCount = shelters.filter(s => !s.capacity).length;

  return (
    <section className="operations-view">
      <div className="operations-heading">
        <div>
          <p className="eyebrow">SAFEMap AI</p>
          <h2>Operations Dashboard</h2>
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
          <span>MODEL COVERAGE</span>
          <strong style={{ fontSize: '1.5rem', marginTop: '12px' }}>50 km</strong>
          <small>limit from an official INDOFLOODS gauge.</small>
          <small style={{display: 'block', color: 'var(--text-highlight)'}}>Supported locations: {riskData?.coverage_status === 'MODEL_SUPPORTED' ? 'Yes (Selected)' : 'No (Selected)'}</small>
          <small style={{display: 'block'}}>Official gauges: {gauges?.length || 0}</small>
        </article>

        <article className="metric-card warning">
          <span>HYDROLOGY STATUS</span>
          <strong style={{ fontSize: '1.5rem', marginTop: '12px', color: 'var(--warning)' }}>DEMO</strong>
          <small>Water-level information is simulated for demonstration purposes.</small>
        </article>
      </div>

      <div className="workspace-grid">
        <div className="map-panel" style={{ minHeight: '500px' }}>
          <OperationsMap riskData={riskData} location={location} route={route} gauges={gauges} shelters={shelters} onLocationSelect={onLocationSelect} />
          <div className="map-legend">
            <span><i className="legend-dot user" />Selected</span>
            <span><i className="legend-dot" style={{backgroundColor: '#f97316'}} />Official Gauge</span>
            <span><i className="legend-dot safe" style={{backgroundColor: '#10b981'}} />Shelter</span>
            <span><i className="legend-dot route" style={{backgroundColor: '#38bdf8'}} />OSM Route</span>
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
                    <strong style={{fontSize: '1.2rem', color: 'var(--warning)'}}>MODEL_UNSUPPORTED</strong>
                  </div>
                  <p className="muted">Flood prediction unavailable.</p>
                </>
              )
            ) : (
              <p className="muted">Select a location.</p>
            )}
            <div style={{marginTop: "16px", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "12px"}}>
              <p className="muted" style={{fontSize: '0.85em'}}>
                Source: Open-Meteo Historical/Reanalysis<br/>
                {weather?.condition ?? 'Weather data unavailable'} · {
                  !weather ? 'Loading rainfall data...' : 
                  (weather.rainfall == null ? 'Rainfall data unavailable' : `${weather.rainfall} mm`)
                }
              </p>
            </div>
          </article>

          <article className="info-card">
            <p className="card-label">GAUGE / HYDROLOGY</p>
            <p className="muted">Official gauges count: {gauges?.length || 0}</p>
            {hydrology ? (
              <div style={{marginTop: '8px', padding: '8px', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: '6px'}}>
                <strong style={{color: 'var(--warning)', display: 'block', marginBottom: '4px'}}>Hydrology data: {hydrology.data_status || 'DEMO'}</strong>
                <p className="muted" style={{margin: 0, fontSize: '0.85em'}}>Water-level information is simulated for demonstration purposes.</p>
              </div>
            ) : (
              <p className="muted">Hydrology data unavailable.</p>
            )}
            <p className="muted" style={{fontSize: '0.85em', marginTop: '8px'}}>Source: DEMO Provider</p>
          </article>

          <article className="info-card">
            <p className="card-label">ROADS / ROUTING</p>
            <div className="metric-row">
              <strong style={{fontSize: '1.2rem'}}>OSM road network</strong>
            </div>
            {route ? (
              <div style={{marginTop: '12px'}}>
                <p className="muted" style={{margin: '4px 0'}}>Shortest available road-network route</p>
                <p className="muted" style={{margin: '4px 0'}}>Route status: {route.route_status || 'OK'}</p>
                <p className="muted" style={{margin: '4px 0'}}>Distance: {route.route_distance_km?.toFixed(2) ?? '?'} km</p>
                <p className="muted" style={{margin: '4px 0'}}>Road condition: {route.road_condition_status || 'UNKNOWN'}</p>
                {route.estimated_duration_min && (
                  <p className="muted" style={{margin: '4px 0'}}>Estimated duration: {route.estimated_duration_min} min</p>
                )}
              </div>
            ) : (
              <p className="muted" style={{marginTop: '8px'}}>No route generated.</p>
            )}
            <div style={{marginTop: "12px", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "8px"}}>
              <p className="muted" style={{margin: '2px 0', fontSize: '0.85em'}}>Network type: Driving/road network</p>
              <p className="muted" style={{margin: '2px 0', fontSize: '0.85em'}}>Road network source: OpenStreetMap</p>
              <p className="muted" style={{margin: '2px 0', fontSize: '0.85em'}}>Live traffic: NOT INTEGRATED</p>
              <p className="muted" style={{margin: '2px 0', fontSize: '0.85em'}}>Temporary road closures: NOT INTEGRATED</p>
              <p className="muted" style={{margin: '2px 0', fontSize: '0.85em'}}>Flooded-road detection: NOT INTEGRATED</p>
            </div>
          </article>
        </aside>
      </div>

      <div className="operations-grid">
        <article className="operations-panel">
          <div className="panel-heading" style={{flexDirection: 'column', alignItems: 'flex-start'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', width: '100%', marginBottom: '8px'}}>
              <h3>Shelters</h3><span>{shelters.length} total records</span>
            </div>
            <div style={{display: 'flex', gap: '12px', fontSize: '0.85em', color: 'var(--text-muted)'}}>
              <span>Verified: {verifiedSheltersCount}</span>
              <span>Unverified: {unverifiedSheltersCount}</span>
              <span>Unknown Status: {unknownOpStatusCount}</span>
              <span>Unknown Cap: {unknownCapacityCount}</span>
            </div>
          </div>
          {shelters.slice(0, 10).map((shelter) => (
            <div className="resource-row" key={shelter.shelter_id || shelter.id || shelter.name}>
              <div>
                <strong>{shelter.name}</strong>
                {shelter.data_status === 'PUBLIC_UNVERIFIED' && (
                  <small style={{display: 'block', color: 'var(--warning)'}}>NOT VERIFIED AS AN EMERGENCY FLOOD SHELTER</small>
                )}
                <small style={{display: 'block'}}>Source: {shelter.source || 'Local shelter dataset'}</small>
                <small style={{display: 'block'}}>Last updated: {shelter.last_updated || 'Timestamp unavailable'}</small>
              </div>
              <div style={{display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-end'}}>
                <span className={`resource-status`}>{shelter.operational_status || 'UNKNOWN'}</span>
                <b>Cap: {shelter.capacity || '?'} | Occ: {shelter.occupancy || '?'}</b>
              </div>
            </div>
          ))}
          {shelters.length > 10 && <div style={{padding: '12px 24px', textAlign: 'center', color: 'var(--text-muted)'}}>Showing 10 of {shelters.length} shelters</div>}
        </article>

        <article className="operations-panel">
          <div className="panel-heading"><h3>Data Limitations & Sources</h3></div>
          <div style={{padding: '24px', lineHeight: '1.6', color: 'var(--text-muted)'}}>
            <p><strong>Flood model:</strong> INDOFLOODS</p>
            <p><strong>Rainfall:</strong> Open-Meteo Historical/Reanalysis</p>
            <p><strong>Shelters:</strong> Local shelter dataset</p>
            <p><strong>Road network:</strong> OpenStreetMap</p>
            <p><strong>Hydrology:</strong> DEMO</p>
            <hr style={{borderColor: 'rgba(255,255,255,0.05)', margin: '16px 0'}} />
            <p style={{fontSize: '0.9em'}}>
              <strong>Note:</strong> This is a decision-support operational prototype. 
              Do not use unsupported model areas for automatic warnings. 
              Shelter information without verification must be treated as public, unvetted data.
            </p>
            <p style={{fontSize: '0.9em', marginTop: '8px'}}>
              <strong>Data Freshness:</strong> {weather?.timestamp ? new Date(weather.timestamp).toLocaleString() : 'Timestamp unavailable'}
            </p>
          </div>
        </article>
      </div>
    </section>
  );
}
