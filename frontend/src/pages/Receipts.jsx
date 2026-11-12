import { useMemo, useState } from 'react';
import { ListFilter } from 'lucide-react';
import { toast } from 'sonner';
import { api, errorText } from '../lib/api';
import { useApiResource } from '../hooks/useApiResource';
import { useReceiptUpload } from '../hooks/useReceiptUpload';
import { Empty, Loading } from '../components/finance/Shared';
import { Button } from '../components/ui/button';
import { ReceiptUpload } from '../components/finance/receipts/ReceiptUpload';
import { ReceiptList } from '../components/finance/receipts/ReceiptList';
import { ReceiptModals } from '../components/finance/receipts/ReceiptModals';

const EMPTY_ITEMS = [];
export default function Receipts({ month, version, onReview, onChanged }) {
  const [category, setCategory] = useState('todas');
  const [all, setAll] = useState(false);
  const [preview, setPreview] = useState(null);
  const [remove, setRemove] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const resource = useApiResource('/receipts', { month: all ? '' : month }, version);
  const items = resource.data || EMPTY_ITEMS;
  const upload = useReceiptUpload(month, onChanged, onReview);
  const categories = useMemo(() => [...new Set(items.map(item => item.category))], [items]);
  const groups = useMemo(() => items.filter(item => category === 'todas' || item.category === category).reduce((result, receipt) => {
    const group = `${receipt.date.slice(0, 7)} · ${receipt.category}`;
    (result[group] ??= []).push(receipt);
    return result;
  }, {}), [items, category]);
  const deleteReceipt = async () => {
    if (!remove || deleting) return;
    setDeleting(true);
    try { await api.delete(`/receipts/${remove.id}`); toast.success('Comprovante excluído.'); setRemove(null); onChanged(); }
    catch (error) { toast.error(errorText(error)); }
    finally { setDeleting(false); }
  };
  let content = <ReceiptList groups={groups} onReview={onReview} onPreview={setPreview} onRemove={setRemove}/>;
  if (resource.loading && !resource.data) content = <Loading/>;
  else if (resource.error) content = <Empty title="Não foi possível carregar comprovantes" text={errorText(resource.error)}><Button onClick={resource.reload} data-testid="receipts-retry">Tentar novamente</Button></Empty>;
  else if (!Object.keys(groups).length) content = <Empty title="Seu arquivo começa aqui" text="Nenhum comprovante encontrado neste período."/>;
  return <>
    <ReceiptUpload {...upload}/>
    <div className="filter-bar"><div className="segmented"><button onClick={() => setAll(false)} className={!all ? 'active' : ''} data-testid="receipts-current-month">Neste mês</button><button onClick={() => setAll(true)} className={all ? 'active' : ''} data-testid="receipts-all-months">Todos os meses</button></div><label className="filter-select"><ListFilter size={15}/><select value={category} onChange={event => setCategory(event.target.value)} aria-label="Filtrar comprovantes" data-testid="receipts-category-filter"><option value="todas">Todas as categorias</option>{categories.map(item => <option key={item}>{item}</option>)}</select></label></div>
    {content}
    <ReceiptModals preview={preview} setPreview={setPreview} remove={remove} setRemove={setRemove} onDelete={deleteReceipt} deleting={deleting}/>
  </>;
}