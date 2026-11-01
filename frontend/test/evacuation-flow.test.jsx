import React, { useCallback, useState } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import RoutesTab from '../src/components/tabs/RoutesTab'
import useEvacuationRoute from '../src/utils/useEvacuationRoute'

vi.mock('../src/components/RiskMap', () => ({
  default: () => <div data-testid="risk-map" />
}))

const location = { latitude: 17.385, longitude: 78.4867 }
const facilities = [
  { id: 'A', name: 'Shelter A', latitude: 17.4, longitude: 78.5, facility_type: 'SHELTER', distance_km: 1.2 },
  { id: 'B', name: 'Shelter B', latitude: 17.41, longitude: 78.51, facility_type: 'SHELTER', distance_km: 2.3 }
]

const routeFor = (facility, overrides = {}) => ({
  route_status: 'ROUTE_AVAILABLE',
  facility_id: facility.id,
  route_distance_km: facility.id === 'A' ? 1.23 : 2.34,
  geometry: [
    [location.longitude, location.latitude],
    [facility.longitude, facility.latitude]
  ],
  road_condition_status: 'CLEAR',
  ...overrides
})

function FlowHarness({ requester, onRequestError = vi.fn(), onOpenNavigation = vi.fn() }) {
  const [selectedFacility, setSelectedFacility] = useState(null)
  const onError = useCallback(onRequestError, [onRequestError])
  const request = useCallback(requester, [requester])
  const { route, isRouting, calculateRouteForFacility, cancelRoute } = useEvacuationRoute({
    location,
    request,
    onError
  })

  const selectFacility = (facility) => {
    cancelRoute()
    setSelectedFacility(facility)
  }

  return (
    <RoutesTab
      location={location}
      facilities={facilities}
      selectedFacility={selectedFacility}
      onFacilitySelect={selectFacility}
      route={route}
      roads={[]}
      floodHazards={[]}
      loading={false}
      isRouting={isRouting}
      onCalculateRoute={() => calculateRouteForFacility(selectedFacility)}
      onOpenNavigation={onOpenNavigation}
      onMyLocation={vi.fn()}
      onLocationSelect={vi.fn()}
    />
  )
}

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function selectFacility(name) {
  const matches = screen.getAllByText(name)
  fireEvent.click(matches[matches.length - 1])
}

function planRoute() {
  fireEvent.click(screen.getByRole('button', { name: 'Plan Route on OSM Network' }))
}

describe('runtime evacuation flow', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('keeps shelter B visible when B resolves before stale A', async () => {
    const pending = new Map()
    const requester = vi.fn((_path, options) => {
      const body = JSON.parse(options.body)
      const request = deferred()
      pending.set(body.facility_id, { ...request, signal: options.signal })
      return request.promise
    })
    render(<FlowHarness requester={requester} />)

    selectFacility('Shelter A')
    planRoute()
    selectFacility('Shelter B')
    planRoute()
    pending.get('B').resolve(routeFor(facilities[1]))
    await screen.findByText('2.34 km')
    pending.get('A').resolve(routeFor(facilities[0]))

    await waitFor(() => {
      expect(screen.getAllByText('Shelter B').length).toBeGreaterThan(0)
      expect(screen.getByText('2.34 km')).toBeInTheDocument()
      expect(screen.queryByText('1.23 km')).not.toBeInTheDocument()
    })
    expect(pending.get('A').signal.aborted).toBe(true)
  })

  it('does not replace B when stale A resolves first', async () => {
    const pending = new Map()
    const requester = vi.fn((_path, options) => {
      const body = JSON.parse(options.body)
      const request = deferred()
      pending.set(body.facility_id, request)
      return request.promise
    })
    render(<FlowHarness requester={requester} />)

    selectFacility('Shelter A')
    planRoute()
    selectFacility('Shelter B')
    planRoute()
    pending.get('A').resolve(routeFor(facilities[0]))
    expect(screen.getByText('Calculating mapped route...')).toBeInTheDocument()
    pending.get('B').resolve(routeFor(facilities[1]))

    await screen.findByText('2.34 km')
    expect(screen.queryByText('1.23 km')).not.toBeInTheDocument()
  })

  it('clears the old route immediately on facility switching and keeps loading current', async () => {
    const pending = new Map()
    const requester = vi.fn((_path, options) => {
      const body = JSON.parse(options.body)
      const request = deferred()
      pending.set(body.facility_id, request)
      return request.promise
    })
    render(<FlowHarness requester={requester} />)

    selectFacility('Shelter A')
    planRoute()
    pending.get('A').resolve(routeFor(facilities[0]))
    await screen.findByText('1.23 km')
    selectFacility('Shelter B')
    planRoute()

    expect(screen.queryByText('1.23 km')).not.toBeInTheDocument()
    expect(screen.getByText('Calculating mapped route...')).toBeInTheDocument()
  })

  it.each([
    ['HTTP error', async (_resolve, reject) => reject(new Error('Request failed: 500')), 'Request failed: 500'],
    ['malformed response', async (resolve) => resolve({ route_status: 'ROUTE_AVAILABLE', geometry: null }), 'Routing service returned an empty route geometry.'],
    ['invalid geometry', async (resolve) => resolve({ ...routeFor(facilities[0]), geometry: [[0, 0], [1, 1]] }), 'Routing service returned a route for different coordinates.'],
    ['facility identity mismatch', async (resolve) => resolve({ ...routeFor(facilities[0]), facility_id: 'B' }), 'Routing service returned a route for a different destination.'],
    ['empty route geometry', async (resolve) => resolve({ route_status: 'ROUTE_AVAILABLE', geometry: [] }), 'Routing service returned an empty route geometry.']
  ])('renders an explicit error for %s', async (_name, settle, message) => {
    const requestError = vi.fn()
    const request = deferred()
    const requester = vi.fn(() => request.promise)
    render(<FlowHarness requester={requester} onRequestError={requestError} />)
    selectFacility('Shelter A')
    planRoute()
    await settle(request.resolve, request.reject, request)

    await waitFor(() => expect(requestError).toHaveBeenLastCalledWith(message))
    expect(screen.queryByText('1.23 km')).not.toBeInTheDocument()
  })

  it('renders NO_SAFE_ROUTE without route geometry or reassuring metrics', async () => {
    const request = deferred()
    const requester = vi.fn(() => request.promise)
    render(<FlowHarness requester={requester} />)
    selectFacility('Shelter A')
    planRoute()
    request.resolve({ route_status: 'NO_SAFE_ROUTE', geometry: [], warnings: ['All corridors blocked.'] })

    expect(await screen.findByText('NO SAFE ROUTE FOUND (ALL ACCESS SEVERED)')).toBeInTheDocument()
    expect(screen.queryByText(/DISTANCE/)).not.toBeInTheDocument()
  })

  it('keeps the external navigation warning visible and delegates navigation', () => {
    const onOpenNavigation = vi.fn()
    render(<FlowHarness requester={vi.fn()} onOpenNavigation={onOpenNavigation} />)
    selectFacility('Shelter A')

    const navigationButton = screen.getByRole('button', { name: /external directions \(not flood-verified\)/i })
    expect(navigationButton).toBeInTheDocument()
    fireEvent.click(navigationButton)
    expect(onOpenNavigation).toHaveBeenCalledTimes(1)
  })

  it('aborts pending work on unmount and never renders the late response', async () => {
    const request = deferred()
    let signal
    const requester = vi.fn((_path, options) => {
      signal = options.signal
      return request.promise
    })
    const view = render(<FlowHarness requester={requester} />)
    selectFacility('Shelter A')
    planRoute()
    view.unmount()
    request.resolve(routeFor(facilities[0]))

    await Promise.resolve()
    expect(signal.aborted).toBe(true)
  })
})
