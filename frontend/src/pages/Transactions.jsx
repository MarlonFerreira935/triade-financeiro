import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, Download, ListFilter, ArrowDownLeft, ArrowUpRight } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Empty, TransactionTable, Loading } from '../components/finance/Shared';
import { useApiResource } from '../hooks/useApiResource';
import { api, money, downloadFile, errorText } from '../lib/api';

const EMPTY_ITEMS = [];
export default function Transactions({ month, version, onEdit, onChanged, accounts }) {
  const [params] = useSearchParams();
  const query = params.get('q') || '';
  const [search, setSearch] = useState(query);
  const [kind, setKind] = useState('todos');
  const [category, setCategory] = useState('todas');
  const [remove, setRemove] = useState(null);
  const [busy, setBusy] = useState(false);
  const resource = useApiResource('/transactions', { month }, version);
  const items = resource.data || EMPTY_ITEMS;
  useEffect(() => { setSearch(query); }, [query]);
  const filtered = useMemo(() => items.filter(item =>
    (kind === 'todos' || item.type === kind) && (category === 'todas' || item.category === category) &&
    `${item.description} ${item.category}`.toLowerCase().includes(search.toLowerCase())), [items, kind, category, search]);
  const categories = useMemo(() => [...new Set(accounts.map(account => account.group))], [accounts]);
  const sums = useMemo(() => items.reduce((result, item) => { result[item.type] += item.amount; return result; }, { receita: 0, despesa: 0 }), [items]);
  const deleteItem = async () => {
    if (!remove || busy) return;
    setBusy(true);
    try { await api.delete(`/transactions/${remove.id}`); toast.success('Lançamento excluído. DRE atualizada.'); setRemove(null); onChanged(); }
    catch (error) { toast.error(errorText(error)); }
    finally { setBusy(false); }
  };
  if (!resource.data && resource.loading) return <Loading/>;
  if (resource.error) return <Empty title="Não foi possível carregar os lançamentos" text={errorText(resource.error)}><Button onClick={resource.reload} data-testid="transactions-retry">Tentar novamente</Button></Empty>;
  return <>
    <div className="ledger-summary"><div><span title="Inclui receitas operacionais e financeiras"><ArrowDownLeft size={16}/> Receitas totais</span><strong className="green" data-testid="ledger-income">{money(sums.receita)}</strong></div><div><span><ArrowUpRight size={16}/> Despesas e retiradas</span><strong data-testid="ledger-expenses">{money(sums.despesa)}</strong></div><div><span>Movimentos do período</span><strong data-testid="ledger-count">{items.length}<small> lançamentos</small></strong></div></div>
    <div className="filter-bar"><div className="segmented"><button data-testid="filter-all" className={kind === 'todos' ? 'active' : ''} onClick={() => setKind('todos')}>Todos</button><button data-testid="filter-income" className={kind === 'receita' ? 'active' : ''} onClick={() => setKind('receita')}>Receitas</button><button data-testid="filter-expenses" className={kind === 'despesa' ? 'active' : ''} onClick={() => setKind('despesa')}>Despesas</button></div><div className="filter-controls">
      <label className="search-field"><Search size={15}/><input data-testid="transactions-search" aria-label="Buscar lançamentos" placeholder="Buscar lançamento" value={search} onChange={event => setSearch(event.target.value)}/></label><label className="filter-select"><ListFilter size={14}/><select data-testid="transactions-category-filter" aria-label="Filtrar categoria" value={category} onChange={event => setCategory(event.target.value)}><option value="todas">Todas as categorias</option>{categories.map(item => <option key={item}>{item}</option>)}</select></label><Button variant="outline" data-testid="transactions-export" onClick={() => downloadFile(`/spreadsheet/export?year=${month.slice(0, 4)}`, `TRIADE_${month.slice(0, 4)}.xlsx`).catch(error => toast.error(errorText(error)))}><Download size={15}/>Exportar</Button>
    </div></div>
    <div className="ledger-list"><TransactionTable items={filtered} onEdit={onEdit} onDelete={setRemove}/></div><p className="table-count" data-testid="filtered-count">{filtered.length} de {items.length} lançamentos · {month.slice(0, 4)}</p>
    <Dialog open={Boolean(remove)} onOpenChange={open => { if (!open && !busy) setRemove(null); }}><DialogContent className="finance-modal" data-testid="delete-transaction-modal"><DialogTitle>Excluir lançamento?</DialogTitle><DialogDescription>O valor será removido da DRE. Um comprovante vinculado ficará pendente novamente.</DialogDescription><p data-testid="delete-transaction-description">{remove?.description}</p><div className="modal-footer"><Button variant="outline" disabled={busy} onClick={() => setRemove(null)} data-testid="delete-cancel">Cancelar</Button><Button variant="destructive" disabled={busy} onClick={deleteItem} data-testid="delete-confirm">{busy ? 'Excluindo...' : 'Excluir lançamento'}</Button></div></DialogContent></Dialog>
  </>;
}