import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from '../services/api'

/**
 * Standard loading / error / empty / success handling for a GET call.
 * `deps` controls refetching; `enabled: false` defers the call.
 */
export function useApi(fetcher, deps = [], { enabled = true, fallback = 'Request failed.' } = {}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState(null)
  const mounted = useRef(true)
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  useEffect(() => {
    if (!enabled) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    fetcher()
      .then((result) => mounted.current && setData(result))
      .catch((err) => mounted.current && setError(errorMessage(err, fallback)))
      .finally(() => mounted.current && setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])
  return { data, loading, error, reload, setData }
}
