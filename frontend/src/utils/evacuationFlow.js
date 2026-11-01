export const ROUTE_ENDPOINT_TOLERANCE = 0.001

export const isValidCoordinate = (coordinate) => (
  coordinate &&
  Number.isFinite(coordinate.latitude) &&
  Number.isFinite(coordinate.longitude) &&
  coordinate.latitude >= -90 &&
  coordinate.latitude <= 90 &&
  coordinate.longitude >= -180 &&
  coordinate.longitude <= 180
)

const isCloseCoordinate = (actual, expected) => (
  Array.isArray(actual) &&
  actual.length === 2 &&
  Number.isFinite(actual[0]) &&
  Number.isFinite(actual[1]) &&
  Math.abs(actual[0] - expected.longitude) <= ROUTE_ENDPOINT_TOLERANCE &&
  Math.abs(actual[1] - expected.latitude) <= ROUTE_ENDPOINT_TOLERANCE
)

const isValidGeometry = (geometry) => (
  Array.isArray(geometry) &&
  geometry.length >= 2 &&
  geometry.every(point => (
    Array.isArray(point) &&
    point.length === 2 &&
    Number.isFinite(point[0]) &&
    Number.isFinite(point[1]) &&
    point[0] >= -180 &&
    point[0] <= 180 &&
    point[1] >= -90 &&
    point[1] <= 90
  ))
)

export const validateRouteResponse = (data, origin, destination, facilityId) => {
  if (!data || typeof data !== 'object') {
    throw new Error('Routing service returned an invalid response.')
  }
  if (!isValidCoordinate(origin) || !isValidCoordinate(destination)) {
    throw new Error('Routing service received invalid route coordinates.')
  }
  if (facilityId && data.facility_id && String(data.facility_id) !== String(facilityId)) {
    throw new Error('Routing service returned a route for a different destination.')
  }

  if (data.route_status === 'NO_SAFE_ROUTE') {
    if (!Array.isArray(data.geometry) || data.geometry.length !== 0) {
      throw new Error('Routing service returned an invalid no-route geometry.')
    }
    return data
  }

  if (data.route_status !== 'ROUTE_AVAILABLE') {
    throw new Error(data.warnings?.[0] || 'No usable route is available for this destination.')
  }
  if (!isValidGeometry(data.geometry)) {
    throw new Error('Routing service returned an empty route geometry.')
  }
  if (
    !isCloseCoordinate(data.geometry[0], origin) ||
    !isCloseCoordinate(data.geometry[data.geometry.length - 1], destination)
  ) {
    throw new Error('Routing service returned a route for different coordinates.')
  }
  return data
}

export const beginLatestRequest = (requestRef) => {
  requestRef.controller?.abort()
  const id = requestRef.id + 1
  const controller = new AbortController()
  requestRef.id = id
  requestRef.controller = controller
  return { id, controller }
}

export const invalidateLatestRequest = (requestRef) => {
  requestRef.controller?.abort()
  requestRef.id += 1
  requestRef.controller = null
}

export const isLatestRequest = (requestRef, id) => requestRef.id === id
