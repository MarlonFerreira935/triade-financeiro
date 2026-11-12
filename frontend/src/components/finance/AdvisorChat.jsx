import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { errorText } from '../../lib/api';
import { useAdvisorChat } from '../../hooks/useAdvisorChat';
import { ChatHeader } from './advisor/ChatHeader';
import { ChatMessages } from './advisor/ChatMessages';
import { ChatInput } from './advisor/ChatInput';

export const AdvisorChat = ({ month, totals, onUpdated }) => {
  const [params, setParams] = useSearchParams();
  const question = params.get('pergunta') || '';
  // Capture the incoming draft once; clearing the URL must not reset an active conversation.
  const [initialQuestion] = useState(question);
  const chat = useAdvisorChat(month, initialQuestion, onUpdated);
  const [deleting, setDeleting] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const textarea = useRef(null);
  const { setInput } = chat;
  useEffect(() => {
    if (!question) return;
    setInput(question);
    setParams(previous => { const next = new URLSearchParams(previous); next.delete('pergunta'); return next; }, { replace: true });
    textarea.current?.focus();
  }, [question, setInput, setParams]);
  const remove = async () => {
    if (!deleting || deleteBusy) return;
    const id = deleting.id;
    setDeleteBusy(true);
    try { await chat.deleteConversation(id); setDeleting(current => current?.id === id ? null : current); }
    catch (error) { toast.error(errorText(error)); }
    finally { setDeleteBusy(false); }
  };
  const newConversation = () => { chat.newConversation(); textarea.current?.focus(); };
  return <section className="advisor-chat" data-testid="advisor-chat">
    <ChatHeader chat={chat} month={month} totals={totals} onDelete={setDeleting} onNew={newConversation}/>
    <ChatMessages chat={chat} month={month} totals={totals}/>
    <ChatInput chat={chat} textareaRef={textarea}/>
    <Dialog open={Boolean(deleting)} onOpenChange={open => { if (!open && !deleteBusy) setDeleting(null); }}><DialogContent className="finance-modal" data-testid="delete-conversation-modal"><DialogTitle>Excluir esta conversa?</DialogTitle><DialogDescription>As mensagens serão removidas do histórico. Seus dados financeiros não serão alterados.</DialogDescription><div className="modal-footer"><Button variant="outline" disabled={deleteBusy} onClick={() => setDeleting(null)} data-testid="delete-conversation-cancel">Cancelar</Button><Button variant="destructive" disabled={deleteBusy} onClick={remove} data-testid="delete-conversation-confirm">{deleteBusy ? 'Excluindo...' : 'Excluir conversa'}</Button></div></DialogContent></Dialog>
  </section>;
};