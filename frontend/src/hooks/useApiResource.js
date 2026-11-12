import { useCallback, useEffect, useState } from 'react';
import { api } from '../lib/api';
import { isCanceled } from '../lib/stream';

/** A request owns its result. A late response can never replace another period's data. */
export function useApiResource(path, params = null, version = 0) {
  const paramsKey = JSON.stringify(params || {});
  const resourceKey = `${path}:${paramsKey}`;
  const [revision, setRevision] = useState(0);
  const requestKey = `${resourceKey}:${version}:${revision}`;
  const [state, setState] = useState({ resourceKey: null, requestKey: null, data: null, loading: true, error: null });
  const reload = useCallback(() => setRevision(value => value + 1), []);
  useEffect(() => {
    if (!path) return undefined;
    const controller = new AbortController();
    setState(previous => ({ ...previous, requestKey, loading: true, error: null }));
    api.get(path, { params: JSON.parse(paramsKey), signal: controller.signal })
      .then(response => {
        if (!controller.signal.aborted) setState({ resourceKey, requestKey, data: response.data, loading: false, error: null });
      })
      .catch(error => {
        if (!isCanceled(error) && !controller.signal.aborted) {
          setState(previous => ({ ...previous, requestKey, loading: false, error }));
        }
      });
    return () => controller.abort();
  }, [path, paramsKey, resourceKey, requestKey]);
  return {
    data: state.resourceKey === resourceKey ? state.data : null,
    loading: Boolean(path) && (state.requestKey !== requestKey || state.loading),
    error: state.requestKey === requestKey ? state.error : null,
    reload,
  };
}