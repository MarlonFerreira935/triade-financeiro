import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { api, errorText } from '../lib/api';
import { isCanceled } from '../lib/stream';

export function useReceiptUpload(month, onChanged, onReview) {
  const [busy, setBusy] = useState(false);
  const request = useRef(null);
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; request.current?.abort(); };
  }, [month]);
  const upload = useCallback(async file => {
    if (!file || request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('month', month);
      const { data } = await api.post('/receipts', form, { signal: controller.signal });
      if (!mounted.current || controller.signal.aborted) return;
      onChanged();
      if (data.warning) toast.info(data.warning);
      else toast.success('Comprovante salvo e identificado. Confira os dados.');
      onReview({ ...data.extraction, receipt_id: data.id });
    } catch (error) {
      if (mounted.current && !isCanceled(error)) toast.error(errorText(error));
    } finally {
      if (request.current === controller) request.current = null;
      if (mounted.current) setBusy(false);
    }
  }, [month, onChanged, onReview]);
  return { upload, busy };
}