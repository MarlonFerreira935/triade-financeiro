import { Link } from 'react-router-dom';
import { ArrowUpRight, Check, CheckCheck, MessageSquareText, RotateCcw, ShieldAlert } from 'lucide-react';
import { Button } from '../../ui/button';

export const AlertCard = ({ alert, month, busy, onAcknowledge }) => {
  const question = `Analise este ponto de atenção de ${month}: ${alert.title}. ${alert.description} Que ações devo priorizar?`;
  return <article className={`financial-alert ${alert.severity} ${alert.acknowledged ? 'acknowledged' : ''}`} id={alert.id} data-testid={`financial-alert-${alert.id}`}>
    <div className="financial-alert-icon"><ShieldAlert size={21}/></div><div className="financial-alert-main"><div className="financial-alert-top">
      <span className="alert-severity"><i/>{alert.severity === 'critico' ? 'PRIORIDADE ALTA' : 'ACOMPANHAMENTO'}</span>{alert.acknowledged && <span className="alert-seen" data-testid={`alert-seen-${alert.id}`}><CheckCheck size={12}/>Visto</span>}<strong data-testid={`alert-metric-${alert.id}`}>{alert.metric}</strong>
    </div><h2 data-testid={`alert-title-${alert.id}`}>{alert.title}</h2><p className="alert-description" data-testid={`alert-description-${alert.id}`}>{alert.description}</p><div className="alert-recommendation"><span>PRÓXIMO PASSO</span><p data-testid={`alert-action-${alert.id}`}>{alert.action}</p></div>
      <div className="financial-alert-actions"><Link to={`/consultor?pergunta=${encodeURIComponent(question)}`} data-testid={`alert-ask-advisor-${alert.id}`} className="ask-advisor-link"><MessageSquareText size={14}/>Analisar com o consultor <ArrowUpRight size={13}/></Link><Button variant="ghost" disabled={busy} data-testid={`alert-acknowledge-${alert.id}`} onClick={() => onAcknowledge(alert)}>{alert.acknowledged ? <RotateCcw size={13}/> : <Check size={13}/>} {alert.acknowledged ? 'Marcar não lido' : 'Marcar como visto'}</Button></div>
    </div>
  </article>;
};