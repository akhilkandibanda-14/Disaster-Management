import { expect, test } from '@playwright/test'

const location = { latitude: 17.385, longitude: 78.4867 }
const nearbyHospitals = [
  {
    facility_id: 'OSM-NODE-2451987334',
    name: 'Fernandez Hospital Bogulkunta',
    latitude: 17.3910,
    longitude: 78.4850,
    distance_km: 0.69,
    source: 'OpenStreetMap (OSM POI)',
    facility_type: 'HOSPITAL',
    data_status: 'PUBLIC_UNVERIFIED',
    verification_status: 'UNVERIFIED',
    operational_status: 'UNKNOWN',
    verification_note: 'OpenStreetMap candidate. Not verified for live casualty intake, open status, or bed capacity.'
  },
  {
    facility_id: 'OSM-NODE-2451987335',
    name: 'Care Hospital Nampally',
    latitude: 17.3920,
    longitude: 78.4720,
    distance_km: 1.74,
    source: 'OpenStreetMap (OSM POI)',
    facility_type: 'HOSPITAL',
    data_status: 'PUBLIC_UNVERIFIED',
    verification_status: 'UNVERIFIED',
    operational_status: 'UNKNOWN',
    verification_note: 'OpenStreetMap candidate. Not verified for live casualty intake, open status, or bed capacity.'
  }
]

async function setupMocks(page) {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition: (_success, error) => error({ code: 1 }) },
    })
  })
  await page.route('**/health', route => route.fulfill({ json: { status: 'ok', demo_mode: false } }))
  await page.route('**/shelters/recommended**', route => route.fulfill({ json: { recommendations: [] } }))
  await page.route('**/shelters', route => route.fulfill({ json: { shelters: [] } }))
  await page.route(/\/emergency-facilities\/nearby-hospitals/, route => route.fulfill({
    json: {
      hospitals: nearbyHospitals,
      total: nearbyHospitals.length,
      origin_latitude: location.latitude,
      origin_longitude: location.longitude,
      radius_km: 5.0,
      source: 'OpenStreetMap (OSM POI Registry)',
      data_status: 'PUBLIC_UNVERIFIED',
      disclaimer: 'Hospital candidates discovered from OpenStreetMap. Facility operational readiness is NOT verified in real time.'
    }
  }))
  await page.route(/\/emergency-facilities(\?.*)?$/, route => {
    if (route.request().url().includes('nearby-hospitals')) {
      return route.fallback()
    }
    return route.fulfill({ json: { facilities: [] } })
  })
  await page.route('**/weather**', route => route.fulfill({ json: {} }))
  await page.route('**/risk-map**', route => route.fulfill({ json: {} }))
  await page.route('**/disaster-alerts', route => route.fulfill({ json: [] }))
  await page.route('**/road-conditions', route => route.fulfill({ json: [] }))
  await page.route('**/gauges', route => route.fulfill({ json: [] }))
  await page.route('**/hydrology/**', route => route.fulfill({ json: {} }))
  await page.route('**/flood-hazards/check-location**', route => route.fulfill({ json: {} }))
  await page.route('**/flood-hazards', route => route.fulfill({ json: { hazards: [] } }))
  await page.route('**/incidents', route => route.fulfill({ json: { incidents: [] } }))
  await page.route('**/evacuation-route', route => route.fulfill({
    json: {
      route_status: 'ROUTE_AVAILABLE',
      facility_id: 'OSM-NODE-2451987334',
      geometry: [
        [location.longitude, location.latitude],
        [78.4850, 17.3910]
      ],
      route_distance_km: 0.85,
      road_condition_status: 'CLEAR',
      warnings: ['Route is computed from static OpenStreetMap road geometry and is not verified safe.']
    }
  }))
}

test.describe('Nearby Hospital Candidates Discovery E2E', () => {
  test('discovers, renders with UNVERIFIED badges, selects, and plans route to nearby hospital candidate', async ({ page }) => {
    await setupMocks(page)
    await page.goto('/')

    // Navigate to Routes tab
    await page.getByRole('button', { name: /Evacuation Routes/ }).click()

    // Verify "Nearby Hospital Candidates (OSM)" section
    const nearbyHeader = page.getByRole('heading', { name: /Nearby Hospital Candidates/i })
    await expect(nearbyHeader).toBeVisible()

    // Verify radius selector is present
    const radiusSelect = page.locator('#nearby-radius-select')
    await expect(radiusSelect).toBeVisible()
    await expect(radiusSelect).toHaveValue('5')

    // Verify truth-in-data warning is visible
    await expect(page.getByText(/Hospital records from OpenStreetMap are unverified/i)).toBeVisible()

    // Verify candidate cards are displayed with UNVERIFIED badge
    const firstHospital = page.getByText('Fernandez Hospital Bogulkunta')
    await expect(firstHospital).toBeVisible()

    const unverifiedBadge = page.locator('.facility-selection-item').filter({ hasText: 'Fernandez Hospital Bogulkunta' }).getByText('UNVERIFIED')
    await expect(unverifiedBadge).toBeVisible()

    // Select the candidate
    const selectBtn = page.locator('.facility-selection-item').filter({ hasText: 'Fernandez Hospital Bogulkunta' }).getByRole('button', { name: /Select/i })
    await selectBtn.click()

    // Verify Destination B is updated
    const destSection = page.locator('.endpoint-item').filter({ hasText: 'DESTINATION' })
    await expect(destSection).toContainText('Fernandez Hospital Bogulkunta')
    await expect(destSection).toContainText('(Unverified)')

    // Plan route
    const planRouteBtn = page.getByRole('button', { name: /Plan Route on OSM Network/i })
    await expect(planRouteBtn).toBeEnabled()
    await planRouteBtn.click()

    // Verify calculated route results
    await expect(page.getByText('0.85 km')).toBeVisible()

    // Capture screenshot
    await page.screenshot({ path: 'test-results/nearby_hospitals_e2e.png' })
  })
})
