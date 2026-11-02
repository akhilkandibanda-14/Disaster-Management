import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  beginLatestRequest,
  invalidateLatestRequest,
  isLatestRequest,
  isValidCoordinate,
  validateRouteResponse
} from './src/utils/evacuationFlow.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const appContent = fs.readFileSync(path.join(__dirname, 'src', 'App.jsx'), 'utf8')
const routeHookContent = fs.readFileSync(path.join(__dirname, 'src', 'utils', 'useEvacuationRoute.js'), 'utf8')
const routesContent = fs.readFileSync(path.join(__dirname, 'src', 'components', 'tabs', 'RoutesTab.jsx'), 'utf8')
const overviewContent = fs.readFileSync(path.join(__dirname, 'src', 'components', 'tabs', 'OverviewTab.jsx'), 'utf8')
const routingContent = fs.readFileSync(path.join(__dirname, '..', 'backend', 'app', 'services', 'routing.py'), 'utf8')

const origin = { latitude: 17.385, longitude: 78.4867 }
const destination = { latitude: 17.4, longitude: 78.5 }
const availableRoute = {
  route_status: 'ROUTE_AVAILABLE',
  facility_id: 'SHELTER-A',
  geometry: [[origin.longitude, origin.latitude], [78.49, 17.39], [destination.longitude, destination.latitude]]
}

test('route response validation accepts a complete available route', () => {
  assert.equal(validateRouteResponse(availableRoute, origin, destination, 'SHELTER-A'), availableRoute)
})

test('route response validation rejects malformed, unknown, empty, mismatched, and invalid responses', () => {
  const cases = [
    [null, 'invalid response'],
    [{ route_status: 'ROUTE_AVAILABLE', geometry: [] }, 'empty route geometry'],
    [{ route_status: 'UNKNOWN', geometry: [] }, 'No usable route'],
    [{ ...availableRoute, geometry: [[0, 0], [1, 1]] }, 'different coordinates'],
    [{ ...availableRoute, facility_id: 'SHELTER-B' }, 'different destination'],
    [{ ...availableRoute, geometry: [[origin.longitude, origin.latitude], [NaN, 1], [destination.longitude, destination.latitude]] }, 'empty route geometry'],
    [{ route_status: 'NO_SAFE_ROUTE', geometry: [[origin.longitude, origin.latitude]] }, 'no-route geometry']
  ]

  for (const [response, message] of cases) {
    assert.throws(() => validateRouteResponse(response, origin, destination, 'SHELTER-A'), new RegExp(message))
  }
  assert.throws(
    () => validateRouteResponse(availableRoute, { latitude: 95, longitude: origin.longitude }, destination),
    /invalid route coordinates/
  )
})

test('NO_SAFE_ROUTE is preserved as an explicit empty-geometry result', () => {
  const response = { route_status: 'NO_SAFE_ROUTE', geometry: [], warnings: ['All corridors blocked.'] }
  assert.equal(validateRouteResponse(response, origin, destination), response)
})

test('latest request guard prevents a late shelter A result from replacing shelter B', async () => {
  const requestRef = { id: 0, controller: null }
  let visibleRoute = null
  let resolveA
  let resolveB
  const resultA = new Promise(resolve => { resolveA = resolve })
  const resultB = new Promise(resolve => { resolveB = resolve })
  const requestA = beginLatestRequest(requestRef)
  const requestB = beginLatestRequest(requestRef)

  resolveB({ shelter: 'B' })
  if (isLatestRequest(requestRef, requestB.id)) visibleRoute = await resultB
  resolveA({ shelter: 'A' })
  if (isLatestRequest(requestRef, requestA.id)) visibleRoute = await resultA

  assert.equal(visibleRoute.shelter, 'B')
  assert.equal(requestA.controller.signal.aborted, true)
})

test('location and facility changes invalidate old route requests without surfacing abort errors', () => {
  const requestRef = { id: 0, controller: null }
  const { id } = beginLatestRequest(requestRef)
  invalidateLatestRequest(requestRef)
  assert.equal(requestRef.controller, null)
  assert.equal(isLatestRequest(requestRef, id), false)
  assert.match(routeHookContent, /if \(routeError\.name === 'AbortError'\) return/)
  assert.match(appContent, /cancelRoute\(\)/)
})

test('stale finally blocks cannot clear the current route loading state', () => {
  assert.match(routeHookContent, /if \(isMountedRef\.current && isLatestRequest\(requestRef\.current, requestId\)\) \{\s*setIsRouting\(false\)/)
  assert.match(routeHookContent, /setIsRouting\(true\)/)
  assert.match(routeHookContent, /setRoute\(null\)/)
})

test('route hook re-arms mounted state on effect execution for React Strict Mode compatibility', () => {
  assert.match(
    routeHookContent,
    /useEffect\(\(\)\s*=>\s*\{[\s\S]*?isMountedRef\.current\s*=\s*true/,
    'useEvacuationRoute must re-arm isMountedRef.current = true within useEffect for React Strict Mode remounting'
  )
})

test('facility coordinates are validated before a route request', () => {
  assert.equal(isValidCoordinate(destination), true)
  assert.equal(isValidCoordinate({ latitude: Number.NaN, longitude: destination.longitude }), false)
  assert.match(routeHookContent, /isValidCoordinate\(destination\)/)
})

test('safety presentation keeps candidates, warnings, CLEAR, and NO_SAFE_ROUTE honest', () => {
  assert.match(routesContent, /Candidate listing only|not flood-verified|not verified/)
  assert.match(routesContent, /route\.road_condition_status === 'CLEAR'/)
  assert.match(routesContent, /CURRENT STATUS NOT VERIFIED/)
  assert.match(routesContent, /NO SAFE ROUTE FOUND/)
  assert.match(routesContent, /current flooding, closures, debris and accessibility are not verified/)
  assert.match(overviewContent, /Unavailable/)
  assert.match(overviewContent, /Current status not verified/)
  assert.match(overviewContent, /NO SAFE ROUTE FOUND/)
  assert.match(overviewContent, /Candidate listing only; operational status, capacity, accessibility and flood safety are not independently verified/)
})

test('backend routing contracts retain the five kilometre snap limit and explicit no-safe status', () => {
  assert.match(routingContent, /MAX_SNAP_DISTANCE_KM\s*=\s*5\.0/)
  assert.match(routingContent, /status="NO_SAFE_ROUTE"/)
  assert.match(routingContent, /route_status="ROUTE_AVAILABLE"/)
})
