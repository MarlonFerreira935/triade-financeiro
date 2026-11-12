import { Download } from 'lucide-react';
import { API } from '../../../lib/api';
import { Button } from '../../ui/button';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '../../ui/dialog';
import { downloadReceipt } from './ReceiptList';

export const ReceiptModals = ({ preview, setPreview, remove, setRemove, onDelete, deleting }) => <>
  <Dialog open={Boolean(preview)} onOpenChange={open => { if (!open) setPreview(null); }}><DialogContent className="finance-modal receipt-viewer" data-testid="receipt-preview-modal"><DialogTitle>{preview?.filename}</DialogTitle><DialogDescription>Comprovante original arquivado</DialogDescription>
    {preview?.content_type.startsWith('image') ? <img src={`${API}/receipts/${preview.id}/file`} alt="Comprovante original"/> : preview && <iframe src={`${API}/receipts/${preview.id}/file`} title="Comprovante PDF"/>}
    <Button variant="outline" data-testid="preview-download" onClick={() => downloadReceipt(preview)}><Download size={15}/>Baixar original</Button>
  </DialogContent></Dialog>
  <Dialog open={Boolean(remove)} onOpenChange={open => { if (!open && !deleting) setRemove(null); }}><DialogContent className="finance-modal" data-testid="delete-receipt-modal"><DialogTitle>Excluir comprovante?</DialogTitle><DialogDescription>Este documento será removido do arquivo de comprovantes.</DialogDescription><Button variant="destructive" disabled={deleting} data-testid="delete-receipt-confirm" onClick={onDelete}>{deleting ? 'Excluindo...' : 'Excluir comprovante'}</Button></DialogContent></Dialog>
</>;