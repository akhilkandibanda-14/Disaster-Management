import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

test('Nearby Hospital Discovery — Frontend & Data Integrity Audit', async (t) => {
  const baseDir = fs.existsSync('src') ? '.' : 'frontend'
  const rootDir = fs.existsSync('src') ? '..' : '.'

  const routesTabPath = path.resolve(baseDir, 'src/components/tabs/RoutesTab.jsx')
  const riskMapPath = path.resolve(baseDir, 'src/components/RiskMap.jsx')
  const appPath = path.resolve(baseDir, 'src/App.jsx')
  const osmDataPath = path.resolve(rootDir, 'data/raw/emergency_facilities/osm_hyderabad_hospitals.json')

  const routesTabContent = fs.readFileSync(routesTabPath, 'utf-8')
  const riskMapContent = fs.readFileSync(riskMapPath, 'utf-8')
  const appContent = fs.readFileSync(appPath, 'utf-8')
  const osmData = JSON.parse(fs.readFileSync(osmDataPath, 'utf-8'))

  await t.test('1. Genuine OpenStreetMap hospital dataset is populated and structurally valid', () => {
    assert.ok(Array.isArray(osmData), 'Dataset must be an array')
    assert.ok(osmData.length >= 25, `Expected at least 25 OSM hospitals, found ${osmData.length}`)

    for (const h of osmData) {
      assert.ok(h.id, 'Hospital must have an id')
      assert.ok(h.name && h.name.trim().length > 0, `Hospital ${h.id} missing name`)
      assert.ok(Number.isFinite(h.latitude), `Invalid latitude for ${h.name}`)
      assert.ok(Number.isFinite(h.longitude), `Invalid longitude for ${h.name}`)
      // Hyderabad bounds check
      assert.ok(h.latitude >= 17.2 && h.latitude <= 17.6, `${h.name} latitude ${h.latitude} outside Hyderabad bounds`)
      assert.ok(h.longitude >= 78.2 && h.longitude <= 78.7, `${h.name} longitude ${h.longitude} outside Hyderabad bounds`)
      assert.equal(h.source, 'OpenStreetMap', 'Source must be OpenStreetMap')
    }
  })

  await t.test('2. RoutesTab provides a dedicated "Nearby Hospital Candidates (OSM)" section', () => {
    assert.ok(
      routesTabContent.includes('Nearby Hospital Candidates (OSM)'),
      'RoutesTab must contain a dedicated Nearby Hospital Candidates section'
    )
    assert.ok(
      routesTabContent.includes('nearby-radius-select'),
      'RoutesTab must include a search radius select input'
    )
    assert.ok(
      routesTabContent.includes('onRefreshNearbyHospitals'),
      'RoutesTab must support refreshing nearby hospital candidates'
    )
  })

  await t.test('3. RoutesTab enforces truth-in-data: UNVERIFIED labels and emergency notices', () => {
    assert.ok(
      routesTabContent.includes('UNVERIFIED'),
      'RoutesTab must display prominent UNVERIFIED badges on OSM candidates'
    )
    assert.ok(
      routesTabContent.includes('Verification Notice'),
      'RoutesTab must display a clear verification notice'
    )
    assert.ok(
      routesTabContent.includes('108 / 112'),
      'RoutesTab must remind citizens to confirm via official emergency lines (108 / 112)'
    )
    assert.ok(
      !routesTabContent.includes('Safe Hospital'),
      'RoutesTab must never claim unverified candidates are "Safe Hospital"'
    )
  })

  await t.test('4. RoutesTab handles loading, empty, and error states gracefully', () => {
    assert.ok(
      routesTabContent.includes('Searching nearby OpenStreetMap healthcare facilities...'),
      'RoutesTab must display loading state text'
    )
    assert.ok(
      routesTabContent.includes('No hospital candidates discovered within'),
      'RoutesTab must display an empty state when 0 candidates found'
    )
    assert.ok(
      routesTabContent.includes('nearbyError'),
      'RoutesTab must render nearbyError alert banner'
    )
  })

  await t.test('5. Existing curated facilities and shelter selectors remain intact', () => {
    assert.ok(
      routesTabContent.includes('Available Destination Facilities'),
      'Existing curated destination facilities panel must remain intact'
    )
    assert.ok(
      routesTabContent.includes('filterType === \'SHELTER\''),
      'Shelter filter pill must remain intact'
    )
    assert.ok(
      routesTabContent.includes('filterType === \'HOSPITAL\''),
      'Curated hospital filter pill must remain intact'
    )
  })

  await t.test('6. App.jsx integrates nearby hospital discovery API and state', () => {
    assert.ok(
      appContent.includes('/emergency-facilities/nearby-hospitals'),
      'App.jsx must query the nearby-hospitals API endpoint'
    )
    assert.ok(
      appContent.includes('nearbySearchRadius'),
      'App.jsx must maintain nearby search radius state'
    )
    assert.ok(
      appContent.includes('nearbyHospitalsLoading'),
      'App.jsx must manage nearby loading state'
    )
    assert.ok(
      appContent.includes('fetchNearbyHospitals'),
      'App.jsx must define fetchNearbyHospitals function'
    )
  })

  await t.test('7. RiskMap renders nearby hospital markers and UNVERIFIED disclosures in popups', () => {
    assert.ok(
      riskMapContent.includes('nearbyHospitals'),
      'RiskMap must accept nearbyHospitals prop'
    )
    assert.ok(
      riskMapContent.includes('is_osm_candidate') || riskMapContent.includes('allFacilities'),
      'RiskMap must map nearby hospital candidates'
    )
    assert.ok(
      riskMapContent.includes('UNVERIFIED'),
      'RiskMap popup must display UNVERIFIED badge'
    )
  })
})
