import { CheckCircle2, Loader2, Sparkles, Target, TrendingUp, TriangleAlert, Wallet } from 'lucide-react';
import { Button } from '../../ui/button';
import { money } from '../../../lib/api';

const SIGNAL_ICONS = { success: CheckCircle2, warning: TriangleAlert, info: TrendingUp };
const SIGNAL_COLORS = { success: 'green', warning: 'gold', info: 'blue' };

export const DiagnosticMetrics = ({ totals }) => <div className="diagnostic-kpis">
  <div><Target size={20}/><span>Ponto de equilíbrio operacional</span><strong data-testid="break-even-value">{totals.break_even === null ? 'Não calculável' : money(totals.break_even)}</strong><small>Sobre receita líquida · conforme a DRE</small></div>
  <div><TrendingUp size={20}/><span>Margem de contribuição</span><strong className="green" data-testid="contribution-margin">{totals.contribution_margin.toFixed(1).replace('.', ',')}%</strong><small>Após os custos variáveis</small></div>
  <div><Wallet size={20}/><span>Resultado após retiradas</span><strong className={totals.free_cash >= 0 ? 'gold' : 'red'} data-testid="after-withdrawals">{money(totals.free_cash)}</strong><small>Caixa livre gerado no período</small></div>
</div>;

export const DiagnosticAnalysis = ({ analysis, hasData }) => <section className="ai-diagnostic">
  <div className="section-heading"><div><div className="eyebrow"><Sparkles size={13}/> INTELIGÊNCIA FINANCEIRA</div><h2 data-testid="ai-diagnostic-title">Uma segunda perspectiva para suas decisões</h2></div><span className="gold-tag">GEMINI</span></div>
  {analysis.text ? <div className="ai-text" data-testid="ai-diagnostic-text">{analysis.text}{analysis.busy && <span className="typing-cursor"/>}</div> : <p className="ai-empty" data-testid="ai-diagnostic-empty">{analysis.busy ? 'Analisando os números da sua DRE...' : 'Seu resultado merece um olhar mais atento.'}</p>}
  {analysis.error && <p role="alert" className="red" data-testid="diagnostic-error">{analysis.error}</p>}
  <Button className="gold-button" disabled={analysis.busy || !hasData} onClick={analysis.generate} data-testid="generate-diagnostic">{analysis.busy ? <Loader2 size={16} className="spin"/> : <Sparkles size={16}/>} {analysis.busy ? 'Analisando...' : analysis.text ? 'Atualizar diagnóstico' : 'Gerar diagnóstico com IA'}</Button>
  <p className="tiny muted">Análise gerencial de apoio. Não substitui a avaliação do seu contador.</p>
</section>;

export const DiagnosticSignals = ({ signals }) => <section className="signals"><h2>Sinais do período</h2>{signals.map((signal, index) => {
  const Icon = SIGNAL_ICONS[signal.level] || TrendingUp;
  return <div className="signal" key={signal.id || signal.title} data-testid={`diagnostic-signal-${index}`}><Icon size={19} className={SIGNAL_COLORS[signal.level] || 'blue'}/><div><h3>{signal.title}</h3><p>{signal.text}</p></div></div>;
})}</section>;

export const DiagnosticScenario = ({ totals, growth, setGrowth, reduction, setReduction }) => {
  const simulated = totals.profit + (totals.net_revenue - totals.variable) * growth / 100 + totals.fixed * reduction / 100;
  return <section className="scenario-section"><div className="section-heading"><div><h2 data-testid="scenario-title">E se o próximo mês fosse diferente?</h2><p>Simulação independente · não altera sua DRE</p></div><span className="category-tag">Cenário de resultado</span></div><div className="scenario-grid">
    <label>Crescimento da receita <b data-testid="growth-value">+{growth}%</b><input type="range" min="0" max="50" value={growth} onChange={event => setGrowth(Number(event.target.value))} data-testid="revenue-growth-slider"/><span>0% <span>50%</span></span></label>
    <label>Redução das despesas fixas <b data-testid="reduction-value">−{reduction}%</b><input type="range" min="0" max="30" value={reduction} onChange={event => setReduction(Number(event.target.value))} data-testid="expense-reduction-slider"/><span>0% <span>30%</span></span></label>
    <div className="scenario-result"><span>Lucro líquido simulado</span><strong data-testid="scenario-profit">{money(simulated)}</strong><small>Custos variáveis proporcionais à receita</small></div>
  </div></section>;
};