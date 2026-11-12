import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, ArrowDownRight, ArrowDownLeft, Wallet, TrendingUp, ArrowRight, Sparkles, FileCheck2, Info } from 'lucide-react';
import { money } from '../lib/api';
import { SectionHeader, TransactionTable } from '../components/finance/Shared';
import { EvolutionChart, ExpensesChart } from '../components/finance/overview/FinancialCharts';

const Metric = ({ title, value, previous, icon: Icon, color, id }) => {
  const delta = previous ? (value - previous) / Math.abs(previous) * 100 : null;
  const positive = id === 'expenses' ? delta <= 0 : delta >= 0;
  return <article className={`metric metric-${color}`} data-testid={`metric-${id}`}><div className="metric-top"><span>{title}</span><div className={`metric-icon ${color}`}><Icon size={17}/></div></div><strong className="metric-value" data-testid={`metric-${id}-value`}>{money(value)}</strong><div className="metric-bottom">{delta !== null ? <><span className={`delta ${positive ? 'green' : 'red'}`}>{delta >= 0 ? <ArrowUpRight size={13}/> : <ArrowDownRight size={13}/>} {Math.abs(delta).toFixed(1).replace('.', ',')}%</span><span>vs. mês anterior</span></> : <span>Sem comparação anterior</span>}</div><div className={`metric-accent ${color}`}/></article>;
};

const OverviewInsights = ({ diagnostics }) => <aside className="insight-section"><div className="insight-heading"><span className="sparkle-box"><Sparkles size={17}/></span><h2 data-testid="insights-title">Um olhar para o negócio</h2><span className="gold-tag">TRÍADE</span></div>{diagnostics.slice(0, 2).map((diagnostic, index) => <div className="insight" key={diagnostic.id || diagnostic.title} data-testid={`overview-insight-${index}`}><span className={`insight-dot ${diagnostic.level}`}/><div><strong>{diagnostic.title}</strong><p>{diagnostic.text}</p></div></div>)}<Link to="/diagnosticos" className="insight-link" data-testid="view-diagnostics">Explorar diagnóstico <ArrowUpRight size={15}/></Link></aside>;

export default function Overview({ data }) {
  const [chartMode, setChartMode] = useState('mensal');
  const { totals, previous } = data;
  const chart = useMemo(() => {
    const values = data.chart.filter(item => item.receitas !== null);
    if (chartMode === 'mensal') return values;
    let revenue = 0, expenses = 0;
    return values.map(item => ({ ...item, receitas: revenue += item.receitas, despesas: expenses += item.despesas }));
  }, [data.chart, chartMode]);
  const pie = useMemo(() => {
    const main = data.categories.slice(0, 4);
    const other = data.categories.slice(4).reduce((sum, category) => sum + category.value, 0);
    return other ? [...main, { name: 'Outras despesas', value: other }] : main;
  }, [data.categories]);
  return <>
    <div className="overview-context"><span className="live-label"><span/> RESULTADO DO MÊS</span><span data-testid="overview-data-source"><FileCheck2 size={13}/> Dados da sua DRE <span className="context-separator">·</span> {totals.count} registros confirmados</span></div>
    <div className="metrics-grid"><Metric title="Receita bruta" value={totals.revenue} previous={previous.revenue} icon={ArrowDownLeft} color="green" id="revenue"/><Metric title="Custos e despesas" value={totals.expenses} previous={previous.expenses} icon={ArrowUpRight} color="red" id="expenses"/><Metric title="Lucro líquido" value={totals.profit} previous={previous.profit} icon={TrendingUp} color="gold" id="profit"/><Metric title="Caixa livre gerado" value={totals.free_cash} previous={previous.free_cash} icon={Wallet} color="blue" id="cash"/></div>
    <div className="chart-grid"><EvolutionChart chart={chart} year={data.month.slice(0, 4)} mode={chartMode} onMode={setChartMode}/><ExpensesChart pie={pie} total={totals.expenses}/></div>
    <div className="bottom-grid"><section className="recent-section"><SectionHeader title="Últimos lançamentos" subtitle="Os movimentos mais recentes do período" id="recent-transactions"><Link to="/lancamentos" className="text-link" data-testid="view-all-transactions">Ver todos <ArrowRight size={14}/></Link></SectionHeader><TransactionTable items={data.recent.slice(0, 4)} compact/></section><OverviewInsights diagnostics={data.diagnostics}/></div>
    <div className="accounting-note" data-testid="accounting-note"><Info size={13}/> Resultado gerencial conforme sua planilha. Caixa livre gerado não representa saldo bancário.</div>
  </>;
}