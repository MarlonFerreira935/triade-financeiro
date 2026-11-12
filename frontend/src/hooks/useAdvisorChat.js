import { useCallback, useEffect, useRef, useState } from 'react';
import { api, API, errorText } from '../lib/api';
import { isCanceled, readEventStream } from '../lib/stream';
import { toast } from 'sonner';

const initialState = () => ({ conversations: [], conversationId: null, messages: [], input: '',
  busy: false, loading: true, failure: '', snapshot: null });

export function useAdvisorChat(month, initialQuestion, onUpdated) {
  const [state, setState] = useState(initialState);
  const stateRef = useRef(state);
  const requestRef = useRef(null);
  const mounted = useRef(false);
  const generation = useRef(0);
  const lastAttempt = useRef(null);
  const historyTarget = useRef(null);
  const update = useCallback(patch => {
    if (!mounted.current) return;
    setState(previous => {
      const next = typeof patch === 'function' ? patch(previous) : { ...previous, ...patch };
      stateRef.current = next;
      return next;
    });
  }, []);

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    const requestGeneration = ++generation.current;
    requestRef.current = controller;
    const startState = { ...initialState(), input: initialQuestion };
    lastAttempt.current = null;
    historyTarget.current = null;
    stateRef.current = startState;
    setState(startState);
    const load = async () => {
      try {
        const list = await api.get('/advisor/conversations', { params: { month }, signal: controller.signal });
        if (controller.signal.aborted || generation.current !== requestGeneration) return;
        update({ conversations: list.data });
        if (list.data.length && !initialQuestion) {
          const { data } = await api.get(`/advisor/conversations/${list.data[0].id}`, { signal: controller.signal });
          if (!controller.signal.aborted && generation.current === requestGeneration) {
            update({ conversationId: data.id, messages: data.messages });
          }
        }
      } catch (error) {
        if (!isCanceled(error) && !controller.signal.aborted) update({ failure: errorText(error) });
      } finally {
        if (!controller.signal.aborted && generation.current === requestGeneration) update({ loading: false });
      }
    };
    load();
    return () => { mounted.current = false; generation.current += 1; controller.abort(); requestRef.current?.abort(); };
  }, [month, initialQuestion, update]);

  const setInput = useCallback(input => update({ input }), [update]);
  const newConversation = useCallback(() => {
    if (stateRef.current.busy) return;
    requestRef.current?.abort();
    generation.current += 1;
    lastAttempt.current = null;
    historyTarget.current = null;
    update({ conversationId: null, messages: [], input: '', failure: '', snapshot: null, loading: false });
  }, [update]);

  const selectConversation = useCallback(async id => {
    if (stateRef.current.busy) return;
    lastAttempt.current = null;
    historyTarget.current = id;
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    const requestGeneration = ++generation.current;
    update({ loading: true, failure: '' });
    try {
      const { data } = await api.get(`/advisor/conversations/${id}`, { signal: controller.signal });
      if (generation.current === requestGeneration && !controller.signal.aborted) {
        lastAttempt.current = null;
        historyTarget.current = null;
        update({ conversationId: data.id, messages: data.messages, snapshot: null });
      }
    } catch (error) {
      if (!isCanceled(error) && generation.current === requestGeneration) update({ failure: errorText(error) });
    } finally {
      if (generation.current === requestGeneration && !controller.signal.aborted) update({ loading: false });
    }
  }, [update]);

  const deleteConversation = useCallback(async id => {
    await api.delete(`/advisor/conversations/${id}`);
    if (!mounted.current) return;
    if (stateRef.current.conversationId === id) newConversation();
    update(previous => ({ ...previous, conversations: previous.conversations.filter(item => item.id !== id) }));
    toast.success('Conversa excluída.');
  }, [newConversation, update]);

  // Recovery is not initialization: keep the active answer and the user's current draft.
  const reloadHistory = useCallback(async () => {
    const current = stateRef.current;
    if (current.busy || current.loading) return;
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    const requestGeneration = ++generation.current;
    const stillCurrent = () => mounted.current && generation.current === requestGeneration && !controller.signal.aborted;
    update({ loading: current.messages.length === 0, failure: '' });
    try {
      const list = await api.get('/advisor/conversations', { params: { month }, signal: controller.signal });
      if (!stillCurrent()) return;
      update({ conversations: list.data });
      const target = current.conversationId || (!current.input ? list.data[0]?.id : null);
      if (target) {
        const response = await api.get(`/advisor/conversations/${target}`, { signal: controller.signal });
        if (stillCurrent()) update({ conversationId: response.data.id, messages: response.data.messages });
      }
    } catch (error) {
      if (stillCurrent() && !isCanceled(error)) update({ failure: errorText(error) });
    } finally {
      if (stillCurrent()) update({ loading: false });
    }
  }, [month, update]);

  const send = useCallback(async (question, retry = false) => {
    const current = stateRef.current;
    const text = (question ?? current.input).trim();
    if (!text || current.busy || current.loading) return;
    // Lock synchronously; two clicks before React renders cannot start two streams.
    stateRef.current = { ...current, busy: true };
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    const requestGeneration = ++generation.current;
    const attempt = retry ? lastAttempt.current : null;
    const userId = attempt?.localUserId || crypto.randomUUID();
    const assistantId = crypto.randomUUID();
    const retryId = attempt?.serverUserId || null;
    lastAttempt.current = { text, localUserId: userId, serverUserId: retryId, assistantId };
    update(previous => ({ ...previous, busy: true, input: '', failure: '', messages: [
      ...previous.messages.filter(message => message.id !== attempt?.assistantId),
      ...(!attempt ? [{ id: userId, role: 'user', content: text, status: 'complete' }] : []),
      { id: assistantId, role: 'assistant', content: '', status: 'streaming' },
    ] }));
    const timer = setTimeout(() => controller.abort('timeout'), 135000);
    const stillCurrent = () => mounted.current && generation.current === requestGeneration;
    let answerComplete = false;
    try {
      const response = await fetch(`${API}/advisor/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, month, conversation_id: current.conversationId, retry_message_id: retryId }), signal: controller.signal });
      await readEventStream(response, event => {
        if (!stillCurrent()) return;
        if (event.type === 'error') throw new Error(event.message);
        if (event.type === 'meta') {
          lastAttempt.current.serverUserId = event.user_message_id;
          update({ conversationId: event.conversation_id, snapshot: event });
        }
        if (event.type === 'delta') update(previous => ({ ...previous, messages: previous.messages.map(message =>
          message.id === assistantId ? { ...message, content: message.content + event.text } : message) }));
        if (event.type === 'done') {
          answerComplete = true;
          update(previous => ({ ...previous, messages: previous.messages.map(message =>
            message.id === assistantId ? { ...message, status: 'complete', month } : message) }));
        }
      });
      if (!stillCurrent()) return;
      const list = await api.get('/advisor/conversations', { params: { month }, signal: controller.signal });
      if (stillCurrent()) { update({ conversations: list.data }); onUpdated?.(); }
    } catch (error) {
      if (stillCurrent()) {
        if (answerComplete) {
          lastAttempt.current = null;
          update({ failure: 'A resposta foi concluída, mas o histórico não pôde ser atualizado. Tente carregar o histórico novamente.' });
          return;
        }
        const failure = controller.signal.reason === 'timeout' ? 'A análise demorou mais que o esperado. Tente novamente.' : error.message;
        update(previous => ({ ...previous, failure, messages: previous.messages.map(message =>
          message.id === assistantId ? { ...message, status: 'failed' } : message) }));
      }
    } finally {
      clearTimeout(timer);
      if (stillCurrent()) update({ busy: false });
    }
  }, [month, onUpdated, update]);

  const retry = useCallback(() => {
    if (stateRef.current.busy || stateRef.current.loading) return;
    if (lastAttempt.current) { send(lastAttempt.current.text, true); return; }
    if (historyTarget.current) { selectConversation(historyTarget.current); return; }
    reloadHistory();
  }, [send, selectConversation, reloadHistory]);
  return { ...state, setInput, send, retry, newConversation, selectConversation, deleteConversation };
}