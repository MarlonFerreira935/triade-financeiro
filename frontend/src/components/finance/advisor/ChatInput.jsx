import { Loader2, RotateCcw, Send, ShieldCheck } from 'lucide-react';
import { Button } from '../../ui/button';

export const ChatInput = ({ chat, textareaRef }) => <>
  {chat.failure && <div className="chat-failure" role="alert" data-testid="advisor-error"><p>{chat.failure}</p><Button variant="ghost" disabled={chat.busy} onClick={chat.retry} data-testid="advisor-retry"><RotateCcw size={13}/>Tentar novamente</Button></div>}
  <div className="chat-composer-wrap"><form className="chat-composer" onSubmit={event => { event.preventDefault(); chat.send(); }}>
    <textarea ref={textareaRef} rows={2} value={chat.input} onChange={event => chat.setInput(event.target.value)} disabled={chat.busy || chat.loading} maxLength={4000} aria-label="Pergunta ao consultor financeiro" placeholder="O que você gostaria de entender sobre seu financeiro?" data-testid="advisor-message-input" onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); chat.send(); } }}/>
    <div className="composer-bottom"><span><ShieldCheck size={12}/>{chat.snapshot ? `Dados consultados às ${new Date(chat.snapshot.updated_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}` : 'Dados atualizados a cada pergunta'}</span><button type="submit" title="Enviar pergunta" aria-label="Enviar pergunta" disabled={chat.busy || chat.loading || !chat.input.trim()} data-testid="advisor-send">{chat.busy ? <Loader2 className="spin" size={16}/> : <Send size={16}/>}</button></div>
  </form><p className="advisor-disclaimer" data-testid="advisor-disclaimer">Análise gerencial de apoio. Nenhum lançamento é alterado pelo consultor.</p></div>
</>;