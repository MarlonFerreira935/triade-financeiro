import { useState } from 'react';
import { History, Plus, Trash2 } from 'lucide-react';
import { Button } from '../../ui/button';
import { monthLabel } from '../../../lib/api';

export const ChatHeader = ({ chat, month, totals, onDelete, onNew }) => {
  const [historyOpen, setHistoryOpen] = useState(false);
  const select = id => { setHistoryOpen(false); chat.selectConversation(id); };
  return <><header className="advisor-chat-header">
    <div className="advisor-identity"><span className="advisor-avatar"><img src="/brand/symbol.png" alt="Tríade"/></span><div><strong data-testid="advisor-name">Consultor Tríade</strong><span><i className="online-dot"/> Inteligência a serviço do seu negócio</span></div></div>
    <div className="chat-tools"><div className="chat-history-control"><Button variant="ghost" size="icon" title="Histórico de conversas" data-testid="advisor-history-toggle" disabled={chat.busy} onClick={() => setHistoryOpen(open => !open)}><History size={17}/></Button>
      {historyOpen && <div className="chat-history-popover" data-testid="advisor-history"><div className="history-popover-heading">Conversas · {monthLabel(month)}</div>
        {chat.conversations.length ? chat.conversations.map(item => <div key={item.id} className="chat-history-row"><button className={chat.conversationId === item.id ? 'active' : ''} data-testid={`conversation-select-${item.id}`} onClick={() => select(item.id)}>{item.title}<span>{new Date(item.updated_at).toLocaleDateString('pt-BR')}</span></button><button className="icon-button" title="Excluir conversa" data-testid={`conversation-delete-${item.id}`} onClick={() => onDelete(item)}><Trash2 size={13}/></button></div>) : <p data-testid="advisor-no-history">Nenhuma conversa neste período.</p>}
      </div>}
    </div><Button variant="outline" className="new-chat" data-testid="advisor-new-chat" disabled={chat.busy} onClick={() => { setHistoryOpen(false); onNew(); }}><Plus size={14}/><span>Nova conversa</span></Button></div>
  </header><div className="chat-period"><span className="gold-tag">BASE REAL</span><span data-testid="advisor-period">{monthLabel(month)}</span><span className="chat-records" data-testid="advisor-records">{totals.count} registros na DRE</span></div></>;
};