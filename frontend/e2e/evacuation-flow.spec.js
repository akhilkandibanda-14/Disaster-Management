import { expect, test } from '@playwright/test'

const location = { latitude: 17.385, longitude: 78.4867 }
const facilities = [
  { id: 'A', name: 'Shelter A', latitude: 17.4, longitude: 78.5, facility_type: 'SHELTER', distance_km: 1.2 },
  { id: 'B', name: 'Shelter B', latitude: 17.41, longitude: 78.51, facility_type: 'SHELTER', distance_km: 2.3 },
]

const routeFor = (facility, overrides = {}) => ({
  route_status: 'ROUTE_AVAILABLE',
  facility_id: facility.id,
  geometry: [
    [location.longitude, location.latitude],
    [facility.longitude, facility.latitude],
  ],
  route_distance_km: facility.id === 'A' ? 1.23 : 2.34,
  road_condition_status: 'CLEAR',
  ...overrides,
})

async function mockDashboard(page) {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition: (_success, error) => error({ code: 1 }) },
    })
  })
  await page.route('**/health', route => route.fulfill({ json: { status: 'ok', demo_mode: false } }))
  await page.route('**/shelters/recommended**', route => route.fulfill({ json: { recommendations: [facilities[0]] } }))
  await page.route('**/shelters', route => route.fulfill({ json: { shelters: facilities } }))
  await page.route('**/emergency-facilities**', route => route.fulfill({ json: { facilities: [] } }))
  await page.route('**/weather**', route => route.fulfill({ json: {} }))
  await page.route('**/risk-map**', route => route.fulfill({ json: {} }))
  await page.route('**/disaster-alerts', route => route.fulfill({ json: [] }))
  await page.route('**/road-conditions', route => route.fulfill({ json: [] }))
  await page.route('**/gauges', route => route.fulfill({ json: [] }))
  await page.route('**/hydrology/**', route => route.fulfill({ json: {} }))
  await page.route('**/flood-hazards/check-location**', route => route.fulfill({ json: {} }))
  await page.route('**/flood-hazards', route => route.fulfill({ json: { hazards: [] } }))
  await page.route('**/incidents', route => route.fulfill({ json: { incidents: [] } }))
  await page.goto('/')
  await page.getByRole('button', { name: /Evacuation Routes/ }).click()
  await expect(page.getByText('Shelter A').last()).toBeVisible()
}

function facilityRow(page, name) {
  return page.locator('.facility-selection-item').filter({ hasText: name })
}

test.describe('browser evacuation flow', () => {
  test('prevents stale facility A from replacing facility B', async ({ page }) => {
    const pending = []
    await page.route('**/evacuation-route', route => new Promise(resolve => {
      pending.push({
        route,
        body: JSON.parse(route.request().postData()),
        resolve: async (response) => {
          await route.fulfill({ json: response })
          resolve()
        },
      })
    }))
    await mockDashboard(page)

    await facilityRow(page, 'Shelter A').click()
    await page.getByRole('button', { name: 'Plan Route on OSM Network' }).click()
    await facilityRow(page, 'Shelter B').click()
    await page.getByRole('button', { name: 'Plan Route on OSM Network' }).click()
    await expect.poll(() => pending.length).toBe(2)

    await pending[1].resolve(routeFor(facilities[1]))
    await expect(page.getByText('2.34 km')).toBeVisible()
    expect(await page.getByText('Shelter B').count()).toBeGreaterThan(0)
    expect(await page.getByText('1.23 km').count()).toBe(0)

    await pending[0].route.abort().catch(() => {})
    await expect(page.getByText('2.34 km')).toBeVisible()
  })

  test('clears route state and presents honest failure and safety states', async ({ page }) => {
    let response = routeFor(facilities[0])
    await page.route('**/evacuation-route', route => {
      if (response.error) return route.fulfill({ status: 500, json: { detail: response.error } })
      return route.fulfill({ json: response })
    })
    await mockDashboard(page)
    await facilityRow(page, 'Shelter A').click()
    await page.getByRole('button', { name: 'Plan Route on OSM Network' }).click()
    await expect(page.getByText('1.23 km')).toBeVisible()

    await facilityRow(page, 'Shelter B').click()
    expect(await page.getByText('1.23 km').count()).toBe(0)

    response = { route_status: 'NO_SAFE_ROUTE', geometry: [], warning_note: 'All corridors blocked.' }
    await page.getByRole('button', { name: 'Plan Route on OSM Network' }).click()
    await expect(page.getByText('NO SAFE ROUTE FOUND (ALL ACCESS SEVERED)')).toBeVisible()
    expect(await page.getByText('DISTANCE', { exact: true }).count()).toBe(0)
    expect(await page.getByText(/not flood-verified/i).count()).toBe(1)
    expect(await page.getByText('Unverified', { exact: false }).count()).toBeGreaterThan(0)

    response = { error: 'Request failed: 500' }
    await facilityRow(page, 'Shelter A').click()
    await page.getByRole('button', { name: 'Plan Route on OSM Network' }).click()
    await expect(page.getByRole('alert')).toContainText('Request failed: 500')
  })

  test('keeps external navigation explicitly unverified', async ({ page }) => {
    await page.route('**/evacuation-route', route => route.fulfill({ json: routeFor(facilities[0]) }))
    await mockDashboard(page)
    await facilityRow(page, 'Shelter A').click()
    const navigation = page.getByRole('button', { name: /external directions \(not flood-verified\)/i })
    await expect(navigation).toBeVisible()
    await expect(navigation).toBeEnabled()
  })

  test('verifies demo mode button and banner are completely absent from UI', async ({ page }) => {
    await mockDashboard(page)
    await expect(page.locator('#header-demo-mode-btn')).toHaveCount(0)
    await expect(page.locator('#demo-mode-indicator-banner')).toHaveCount(0)
    await expect(page.getByText('DEMO MODE')).toHaveCount(0)
  })
})
