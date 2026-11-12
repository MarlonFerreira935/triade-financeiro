import { Activity, BellRing, ShieldAlert } from 'lucide-react';

export const AlertSummary = ({ feed }) => <div className="alert-summary-grid">
  <div><span><Activity size={17}/> Monitoramento do período</span><strong data-testid="alert-total-count">{feed?.count || 0}<small> alertas ativos</small></strong></div>
  <div><span><ShieldAlert size={17}/> Prioridade alta</span><strong className={feed?.critical_count > 0 ? 'red' : 'muted'} data-testid="alert-critical-count">{feed?.critical_count || 0}<small> pontos críticos</small></strong></div>
  <div><span><BellRing size={17}/> Aguardando seu olhar</span><strong className="gold" data-testid="alert-unread-count">{feed?.unread_count || 0}<small> não lidos</small></strong></div>
</div>;

export const AlertRules = ({ rules }) => <div className="alert-rules" data-testid="alert-rules"><div className="rules-intro"><ShieldAlert size={18}/><p>Alertas calculados com os dados confirmados. Os critérios são gerenciais e não substituem um orçamento ou avaliação contábil.</p></div>{rules.map(rule => <div key={rule.id} data-testid={`alert-rule-${rule.id}`}><h3>{rule.name}</h3><p>{rule.criterion}</p></div>)}</div>;