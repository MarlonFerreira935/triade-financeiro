import { ArrowUpRight, ChartNoAxesCombined, ShieldCheck, TrendingUp, Wallet } from 'lucide-react';
import { money } from '../../../lib/api';

const SUGGESTIONS = [
  { id: 'health', icon: ChartNoAxesCombined, label: 'Como está a saúde do negócio?', prompt: 'Faça uma análise da saúde financeira do negócio neste período. O que exige minha atenção primeiro?' },
  { id: 'margin', icon: TrendingUp, label: 'Onde posso melhorar a margem?', prompt: 'Quais são as melhores oportunidades para aumentar a margem, considerando nossos custos reais?' },
  { id: 'withdrawals', icon: Wallet, label: 'As retiradas estão sustentáveis?', prompt: 'As retiradas dos sócios estão sustentáveis neste mês? Analise os valores reais e recomende um limite responsável.' },
  { id: 'comparison', icon: ShieldCheck, label: 'O que mudou no último mês?', prompt: 'Compare este período com o mês anterior: o que melhorou, o que piorou e quais ações você recomenda?' },
];

export const ChatWelcome = ({ totals, send }) => <div className="advisor-welcome">
  <div className="advisor-welcome-symbol"><img src="/brand/symbol.png" alt="Marca Tríade"/></div><span className="eyebrow">SEU NEGÓCIO. UMA VISÃO MAIS CLARA.</span>
  <h2 data-testid="advisor-welcome-title">Vamos olhar para<br/>os seus números?</h2><p data-testid="advisor-welcome-subtitle">Decisões melhores começam com as perguntas certas.</p>
  <div className="advisor-mini-kpis"><div><span>Lucro líquido</span><strong data-testid="advisor-profit">{money(totals.profit)}</strong></div><div><span>Margem líquida</span><strong className="green" data-testid="advisor-margin">{totals.margin.toFixed(1).replace('.', ',')}%</strong></div><div><span>Caixa livre gerado</span><strong data-testid="advisor-cash">{money(totals.free_cash)}</strong></div></div>
  <div className="advisor-prompts">{SUGGESTIONS.map((suggestion, index) => <button key={suggestion.id} onClick={() => send(suggestion.prompt)} data-testid={`advisor-suggestion-${index}`}><suggestion.icon size={16}/><span>{suggestion.label}</span><ArrowUpRight size={14}/></button>)}</div>
</div>;