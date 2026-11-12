import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import { api, errorText } from '../lib/api';

export function useTransactionForm({ open, initial, month, accounts, onSaved, onClose }) {
  const [form, setForm] = useState({});
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (open) setForm(initial ? { ...initial, amount: initial.amount || '' } : {
      description: '', amount: '', type: 'despesa', account_id: '50', date: `${month}-01`, note: '',
    });
  }, [open, initial, month]);
  const accountOptions = useMemo(() => accounts.filter(account => account.type === form.type), [accounts, form.type]);
  const setField = useCallback((key, value) => setForm(previous => ({ ...previous, [key]: value })), []);
  const setType = useCallback(type => setForm(previous => ({ ...previous, type, account_id: type === 'receita' ? '4' : '50' })), []);
  const submit = async event => {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    try {
      const body = { description: form.description, amount: Number(form.amount), date: form.date,
        account_id: form.account_id, type: form.type, note: form.note || '', receipt_id: form.receipt_id || null };
      if (form.id) await api.put(`/transactions/${form.id}`, body);
      else await api.post('/transactions', body);
      if (mounted.current) { toast.success('Lançamento salvo. Sua DRE foi atualizada.'); onSaved(form.date.slice(0, 7)); onClose(); }
    } catch (error) {
      if (mounted.current) toast.error(errorText(error));
    } finally {
      submitting.current = false;
      if (mounted.current) setBusy(false);
    }
  };
  return { form, busy, accountOptions, setField, setType, submit };
}