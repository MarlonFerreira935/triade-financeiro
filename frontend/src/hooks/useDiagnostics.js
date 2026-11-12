import { useCallback, useEffect, useRef, useState } from 'react';
import { api, API, errorText } from '../lib/api';
import { isCanceled, readEventStream } from '../lib/stream';

export function useDiagnostics(month) {
  const [state, setState] = useState({ text: '', busy: false, error: '', loading: true });
  const request = useRef(null);
  const generation = useRef(0);
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    request.current = controller;
    const identity = ++generation.current;
    setState({ text: '', busy: false, error: '', loading: true });
    api.get('/diagnostics/latest', { params: { month }, signal: controller.signal })
      .then(response => {
        if (!controller.signal.aborted && generation.current === identity) {
          setState({ text: response.data.text || '', busy: false, error: '', loading: false });
        }
      })
      .catch(error => {
        if (!isCanceled(error) && generation.current === identity) setState(previous => ({ ...previous, loading: false, error: errorText(error) }));
      });
    return () => { mounted.current = false; generation.current += 1; controller.abort(); request.current?.abort(); };
  }, [month]);

  const generate = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    const identity = ++generation.current;
    const current = () => mounted.current && generation.current === identity;
    setState({ text: '', busy: true, error: '', loading: false });
    const timer = setTimeout(() => controller.abort('timeout'), 135000);
    try {
      const response = await fetch(`${API}/diagnostics/stream?month=${month}`, { signal: controller.signal });
      await readEventStream(response, event => {
        if (!current()) return;
        if (event.error) throw new Error(event.error);
        if (event.text) setState(previous => ({ ...previous, text: previous.text + event.text }));
      });
    } catch (error) {
      if (current()) setState(previous => ({ ...previous, error: controller.signal.reason === 'timeout' ? 'A análise demorou mais que o esperado. Tente novamente.' : error.message }));
    } finally {
      clearTimeout(timer);
      if (current()) setState(previous => ({ ...previous, busy: false }));
    }
  }, [month]);
  return { ...state, generate };
}