import { ArrowUpRight, CheckCircle2, Clock3, Download, FileText, FolderOpen, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, dateLabel, downloadFile, errorText, money } from '../../../lib/api';
import { Button } from '../../ui/button';

export const downloadReceipt = receipt => downloadFile(`/receipts/${receipt.id}/file`, receipt.filename).catch(error => toast.error(errorText(error)));

const ReceiptCard = ({ receipt, onReview, onPreview, onRemove }) => {
  const posted = receipt.status === 'lancado';
  return <article className="receipt-card" data-testid={`receipt-card-${receipt.id}`}>
    <button className="receipt-preview" onClick={() => onPreview(receipt)} data-testid={`preview-receipt-${receipt.id}`}>{receipt.content_type.startsWith('image') ? <img src={`${API}/receipts/${receipt.id}/file`} alt={receipt.filename}/> : <FileText size={48}/>}<span>Visualizar <ArrowUpRight size={14}/></span></button>
    <div className="receipt-details"><div className={`receipt-state ${posted ? 'green' : 'gold'}`} data-testid={`receipt-status-${receipt.id}`}>{posted ? <CheckCircle2 size={13}/> : <Clock3 size={13}/>} {posted ? 'Lançado na DRE' : 'Aguardando conferência'}</div><h3 title={receipt.filename} data-testid={`receipt-filename-${receipt.id}`}>{receipt.filename}</h3><div className="receipt-values"><span>{dateLabel(receipt.date)}</span><strong>{receipt.amount ? money(receipt.amount) : 'Valor a conferir'}</strong></div>
      <div className="receipt-actions">{!posted && <Button variant="outline" data-testid={`review-receipt-${receipt.id}`} onClick={() => onReview({ ...receipt.extraction, receipt_id: receipt.id })}>Conferir dados</Button>}<Button size="icon" variant="ghost" title="Baixar comprovante" data-testid={`download-receipt-${receipt.id}`} onClick={() => downloadReceipt(receipt)}><Download size={15}/></Button>{!posted && <Button size="icon" variant="ghost" title="Excluir comprovante" data-testid={`delete-receipt-${receipt.id}`} onClick={() => onRemove(receipt)}><Trash2 size={15}/></Button>}</div>
    </div>
  </article>;
};

export const ReceiptList = ({ groups, onReview, onPreview, onRemove }) => Object.entries(groups).map(([group, receipts]) => <section className="receipt-group" key={group}>
  <h2 data-testid={`receipt-group-${group}`}><FolderOpen size={17}/>{group}<span>{receipts.length}</span></h2><div className="receipt-grid">{receipts.map(receipt => <ReceiptCard key={receipt.id} receipt={receipt} onReview={onReview} onPreview={onPreview} onRemove={onRemove}/>)}</div>
</section>);