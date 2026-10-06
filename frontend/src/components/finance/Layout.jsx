import { NavLink,Link,useLocation,useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { LayoutDashboard,ArrowLeftRight,FileChartColumn,Files,Sparkles,MessageCircle,Sheet,ChevronRight,Search,Menu,X,ArrowUpRight,MapPin,Plus,Upload,CalendarDays,ChevronDown,Bell,MessagesSquare,ShieldAlert } from 'lucide-react';
import { Button } from '../ui/button';
import { monthLabel } from '../../lib/api';
const primary=[['/','Visão geral',LayoutDashboard],['/lancamentos','Lançamentos',ArrowLeftRight],['/dre','DRE gerencial',FileChartColumn],['/comprovantes','Comprovantes',Files],['/diagnosticos','Diagnósticos',Sparkles],['/consultor','Consultor financeiro',MessagesSquare],['/alertas','Alertas financeiros',ShieldAlert]];
const integrations=[['/whatsapp','WhatsApp Business',MessageCircle],['/planilhas','Planilhas',Sheet]];
const titles={'/':'Visão geral','/lancamentos':'Lançamentos','/dre':'DRE gerencial','/comprovantes':'Comprovantes','/diagnosticos':'Diagnósticos','/whatsapp':'WhatsApp Business','/planilhas':'Planilhas','/consultor':'Seu consultor financeiro','/alertas':'Alertas financeiros'};
const descriptions={'/':'Cada número, uma decisão mais inteligente.','/lancamentos':'Todos os movimentos da Tríade, em um só lugar.','/dre':'O seu modelo de DRE. A mesma estrutura, sempre atualizado.','/comprovantes':'Seus documentos, organizados por mês e categoria.','/diagnosticos':'Clareza para cuidar do presente e planejar o próximo passo.','/whatsapp':'Seu financeiro, mais perto da sua rotina.','/planilhas':'Sua planilha original é o ponto de partida.','/consultor':'Uma conversa com os dados. Um próximo passo mais seguro.','/alertas':'Um olhar atento ao que precisa da sua atenção.'};
export const Layout=({children,month,setMonth,meta,onNew,alerts})=>{
 const [mobile,setMobile]=useState(false),[search,setSearch]=useState(''),[notices,setNotices]=useState(false);
 const location=useLocation(),navigate=useNavigate();
 const months=Array.from(new Set([...(meta?.months||[]),...Array.from({length:12},(_,i)=>`${month.slice(0,4)}-${String(i+1).padStart(2,'0')}`)])).sort().reverse();
 const nav=list=>list.map(([to,label,Icon])=><NavLink key={to} to={to} end={to==='/'} className={({isActive})=>`nav-link ${isActive?'active':''}`} data-testid={`nav-${to==='/'?'overview':to.slice(1)}`} onClick={()=>setMobile(false)}>
  <Icon size={18}/><span>{label}</span>{to==='/consultor'&&<span className="nav-ai">IA</span>}{to==='/alertas'&&!!alerts?.unread_count&&<span className="nav-alert-count" data-testid="nav-alert-count">{alerts.unread_count}</span>}{to==='/whatsapp'&&<span className="nav-status"/>}
 </NavLink>);
 return <div className="app-shell">
  <aside className={`sidebar ${mobile?'is-open':''}`}>
   <Link to="/" className="brand" data-testid="brand-home"><img src="/brand/symbol.png" alt="Símbolo Tríade"/><div><strong>TRÍADE<span>FINANCEIRO</span></strong></div></Link>
   <button className="mobile-close icon-button" onClick={()=>setMobile(false)} data-testid="close-sidebar" aria-label="Fechar menu"><X size={20}/></button>
   <div className="company-label" data-testid="company-identity"><span className="company-mark">T</span><div><strong>Tríade Móveis</strong><span>Porto Alegre, RS</span></div><ChevronDown size={13}/></div>
   <div className="nav-group-label">GESTÃO FINANCEIRA</div><nav>{nav(primary)}</nav>
   <div className="nav-group-label integrations-label">INTEGRAÇÕES</div><nav>{nav(integrations)}</nav>
   <div className="sidebar-bottom"><Link className="whatsapp-mini" to="/whatsapp" data-testid="whatsapp-connect-card" onClick={()=>setMobile(false)}><MessageCircle size={21}/><strong>Conecte seu WhatsApp</strong><p>Uma conversa. Tudo em dia.</p><span>Configurar conexão <ArrowUpRight size={14}/></span></Link>
    <div className="sidebar-company"><div className="avatar">TP</div><div><strong>Tríade Porto Alegre</strong><span>Workspace financeiro</span></div><span className="online-dot"/></div>
   </div>
  </aside>
  {mobile&&<button className="sidebar-backdrop" onClick={()=>setMobile(false)} data-testid="sidebar-backdrop" aria-label="Fechar menu"/>}
  <div className="main-shell"><header className="topbar">
   <div className="breadcrumbs"><button className="icon-button mobile-toggle" data-testid="open-sidebar" onClick={()=>setMobile(true)} aria-label="Abrir menu"><Menu size={20}/></button><span>Workspace</span><ChevronRight size={13}/><strong>Financeiro</strong></div>
   <div className="topbar-right"><form className="global-search" onSubmit={e=>{e.preventDefault();navigate(`/lancamentos?q=${encodeURIComponent(search)}`)}}><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar lançamentos..." aria-label="Buscar lançamentos" data-testid="global-search"/><kbd>↵</kbd></form>
    <span className="workspace-status" data-testid="workspace-status"><span className="online-dot"/> Workspace ativo</span>
    <div className="notifications"><button className={`icon-button ${notices?'selected':''}`} aria-label="Notificações financeiras" data-testid="notifications-toggle" onClick={()=>setNotices(!notices)}><Bell size={18}/>{!!alerts?.unread_count&&<span className="notification-count" data-testid="notification-alert-count">{alerts.unread_count}</span>}</button>
     {notices&&<div className="notice-popover" data-testid="notifications-panel"><strong>Radar financeiro</strong>{alerts?.alerts.length?alerts.alerts.slice(0,3).map(a=><Link className="notice-alert" key={a.id} to={`/alertas#${a.id}`} onClick={()=>setNotices(false)} data-testid={`notification-alert-${a.id}`}><span>{a.title}</span><p>{a.metric} · {a.severity==='critico'?'Prioridade alta':'Acompanhamento'}</p></Link>):<p data-testid="notifications-empty">{alerts?.has_data?'Nenhum ponto crítico identificado neste período.':'Sem dados para monitorar neste período.'}</p>}<Link className="all-notifications" to="/alertas" onClick={()=>setNotices(false)} data-testid="notification-alerts-link">Ver alertas financeiros <ArrowUpRight size={13}/></Link></div>}
    </div><div className="top-avatar" title="Tríade Porto Alegre">TP</div>
   </div>
  </header>
  <main className="workspace"><div className="page-top"><div><div className="eyebrow" data-testid="workspace-company"><span/> TRÍADE PORTO ALEGRE</div><h1 data-testid="page-title">{titles[location.pathname]||'Financeiro'}</h1><p data-testid="page-description">{descriptions[location.pathname]}</p></div>
   <div className="page-actions"><label className="period-selector"><CalendarDays size={15}/><select aria-label="Período" data-testid="period-select" value={month} onChange={e=>setMonth(e.target.value)}>{months.map(m=><option key={m} value={m}>{monthLabel(m)}</option>)}</select><ChevronDown size={13}/></label><Button variant="outline" className="import-header" onClick={()=>navigate('/planilhas')} data-testid="header-import"><Upload size={15}/>Importar planilha</Button><Button className="gold-button" onClick={()=>onNew()} data-testid="new-transaction"><Plus size={17}/>Novo lançamento</Button></div>
  </div><div className="page-content" key={location.pathname}>{children}</div><footer className="workspace-footer"><span><MapPin size={12}/> Porto Alegre, RS</span><span>Tríade · Gestão com propósito.</span><span className="footer-brand">FEITO PARA O SEU NEGÓCIO</span></footer></main>
  </div>
 </div>
};