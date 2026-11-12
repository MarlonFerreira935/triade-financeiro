import { useMemo, useState } from 'react';
import { Activity, ChevronDown, ChevronUp } from 'lucide-react';
import { toast } from 'sonner';
import { api, errorText } from '../lib/api';
import { Empty, Loading } from '../components/finance/Shared';
import { AlertCard } from '../components/finance/alerts/AlertCard';
import { AlertRules, AlertSummary } from '../components/finance/alerts/AlertSummary';
import { Button } from '../components/ui/button';

const FILTERS = { todos: () => true, criticos: alert => alert.severity === 'critico', 'nao-lidos': alert => !alert.acknowledged };
const EMPTY_TITLES = { todos: 'Nenhum alerta neste período', criticos: 'Nenhum alerta crítico', 'nao-lidos': 'Tudo acompanhado por aqui' };
export default function Alerts({ month, feed, error, onRetry, onUpdated }) {
  const [filter, setFilter] = useState('todos');
  const [showRules, setShowRules] = useState(false);
  const [busy, setBusy] = useState(null);
  const items = useMemo(() => (feed?.alerts || []).filter(FILTERS[filter]), [feed, filter]);
  const acknowledge = async alert => {
    if (busy) return;
    setBusy(alert.id);
    try { await api.put(`/alerts/${alert.id}/acknowledge`, { month, acknowledged: !alert.acknowledged }); onUpdated(); toast.success(alert.acknowledged ? 'Alerta marcado como não lido.' : 'Alerta marcado como visto.'); }
    catch (error) { toast.error(errorText(error)); }
    finally { setBusy(null); }
  };
  if (error) return <div data-testid="alerts-load-error" role="alert"><Empty title="Não foi possível carregar os alertas" text={errorText(error)}><Button onClick={onRetry} data-testid="alerts-retry">Tentar novamente</Button></Empty></div>;
  if (!feed) return <Loading/>;
  return <>
    <AlertSummary feed={feed}/>
    <div className="filter-bar"><div className="segmented"><button onClick={() => setFilter('todos')} className={filter === 'todos' ? 'active' : ''} data-testid="alerts-filter-all">Todos</button><button onClick={() => setFilter('criticos')} className={filter === 'criticos' ? 'active' : ''} data-testid="alerts-filter-critical">Prioridade alta</button><button onClick={() => setFilter('nao-lidos')} className={filter === 'nao-lidos' ? 'active' : ''} data-testid="alerts-filter-unread">Não lidos</button></div><button className="text-link" onClick={() => setShowRules(value => !value)} data-testid="alert-rules-toggle">Critérios do monitoramento {showRules ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}</button></div>
    {showRules && <AlertRules rules={feed.rules}/>}
    <div className="alerts-list">{items.map(alert => <AlertCard key={alert.id} alert={alert} month={month} busy={Boolean(busy)} onAcknowledge={acknowledge}/>)}</div>
    {!items.length && <Empty title={EMPTY_TITLES[filter]} text={feed.has_data ? 'Nenhum ponto corresponde a este filtro nos critérios atuais.' : 'Não há dados financeiros suficientes para avaliar este mês.'}/>}
    <p className="alert-update-note" data-testid="alerts-update-note"><Activity size={12}/> Atualizado com os lançamentos confirmados · {new Date(feed.updated_at).toLocaleString('pt-BR')}</p>
  </>;
}