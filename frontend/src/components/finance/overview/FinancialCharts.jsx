import { memo } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { money, shortMoney } from '../../../lib/api';
import { SectionHeader } from '../Shared';

const COLORS = ['#c8a76b', '#6f9990', '#708bab', '#aa8469', '#84818e', '#666c72'];
const MARGIN = { top: 15, right: 10, left: -12, bottom: 0 };
const X_TICK = { fill: '#818389', fontSize: 11 };
const Y_TICK = { fill: '#767a81', fontSize: 10 };
const REVENUE_DOT = { r: 4, fill: '#cfb17b', stroke: '#141518', strokeWidth: 3 };
const EXPENSE_DOT = { r: 4, fill: '#71998d', stroke: '#141518', strokeWidth: 3 };
const ACTIVE_DOT = { r: 5 };
const TOOLTIP_STYLE = { background: '#202125', border: '1px solid #3c3c3c', borderRadius: 6, color: '#eee' };
const TOOLTIP_ITEM_STYLE = { color: '#eee' };
const EMPTY_PIE = [{ name: 'Sem despesas', value: 1 }];
const LEGEND_STYLES = COLORS.map(color => ({ background: color }));

const ChartTip = ({ active, payload, label }) => active && payload?.length ? <div className="chart-tooltip" data-testid="chart-tooltip"><strong>{label}</strong>{payload.map(point => <p key={point.dataKey}><i style={{ background: point.color }}/>{point.name}<b>{money(point.value)}</b></p>)}</div> : null;
const CHART_TOOLTIP = <ChartTip/>;

export const EvolutionChart = memo(function EvolutionChart({ chart, year, mode, onMode }) {
  return <section className="chart-section"><SectionHeader title="Evolução financeira" subtitle={`Receitas e despesas · ${year}`} id="financial-chart"><div className="segmented"><button data-testid="chart-monthly" className={mode === 'mensal' ? 'active' : ''} onClick={() => onMode('mensal')}>Mensal</button><button data-testid="chart-cumulative" className={mode === 'acumulado' ? 'active' : ''} onClick={() => onMode('acumulado')}>Acumulado</button></div></SectionHeader>
    <div className="chart-legend"><span><i className="legend-dot gold-bg"/>Receitas</span><span><i className="legend-dot sage-bg"/>Despesas</span><span className="chart-unit">Valores em R$</span></div>
    <div className="finance-chart" data-testid="financial-evolution-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chart} margin={MARGIN}><defs><linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#c8a76b" stopOpacity={0.2}/><stop offset="100%" stopColor="#c8a76b" stopOpacity={0}/></linearGradient><linearGradient id="expenseGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#73998d" stopOpacity={0.08}/><stop offset="100%" stopColor="#73998d" stopOpacity={0}/></linearGradient></defs>
      <CartesianGrid stroke="#27292e" strokeDasharray="3 5" vertical={false}/><XAxis dataKey="name" axisLine={false} tickLine={false} tick={X_TICK} dy={10}/><YAxis tickFormatter={shortMoney} axisLine={false} tickLine={false} tick={Y_TICK} width={64}/><Tooltip content={CHART_TOOLTIP}/><Area name="Receitas" type="monotone" dataKey="receitas" stroke="#cfb17b" strokeWidth={2.5} fill="url(#revenueGradient)" dot={REVENUE_DOT} activeDot={ACTIVE_DOT}/><Area name="Despesas" type="monotone" dataKey="despesas" stroke="#71998d" strokeWidth={2} fill="url(#expenseGradient)" dot={EXPENSE_DOT}/>
    </AreaChart></ResponsiveContainer></div><div className="chart-footnote"><span><span className="online-dot"/> Valores mensais consolidados</span><Link to="/dre" data-testid="chart-view-dre">Ver DRE completa <ArrowUpRight size={13}/></Link></div>
  </section>;
});

export const ExpensesChart = memo(function ExpensesChart({ pie, total }) {
  const entries = pie.length ? pie : EMPTY_PIE;
  return <section className="expense-section"><SectionHeader title="Onde estão suas despesas" subtitle="Distribuição por categoria" id="expenses-chart"/>
    <div className="expense-visual"><div className="donut" data-testid="expenses-donut"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={entries} dataKey="value" innerRadius="74%" outerRadius="96%" paddingAngle={3} stroke="none" startAngle={90} endAngle={-270}>{entries.map((entry, index) => <Cell key={entry.name} fill={pie.length ? COLORS[index] : '#2b2d31'}/>)}</Pie><Tooltip formatter={money} contentStyle={TOOLTIP_STYLE} itemStyle={TOOLTIP_ITEM_STYLE}/></PieChart></ResponsiveContainer><div className="donut-label"><small>Total de despesas</small><strong data-testid="expense-chart-total">R$ {shortMoney(total)}</strong></div></div>
      <div className="expense-legend">{pie.map((category, index) => <div className="expense-legend-row" key={category.name} data-testid={`expense-category-${index}`}><span><i style={LEGEND_STYLES[index]}/>{category.name}</span><b>{(category.value / (total || 1) * 100).toFixed(1).replace('.', ',')}%</b></div>)}</div>
    </div>
  </section>;
});