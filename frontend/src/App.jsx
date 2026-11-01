import React, { useState, useEffect, useRef } from 'react'
import Header from './components/Header'
import SOSModal from './components/SOSModal'
import AIAssistantChat from './components/AIAssistantChat'
import OverviewTab from './components/tabs/OverviewTab'
import MapTab from './components/tabs/MapTab'
import RoutesTab from './components/tabs/RoutesTab'
import SheltersTab from './components/tabs/SheltersTab'
import AlertsTab from './components/tabs/AlertsTab'
import AboutTab from './components/tabs/AboutTab'
import IncidentsTab from './components/tabs/IncidentsTab'
import OperationsDashboard from './components/OperationsDashboard'
import { translations } from './utils/translations'
import {
  beginLatestRequest,
  invalidateLatestRequest,
  isLatestRequest,
} from './utils/evacuationFlow'
import useEvacuationRoute from './utils/useEvacuationRoute'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const hyderabadLocation = { latitude: 17.385, longitude: 78.4867 }
const isInHyderabad = ({ latitude, longitude }) => latitude >= 17.2 && latitude <= 17.6 && longitude >= 78.2 && longitude <= 78.7
const dashboardResourceNames = [
  'weather', 'risk', 'recommendation', 'shelters', 'facilities', 'alerts',
  'roads', 'gauges', 'hydrology', 'hazards', 'locationWarning', 'incidents'
]
const globalDashboardResourceNames = ['shelters', 'alerts', 'roads', 'gauges', 'hazards', 'incidents']

const initialDashboardStatus = dashboardResourceNames.reduce((status, name) => {
  status[name] = 'loading'
  return status
}, {})

export default function App() {
  const [activeTab, setActiveTab] = useState('citizen')
  const [language, setLanguage] = useState('en')
  const [isSevereWeather, setIsSevereWeather] = useState(false)
  const [highContrast, setHighContrast] = useState(false)
  const [isSosOpen, setIsSosOpen] = useState(false)

  const [apiStatus, setApiStatus] = useState('Checking API...')
  const [location, setLocation] = useState(hyderabadLocation)
  const [locationStatus, setLocationStatus] = useState('Hyderabad center location')
  const [weather, setWeather] = useState(null)
  const [riskData, setRiskData] = useState(null)
  const [recommendationResponse, setRecommendationResponse] = useState(null)
  const [facilities, setFacilities] = useState([])
  const [selectedFacility, setSelectedFacility] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [shelters, setShelters] = useState([])
  const [roads, setRoads] = useState([])
  const [gauges, setGauges] = useState([])
  const [hydrology, setHydrology] = useState(null)
  const [floodHazards, setFloodHazards] = useState([])
  const [hazardWarning, setHazardWarning] = useState(null)
  const [incidents, setIncidents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dashboardStatus, setDashboardStatus] = useState(initialDashboardStatus)
  const hasManualLocationSelection = useRef(false)
  const dashboardRequestRef = useRef({ id: 0, controller: null })
  const isMountedRef = useRef(true)

  const t = translations[language] || translations.en

  const request = async (path, options) => {
    const response = await fetch(`${apiBaseUrl}${path}`, options)
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      throw new Error(payload.detail ?? `Request failed: ${response.status}`)
    }
    return response.json()
  }

  const { route, isRouting, calculateRouteForFacility, cancelRoute } = useEvacuationRoute({
    location,
    request,
    onError: setError
  })

  const loadDashboard = async (currentLocation) => {
    const { id: requestId, controller } = beginLatestRequest(dashboardRequestRef.current)

    setLoading(true)
    setError('')
    setDashboardStatus(previous => {
      const next = { ...previous }
      const hasRetainedData = {
        shelters: shelters.length > 0,
        alerts: alerts.length > 0,
        roads: roads.length > 0,
        gauges: gauges.length > 0,
        hazards: floodHazards.length > 0,
        incidents: incidents.length > 0
      }
      dashboardResourceNames.forEach(name => {
        next[name] = globalDashboardResourceNames.includes(name)
          ? (hasRetainedData[name] ? 'refreshing' : 'loading')
          : 'loading'
      })
      return next
    })
    setWeather(null)
    setRiskData(null)
    setRecommendationResponse(null)
    setFacilities([])
    setSelectedFacility(null)
    // Global feeds remain visible while refreshing and are marked via dashboardStatus.
    setHydrology(null)
    setHazardWarning(null)
    cancelRoute()
    const query = `latitude=${currentLocation.latitude}&longitude=${currentLocation.longitude}`
    const recQuery = `${query}&radius_km=15.0&top_n=5`

    try {
      const requestResource = (name, path) => request(path, { signal: controller.signal })
        .then(data => ({ name, status: 'available', data }))
        .catch(loadError => ({ name, status: 'unavailable', error: loadError }))

      const [healthResult, ...results] = await Promise.all([
        request('/health', { signal: controller.signal }).then(data => ({ status: 'available', data })).catch(error => ({ status: 'unavailable', error })),
        requestResource('weather', `/weather?${query}`),
        requestResource('risk', `/risk-map?${query}`),
        requestResource('recommendation', `/shelters/recommended?${recQuery}`),
        requestResource('shelters', '/shelters'),
        requestResource('facilities', `/emergency-facilities?facility_type=HOSPITAL&${query}&radius_km=15`),
        requestResource('alerts', '/disaster-alerts'),
        requestResource('roads', '/road-conditions'),
        requestResource('gauges', '/gauges'),
        requestResource('hydrology', `/hydrology/water-level?${query}`),
        requestResource('hazards', '/flood-hazards'),
        requestResource('locationWarning', `/flood-hazards/check-location?${query}`),
        requestResource('incidents', '/incidents')
      ])

      if (!isMountedRef.current || !isLatestRequest(dashboardRequestRef.current, requestId)) return

      const resources = Object.fromEntries(results.map(result => [result.name, result]))
      const nextStatus = Object.fromEntries(
        dashboardResourceNames.map(name => [name, resources[name].status])
      )
      setDashboardStatus(nextStatus)
      setApiStatus(healthResult.status === 'available'
        ? (healthResult.data?.demo_mode ? 'API Online · Demo Mode' : 'API Online')
        : 'API Unavailable')
      setWeather(resources.weather.status === 'available' ? resources.weather.data : null)
      setRiskData(resources.risk.status === 'available' ? resources.risk.data : null)
      setRecommendationResponse(resources.recommendation.status === 'available' ? resources.recommendation.data : null)
      
      const shelterList = resources.shelters.status === 'available' ? resources.shelters.data : null
      const emergencyServices = resources.facilities.status === 'available' ? resources.facilities.data : null
      const allShelters = (shelterList?.shelters || (resources.shelters.status === 'unavailable' ? shelters : [])).map(s => ({
        ...s,
        facility_type: 'SHELTER',
        id: s.shelter_id || s.id,
        name: s.name,
        distance_km: s.distance_km
      }))
      
      const rawServices = emergencyServices?.facilities || []
      const allServices = rawServices.map(e => ({
        ...e,
        facility_type: e.facility_type ? e.facility_type.toUpperCase() : 'HOSPITAL',
        id: e.id || e.service_id,
        name: e.name,
        distance_km: e.distance_km
      }))
      
      const combinedFacilities = [...allShelters, ...allServices]
      setFacilities(combinedFacilities)
      if (resources.shelters.status === 'available') setShelters(allShelters)
      
      const shelterRes = resources.recommendation.status === 'available' ? resources.recommendation.data : null
      if (shelterRes?.recommendations?.[0]) {
        setSelectedFacility(shelterRes.recommendations[0])
      } else if (combinedFacilities.length > 0) {
        setSelectedFacility(combinedFacilities[0])
      } else {
        setSelectedFacility(null)
      }
      
      if (resources.alerts.status === 'available') setAlerts(resources.alerts.data || [])
      if (resources.roads.status === 'available') setRoads(resources.roads.data || [])
      const gaugeList = resources.gauges.status === 'available' ? resources.gauges.data : null
      if (resources.gauges.status === 'available') setGauges(gaugeList?.gauges || gaugeList || [])
      setHydrology(resources.hydrology.status === 'available' ? resources.hydrology.data : null)
      const hazardData = resources.hazards.status === 'available' ? resources.hazards.data : null
      if (resources.hazards.status === 'available') setFloodHazards(hazardData?.hazards || [])
      setHazardWarning(resources.locationWarning.status === 'available' ? resources.locationWarning.data : null)
      const incidentList = resources.incidents.status === 'available' ? resources.incidents.data : null
      if (resources.incidents.status === 'available') setIncidents(incidentList?.incidents || [])
    } catch (loadError) {
      if (!isMountedRef.current || !isLatestRequest(dashboardRequestRef.current, requestId)) return
      setApiStatus('API Unavailable')
      setError(loadError.message)
      setDashboardStatus(dashboardResourceNames.reduce((status, name) => {
        status[name] = 'unavailable'
        return status
      }, {}))
    } finally {
      if (isMountedRef.current && isLatestRequest(dashboardRequestRef.current, requestId)) {
        setLoading(false)
      }
    }
  }

  // Resolve the browser location on every page load before loading dashboard data.
  useEffect(() => {
    isMountedRef.current = true
    refreshLocation()
    return () => {
      isMountedRef.current = false
      invalidateLatestRequest(dashboardRequestRef.current)
    }
  }, [])

  const handleLocationSelect = (newLocation) => {
    hasManualLocationSelection.current = true
    setLocation(newLocation)
    setLocationStatus('Selected coordinates active')
    cancelRoute()
    loadDashboard(newLocation)
  }

  const handleFacilitySelect = (facility) => {
    cancelRoute()
    setSelectedFacility(facility)
  }

  const handlePlanRouteToFacility = (facility) => {
    setSelectedFacility(facility)
    setActiveTab('routes')
    calculateRouteForFacility(facility)
  }

  const openExternalNavigation = (facility = selectedFacility) => {
    if (!facility || facility.latitude == null || facility.longitude == null) {
      setError('This safety location does not have valid coordinates for navigation.')
      return
    }

    const origin = `${location.latitude},${location.longitude}`
    const destination = `${facility.latitude},${facility.longitude}`
    const mapsUrl = `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}&travelmode=driving`
    window.open(mapsUrl, '_blank', 'noopener,noreferrer')
  }

  const refreshLocation = () => {
    setError('')
    hasManualLocationSelection.current = false
    if (!navigator.geolocation) {
      setLocationStatus('Location unavailable - center active')
      loadDashboard(hyderabadLocation)
      return
    }

    setLocationStatus('Acquiring live GPS...')
    navigator.geolocation.getCurrentPosition(
      (position) => {
        if (!isMountedRef.current || hasManualLocationSelection.current) return
        const currentLocation = { latitude: position.coords.latitude, longitude: position.coords.longitude }
        setLocation(currentLocation)
        if (isInHyderabad(currentLocation)) {
          setLocationStatus('Live location active')
          loadDashboard(currentLocation)
          return
        }
        setLocationStatus('Live location active · Hyderabad data services unavailable outside coverage')
        loadDashboard(currentLocation)
      },
      () => {
        if (!isMountedRef.current || hasManualLocationSelection.current) return
        setLocationStatus('Location unavailable - center active')
        setLocation(hyderabadLocation)
        loadDashboard(hyderabadLocation)
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 },
    )
  }

  return (
    <div className={`safemap-app-container command-center-mode ${highContrast ? 'high-contrast-mode' : ''}`}>
      {/* Reference Design Command Center Header */}
      <Header
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        language={language}
        onSelectLanguage={setLanguage}
        isSevereWeather={isSevereWeather}
        onToggleWeather={setIsSevereWeather}
        highContrast={highContrast}
        onToggleHighContrast={() => setHighContrast(!highContrast)}
        onOpenSOS={() => setIsSosOpen(true)}
        apiStatus={apiStatus}
        alertsCount={alerts.length}
        t={t}
      />

      {error && (
        <div className="app-error-banner" role="alert">
          <span className="error-icon" aria-hidden="true">⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Main Tab Content Area */}
      <main className="app-main-workspace" id="main-content">
        {(activeTab === 'citizen' || activeTab === 'overview') && (
          <OverviewTab
            riskData={riskData}
            location={location}
            facilities={facilities}
            selectedFacility={selectedFacility}
            onFacilitySelect={handleFacilitySelect}
            roads={roads}
            route={route}
            floodHazards={floodHazards}
            loading={loading}
            weather={weather}
            hydrology={hydrology}
            alerts={alerts}
            hazardWarning={hazardWarning}
            onCalculateRoute={() => calculateRouteForFacility(selectedFacility)}
            onOpenNavigation={() => openExternalNavigation(selectedFacility)}
            isRouting={isRouting}
            onLocationSelect={handleLocationSelect}
            onMyLocation={refreshLocation}
            onNavigateToTab={setActiveTab}
            isSevereWeather={isSevereWeather}
            dashboardStatus={dashboardStatus}
            t={t}
            incidents={incidents}
          />
        )}

        {activeTab === 'map' && (
          <MapTab
            riskData={riskData}
            location={location}
            facilities={facilities}
            selectedFacility={selectedFacility}
            onFacilitySelect={handleFacilitySelect}
            roads={roads}
            route={route}
            floodHazards={floodHazards}
            loading={loading}
            hazardWarning={hazardWarning}
            onLocationSelect={handleLocationSelect}
            incidents={incidents}
          />
        )}

        {activeTab === 'routes' && (
          <RoutesTab
            location={location}
            facilities={facilities}
            selectedFacility={selectedFacility}
            onFacilitySelect={handleFacilitySelect}
            route={route}
            roads={roads}
            floodHazards={floodHazards}
            loading={loading}
            isRouting={isRouting}
            dashboardStatus={dashboardStatus}
            onCalculateRoute={() => calculateRouteForFacility(selectedFacility)}
            onOpenNavigation={() => openExternalNavigation(selectedFacility)}
            onMyLocation={refreshLocation}
            onLocationSelect={handleLocationSelect}
            incidents={incidents}
          />
        )}

        {(activeTab === 'directory' || activeTab === 'shelters') && (
          <SheltersTab
            facilities={facilities}
            selectedFacility={selectedFacility}
            onFacilitySelect={handleFacilitySelect}
            onPlanRouteToFacility={handlePlanRouteToFacility}
          />
        )}

        {(activeTab === 'protocols' || activeTab === 'alerts') && (
          <AlertsTab
            alerts={alerts}
            floodHazards={floodHazards}
            hazardWarning={hazardWarning}
            dashboardStatus={dashboardStatus}
          />
        )}

        {activeTab === 'operations' && (
          <OperationsDashboard
            apiBaseUrl={apiBaseUrl}
            apiStatus={apiStatus}
            weather={weather}
            riskData={riskData}
            shelters={shelters}
            facilities={facilities}
            roads={roads}
            location={location}
            route={route}
            gauges={gauges}
            hydrology={hydrology}
            alerts={alerts}
            floodHazards={floodHazards}
            hazardWarning={hazardWarning}
            onLocationSelect={handleLocationSelect}
          />
        )}

        {activeTab === 'incidents' && (
          <IncidentsTab
            location={location}
            incidents={incidents}
            onRefreshIncidents={() => {
              request('/incidents')
                .then(res => setIncidents(res?.incidents || []))
                .catch(() => {})
            }}
            apiBaseUrl={apiBaseUrl}
            t={t}
          />
        )}

        {activeTab === 'about' && <AboutTab />}
      </main>

      {/* Floating AI Safety Assistant in Bottom Right */}
      <AIAssistantChat
        language={language}
        riskData={riskData}
        weather={weather}
        alerts={alerts}
        route={route}
        shelters={shelters}
        hazardWarning={hazardWarning}
        location={location}
      />

      {/* Emergency SOS Modal */}
      <SOSModal isOpen={isSosOpen} onClose={() => setIsSosOpen(false)} />

      {/* Persistent Legal & Prototype Disclaimer Footer */}
      <footer className="app-command-footer">
        <div className="footer-container">
          <div className="footer-left">
            <span className="footer-badge">ACADEMIC RESEARCH PROTOTYPE</span>
            <span className="footer-dot">•</span>
            <span className="footer-disclaimer-text">
              SafeMap AI Hyderabad is an experimental decision-support prototype. <strong>NOT</strong> an official emergency alert system. For life-threatening emergencies, immediately dial <strong>112</strong> or GHMC DRF <strong>040-21111111</strong>.
            </span>
          </div>
          <div className="footer-right">
            <span className="footer-coords">
              Hyderabad (17.3850° N, 78.4867° E) · 50km Safeguard Active
            </span>
          </div>
        </div>
      </footer>
    </div>
  )
}
