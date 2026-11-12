import { Check, FileCheck2, Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { useTransactionForm } from '../../hooks/useTransactionForm';
import { TransactionFields } from './TransactionFields';

function titleFor(form) {
  if (form.id) return 'Editar lançamento';
  return form.receipt_id ? 'Conferir comprovante' : 'Novo lançamento';
}

export const TransactionModal = props => {
  const fields = useTransactionForm(props);
  const { form, busy, submit } = fields;
  return <Dialog open={props.open} onOpenChange={open => { if (!open && !busy) props.onClose(); }}><DialogContent className="finance-modal" data-testid="transaction-modal">
    <DialogHeader><div className="modal-symbol"><FileCheck2 size={22}/></div><DialogTitle data-testid="transaction-modal-title">{titleFor(form)}</DialogTitle><DialogDescription>{form.receipt_id ? 'Confira os dados identificados antes de confirmar.' : 'Um novo movimento no financeiro da Tríade.'}</DialogDescription></DialogHeader>
    <form onSubmit={submit} className="finance-form"><TransactionFields {...fields}/><div className="modal-footer"><Button type="button" variant="outline" disabled={busy} onClick={props.onClose} data-testid="transaction-cancel">Cancelar</Button><Button type="submit" className="gold-button" disabled={busy} data-testid="transaction-save">{busy ? <Loader2 className="spin" size={16}/> : <Check size={16}/>} {busy ? 'Salvando...' : 'Confirmar lançamento'}</Button></div></form>
  </DialogContent></Dialog>;
};