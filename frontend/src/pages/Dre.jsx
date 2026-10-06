import { useEffect,useState } from 'react';
import { Download,ChevronDown,ChevronRight,CheckCheck } from 'lucide-react';
import { Button } from '../components/ui/button';
import { api,money,downloadFile,errorText } from '../lib/api';
import { Loading } from '../components/finance/Shared';
import { toast } from 'sonner';

export default function Dre({month,version}){
 const [data,setData]=useState(null),[view,setView]=useState('mensal'),[detailed,setDetailed]=useState(true),[failed,setFailed]=useState(false);
 const year=Number(month.slice(0,4)),current=Number(month.slice(5))-1;
 useEffect(()=>{
  let active=true;setFailed(false);
  api.get('/dre',{params:{year}}).then(r=>{if(active)setData(r.data)}).catch(e=>{if(active){setFailed(true);toast.error(errorText(e))}});
  return()=>{active=false};
 },[year,version]);
 if(failed)return <div className="empty" data-testid="dre-load-error"><p>Não foi possível carregar a DRE. Selecione novamente o período.</p></div>;
 if(!data||data.year!==year)return <Loading/>;
 const rows=data.rows.filter(r=>detailed||r.subtotal||(!r.account&&!/^\d\.\d/.test(r.label)));
 const cols=view==='mensal'?[current]:Array.from({length:Math.min(current+1,3)},(_,i)=>Math.max(0,current-2)+i);
 const net=data.rows.find(r=>r.row===11).values[current];
 return <>
  <div className="dre-toolbar"><div className="original-badge" data-testid="dre-original-structure"><CheckCheck size={16}/><div><strong>Seu modelo original, preservado</strong><span>Plano de contas e cálculos da Tríade</span></div></div><div className="filter-controls"><div className="segmented"><button className={view==='mensal'?'active':''} onClick={()=>setView('mensal')} data-testid="dre-month-view">Mensal</button><button className={view==='comparativo'?'active':''} onClick={()=>setView('comparativo')} data-testid="dre-comparison-view">Comparativo</button></div><Button variant="outline" data-testid="dre-export" onClick={()=>downloadFile(`/spreadsheet/export?year=${year}`,`TRIADE_DRE_${year}.xlsx`).catch(e=>toast.error(errorText(e)))}><Download size={15}/>Baixar Excel</Button></div></div>
  <div className="dre-table-heading"><span data-testid="dre-period-title">Demonstração do resultado · {year}</span><button className="text-link" onClick={()=>setDetailed(!detailed)} data-testid="dre-toggle-detail">{detailed?<ChevronDown size={14}/>:<ChevronRight size={14}/>}{detailed?'Recolher contas':'Expandir contas'}</button></div>
  <div className="table-scroll dre-scroll"><table className="dre-table" data-testid="dre-table"><thead><tr><th>PLANO DE CONTAS GERENCIAL</th>{cols.map(i=><th key={i}>{data.months[i]} / {String(year).slice(-2)}</th>)}<th>AV (%)</th></tr></thead><tbody>
   {rows.map(r=><tr key={r.row} className={`${r.subtotal?'subtotal':''} ${!r.account&&!r.subtotal?'group-row':''} ${r.percentage?'percentage-row':''} ${[67,73].includes(r.row)?'result-row':''}`} data-testid={`dre-row-${r.row}`}>
    <td>{r.account&&<span className="account-indent"/>}{r.label}</td>
    {cols.map(i=><td key={i} className="amount" data-label={`${data.months[i]}/${String(year).slice(-2)}`} data-testid={`dre-value-${r.row}-${i+1}`}>{!r.account&&!r.subtotal?'':r.percentage?`${r.values[i].toFixed(1).replace('.',',')}%`:money(r.values[i])}</td>)}
    <td className="muted amount" data-testid={`dre-vertical-${r.row}`}>{(r.account||r.subtotal)&&!r.percentage&&net?`${(r.values[current]/net*100).toFixed(1).replace('.',',')}%`:'—'}</td>
   </tr>)}
  </tbody></table></div>
  <p className="accounting-note" data-testid="dre-note">AV: participação sobre a receita operacional líquida do mês selecionado. Comparativo: até três meses. O Excel mantém todas as abas e fórmulas originais.</p>
 </>
}