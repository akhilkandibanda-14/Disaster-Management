import React, { useState, useEffect } from 'react'
import Header from './components/Header'
import SOSModal from './components/SOSModal'
import AIAssistantChat from './components/AIAssistantChat'
import OverviewTab from './components/tabs/OverviewTab'
import MapTab from './components/tabs/MapTab'
import RoutesTab from './components/tabs/RoutesTab'
import SheltersTab from './components/tabs/SheltersTab'
import AlertsTab from './components/tabs/AlertsTab'
import AboutTab from './components/tabs/AboutTab'
import OperationsDashboard from './components/OperationsDashboard'
import { translations } from './utils/translations'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const hyderabadLocation = { latitude: 17.385, longitude: 78.4867 }
const isInHyderabad = ({ latitude, longitude }) => latitude >= 17.2 && latitude <= 17.6 && longitude >= 78.2 && longitude <= 78.7

const defaultInitialShelter = {
  shelter_id: "S0738",
  id: "S0738",
  name: "Khairatabad Shelter 738",
  latitude: 17.416844,
  longitude: 78.464475,
  capacity: 800.0,
  current_occupancy: 96.0,
  available_capacity: 704.0,
  flood_risk: "Low",
  facilities: "Water, Toilets, Food, First Aid",
  road_accessibility: "Good",
  accessibility: "Good",
  elevation_m: 2369.0,
  distance_km: 2.3,
  operational_status: "OPEN",
  shelter_type: "Permanent Flood Shelter",
  data_status: "VERIFIED_FLOOD_SHELTER"
}

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
  const [facilities, setFacilities] = useState([defaultInitialShelter])
  const [selectedFacility, setSelectedFacility] = useState(defaultInitialShelter)
  const [route, setRoute] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [shelters, setShelters] = useState([defaultInitialShelter])
  const [roads, setRoads] = useState([])
  const [gauges, setGauges] = useState([])
  const [hydrology, setHydrology] = useState(null)
  const [floodHazards, setFloodHazards] = useState([])
  const [hazardWarning, setHazardWarning] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isRouting, setIsRouting] = useState(false)
  const [error, setError] = useState('')

  const t = translations[language] || translations.en

  const request = async (path, options) => {
    const response = await fetch(`${apiBaseUrl}${path}`, options)
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      throw new Error(payload.detail ?? `Request failed: ${response.status}`)
    }
    return response.json()
  }

  const loadDashboard = async (currentLocation) => {
    setLoading(true)
    setError('')
    const query = `latitude=${currentLocation.latitude}&longitude=${currentLocation.longitude}`
    const recQuery = `${query}&radius_km=15.0&top_n=5`

    try {
      const [
        health, 
        weatherData, 
        riskRes, 
        shelterRes, 
        shelterList,
        emergencyServices,
        alertData, 
        roadList, 
        gaugeList, 
        hydroData,
        hazardData,
        locationWarningData
      ] = await Promise.all([
        request('/health').catch(() => ({})),
        request(`/weather?${query}`).catch(() => null),
        request(`/risk-map?${query}`).catch(() => null),
        request(`/shelters/recommended?${recQuery}`).catch(() => null),
        request('/shelters').catch(() => ({ shelters: [] })),
        request('/emergency-services').catch(() => []),
        request('/disaster-alerts').catch(() => []),
        request('/road-conditions').catch(() => []),
        request('/gauges').catch(() => []),
        request(`/hydrology/water-level?${query}`).catch(() => null),
        request('/flood-hazards').catch(() => ({ hazards: [] })),
        request(`/flood-hazards/check-location?${query}`).catch(() => null)
      ])
      
      setApiStatus(health?.demo_mode ? 'API Online · Demo Mode' : 'API Online')
      setWeather(weatherData)
      setRiskData(riskRes)
      setRecommendationResponse(shelterRes)
      
      const allShelters = (shelterList?.shelters || []).map(s => ({
        ...s,
        facility_type: 'SHELTER',
        id: s.shelter_id || s.id,
        name: s.name,
        distance_km: s.distance_km || 2.3
      }))
      
      const rawServices = Array.isArray(emergencyServices) ? emergencyServices : (emergencyServices?.services || [])
      const allServices = rawServices.map(e => ({
        ...e,
        facility_type: e.type ? e.type.toUpperCase() : 'HOSPITAL',
        id: e.id || e.service_id,
        name: e.name,
        distance_km: e.distance_km || 3.1
      }))
      
      const combinedFacilities = allShelters.length > 0 ? [...allShelters, ...allServices] : [defaultInitialShelter, ...allServices]
      setFacilities(combinedFacilities)
      setShelters(allShelters.length > 0 ? allShelters : [defaultInitialShelter])
      
      if (shelterRes?.recommendations?.[0]) {
        setSelectedFacility(shelterRes.recommendations[0])
      } else if (combinedFacilities.length > 0) {
        setSelectedFacility(combinedFacilities[0])
      }
      
      setAlerts(alertData || [])
      setRoads(roadList || [])
      setGauges(gaugeList || [])
      setHydrology(hydroData)
      setFloodHazards(hazardData?.hazards || [])
      setHazardWarning(locationWarningData)
    } catch (loadError) {
      setApiStatus('API Unavailable')
      setError(loadError.message)
    } finally {
      setLoading(false)
    }
  }

  // Initial dashboard load & optional Geolocation setup on mount
  useEffect(() => {
    // Load immediately with Hyderabad center location
    loadDashboard(hyderabadLocation)

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const currentLocation = { latitude: position.coords.latitude, longitude: position.coords.longitude }
          if (isInHyderabad(currentLocation)) {
            setLocation(currentLocation)
            setLocationStatus('Live location active')
            loadDashboard(currentLocation)
          }
        },
        () => {
          // Graceful fallback to default Hyderabad location
        },
        { enableHighAccuracy: true, timeout: 4000, maximumAge: 60000 },
      )
    }
  }, [])

  const handleLocationSelect = (newLocation) => {
    setLocation(newLocation)
    setLocationStatus('Selected coordinates active')
    loadDashboard(newLocation)
  }

  const handleFacilitySelect = (facility) => {
    setSelectedFacility(facility)
    setRoute(null)
  }

  const handlePlanRouteToFacility = (facility) => {
    setSelectedFacility(facility)
    setActiveTab('routes')
    calculateRouteForFacility(facility)
  }

  const calculateRouteForFacility = async (fac = selectedFacility) => {
    if (!fac) return
    setIsRouting(true)
    setError('')
    try {
      const destLat = fac.latitude ?? 17.416844
      const destLon = fac.longitude ?? 78.464475
      const facId = fac.facility_id || fac.id || fac.shelter_id
      
      const payload = { 
        origin: { latitude: location.latitude, longitude: location.longitude },
        destination: { latitude: destLat, longitude: destLon }
      }
      if (facId) {
        payload.facility_id = String(facId)
      }
      
      const data = await request('/evacuation-route', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(payload) 
      })
      setRoute(data)
    } catch (routeError) {
      setError(routeError.message)
    } finally {
      setIsRouting(false)
    }
  }

  const refreshLocation = () => {
    setError('')
    if (!navigator.geolocation) {
      setLocationStatus('Location unavailable - center active')
      loadDashboard(hyderabadLocation)
      return
    }

    setLocationStatus('Acquiring live GPS...')
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const currentLocation = { latitude: position.coords.latitude, longitude: position.coords.longitude }
        if (isInHyderabad(currentLocation)) {
          setLocation(currentLocation)
          setLocationStatus('Live location active')
          loadDashboard(currentLocation)
          return
        }
        setLocationStatus('Outside Hyderabad - center active')
        loadDashboard(hyderabadLocation)
      },
      () => {
        setLocationStatus('Location unavailable - center active')
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
            isRouting={isRouting}
            onLocationSelect={handleLocationSelect}
            onNavigateToTab={setActiveTab}
            isSevereWeather={isSevereWeather}
            t={t}
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
            onCalculateRoute={() => calculateRouteForFacility(selectedFacility)}
            onLocationSelect={handleLocationSelect}
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

        {activeTab === 'about' && <AboutTab />}
      </main>

      {/* Floating AI Safety Assistant in Bottom Right */}
      <AIAssistantChat />

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
