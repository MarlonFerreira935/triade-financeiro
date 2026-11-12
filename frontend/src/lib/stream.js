/** Parse SSE incrementally; cancel the reader on error or interrupted consumption. */
export async function readEventStream(response, onEvent) {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : 'Não foi possível iniciar a análise.');
  }
  if (!response.body) throw new Error('A conexão não disponibilizou uma resposta.');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let completed = false;
  const dispatch = block => {
    const data = block.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
    if (!data) return;
    const event = JSON.parse(data);
    onEvent(event);
    if (event.type === 'done' || event.done === true) completed = true;
  };
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      buffer = buffer.replace(/\r\n/g, '\n');
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop();
      blocks.forEach(dispatch);
      if (done) break;
    }
    if (buffer.trim()) dispatch(buffer);
    if (!completed) throw new Error('A conexão foi interrompida antes de concluir a resposta.');
  } finally {
    if (!completed) await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

export const isCanceled = error => error?.name === 'AbortError' || error?.name === 'CanceledError' || error?.code === 'ERR_CANCELED';