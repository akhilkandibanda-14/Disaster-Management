import { useCallback, useEffect, useRef, useState } from 'react'
import {
  beginLatestRequest,
  invalidateLatestRequest,
  isLatestRequest,
  isValidCoordinate,
  validateRouteResponse
} from './evacuationFlow'

export default function useEvacuationRoute({ location, request, onError }) {
  const [route, setRoute] = useState(null)
  const [isRouting, setIsRouting] = useState(false)
  const requestRef = useRef({ id: 0, controller: null })
  const isMountedRef = useRef(true)

  const cancelRoute = useCallback(() => {
    invalidateLatestRequest(requestRef.current)
    setRoute(null)
    setIsRouting(false)
  }, [])

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      invalidateLatestRequest(requestRef.current)
    }
  }, [])

  const calculateRouteForFacility = useCallback(async (facility) => {
    if (!facility) return

    const { id: requestId, controller } = beginLatestRequest(requestRef.current)
    const routeLocation = location
    setIsRouting(true)
    setRoute(null)
    onError('')

    try {
      const destination = { latitude: facility.latitude, longitude: facility.longitude }
      if (!isValidCoordinate(destination)) {
        throw new Error('Selected facility has no usable coordinates.')
      }

      const facilityId = facility.facility_id || facility.id || facility.shelter_id
      const payload = {
        origin: { latitude: routeLocation.latitude, longitude: routeLocation.longitude },
        destination,
        compute_alternatives: false
      }
      if (facilityId) payload.facility_id = String(facilityId)

      const data = await request('/evacuation-route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      })
      const validatedData = validateRouteResponse(data, routeLocation, destination, facilityId)
      if (isMountedRef.current && isLatestRequest(requestRef.current, requestId)) {
        setRoute(validatedData)
      }
    } catch (routeError) {
      if (routeError.name === 'AbortError') return
      if (isMountedRef.current && isLatestRequest(requestRef.current, requestId)) {
        onError(routeError.message)
      }
    } finally {
      if (isMountedRef.current && isLatestRequest(requestRef.current, requestId)) {
        setIsRouting(false)
      }
    }
  }, [location, onError, request])

  return { route, isRouting, calculateRouteForFacility, cancelRoute }
}
