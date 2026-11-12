import { useMemo, useState } from 'react';
import { Download, ChevronDown, ChevronRight, CheckCheck } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { downloadFile, errorText } from '../lib/api';
import { dreColumns, visibleDreRows } from '../lib/dre';
import { useApiResource } from '../hooks/useApiResource';
import { Loading } from '../components/finance/Shared';
import { DreTable } from '../components/finance/DreTable';

export default function Dre({ month, version }) {
  const [view, setView] = useState('mensal');
  const [detailed, setDetailed] = useState(true);
  const year = Number(month.slice(0, 4)), current = Number(month.slice(5)) - 1;
  const resource = useApiResource('/dre', { year }, version);
  const rows = useMemo(() => visibleDreRows(resource.data?.rows || [], detailed), [resource.data, detailed]);
  const columns = useMemo(() => dreColumns(current, view), [current, view]);
  if (resource.error) return <div className="empty" data-testid="dre-load-error"><p>{errorText(resource.error)}</p><Button onClick={resource.reload} data-testid="dre-retry">Tentar novamente</Button></div>;
  if (!resource.data) return <Loading/>;
  const net = resource.data.rows.find(row => row.row === 11)?.values[current] || 0;
  return <>
    <div className="dre-toolbar"><div className="original-badge" data-testid="dre-original-structure"><CheckCheck size={16}/><div><strong>Seu modelo original, preservado</strong><span>Plano de contas e cálculos da Tríade</span></div></div><div className="filter-controls"><div className="segmented"><button className={view === 'mensal' ? 'active' : ''} onClick={() => setView('mensal')} data-testid="dre-month-view">Mensal</button><button className={view === 'comparativo' ? 'active' : ''} onClick={() => setView('comparativo')} data-testid="dre-comparison-view">Comparativo</button></div><Button variant="outline" data-testid="dre-export" onClick={() => downloadFile(`/spreadsheet/export?year=${year}`, `TRIADE_DRE_${year}.xlsx`).catch(error => toast.error(errorText(error)))}><Download size={15}/>Baixar Excel</Button></div></div>
    <div className="dre-table-heading"><span data-testid="dre-period-title">Demonstração do resultado · {year}</span><button className="text-link" onClick={() => setDetailed(value => !value)} data-testid="dre-toggle-detail">{detailed ? <ChevronDown size={14}/> : <ChevronRight size={14}/>}{detailed ? 'Recolher contas' : 'Expandir contas'}</button></div>
    <DreTable rows={rows} columns={columns} current={current} net={net} months={resource.data.months} year={year}/>
    <p className="accounting-note" data-testid="dre-note">AV: participação sobre a receita operacional líquida do mês selecionado. Comparativo: até três meses. O Excel mantém todas as abas e fórmulas originais.</p>
  </>;
}