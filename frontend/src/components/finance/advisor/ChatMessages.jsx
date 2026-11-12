import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Check, Loader2 } from 'lucide-react';
import { monthLabel } from '../../../lib/api';
import { ChatWelcome } from './ChatWelcome';

const MARKDOWN_ELEMENTS = ['p', 'strong', 'em', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'blockquote', 'code', 'br', 'hr'];

const AssistantContent = ({ message, index }) => <>
  <div className="message-markdown" data-testid={`assistant-content-${index}`}>
    {message.content ? <ReactMarkdown allowedElements={MARKDOWN_ELEMENTS} unwrapDisallowed>{message.content}</ReactMarkdown> : message.status === 'streaming' ? <span className="thinking"><i/><i/><i/>Analisando seus dados</span> : <span className="muted">A resposta não foi concluída.</span>}
    {message.status === 'streaming' && message.content && <span className="typing-cursor"/>}
  </div>
  {['failed', 'interrupted'].includes(message.status) && <span className="answer-incomplete" data-testid={`answer-incomplete-${index}`}>Resposta incompleta · não utilize como análise concluída</span>}
</>;

const ChatMessage = ({ message, index, month }) => <article className={`chat-message ${message.role}`} data-testid={`chat-message-${index}`}>
  <div className="message-person">{message.role === 'assistant' ? <img src="/brand/symbol.png" alt="Tríade"/> : <span>TP</span>}</div>
  <div className="message-content"><div className="message-byline"><strong>{message.role === 'assistant' ? 'Consultor Tríade' : 'Você'}</strong>{message.role === 'assistant' && <span>IA FINANCEIRA</span>}</div>
    {message.role === 'assistant' ? <AssistantContent message={message} index={index}/> : <p className="user-message-text">{message.content}</p>}
    {message.role === 'assistant' && message.status === 'complete' && <div className="answer-source" data-testid={`answer-source-${index}`}><Check size={11}/> DRE e lançamentos · {monthLabel(message.month || month)}{message.data_as_of && <span> · {new Date(message.data_as_of).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>}</div>}
  </div>
</article>;

export const ChatMessages = ({ chat, month, totals }) => {
  const scroll = useRef(null);
  useEffect(() => {
    scroll.current?.scrollTo({ top: scroll.current.scrollHeight, behavior: 'smooth' });
  }, [chat.messages, chat.busy]);
  let content = <ChatWelcome totals={totals} send={chat.send}/>;
  if (chat.loading) content = <div className="chat-loading"><Loader2 className="spin" size={20}/><span>Carregando conversas...</span></div>;
  else if (chat.messages.length) content = <div className="chat-messages">{chat.messages.map((message, index) => <ChatMessage key={message.id} message={message} index={index} month={month}/>)}</div>;
  return <div className="chat-scroll" ref={scroll} data-testid="advisor-message-list">{content}</div>;
};