import { useState,useEffect,useCallback } from 'react';
import { BrowserRouter,Routes,Route } from 'react-router-dom';
import { Toaster } from 'sonner';
import { useApiResource } from './hooks/useApiResource';
import { Layout } from './components/finance/Layout';
import { TransactionModal } from './components/finance/TransactionModal';
import { Loading } from './components/finance/Shared';
import { OverviewAlerts } from './components/finance/OverviewAlerts';
import { Button } from './components/ui/button';
import Overview from './pages/Overview';
import Transactions from './pages/Transactions';
import Dre from './pages/Dre';
import Receipts from './pages/Receipts';
import Diagnostics from './pages/Diagnostics';
import Spreadsheets from './pages/Spreadsheets';
import Whatsapp from './pages/Whatsapp';
import Advisor from './pages/Advisor';
import Alerts from './pages/Alerts';
import './App.css';
import './advisor.css';
import './mobile-finance.css';
import './advisor-refinements.css';

function Workspace(){
 const [month,setMonth]=useState('');
 const [version,setVersion]=useState(0),[modal,setModal]=useState(false),[initial,setInitial]=useState(null);
 const refresh=useCallback(()=>setVersion(v=>v+1),[]);
 const metadata=useApiResource('/meta',null,version);
 const dashboard=useApiResource(month?'/dashboard':null,{month},version);
 const alertResource=useApiResource(month?'/alerts':null,{month},version);
 const meta=metadata.data, data=dashboard.data, alerts=alertResource.data;
 useEffect(()=>{if(meta)setMonth(current=>current||meta.default_month);},[meta]);
 const open=record=>{setInitial(record||null);setModal(true)};
 if((metadata.error&&!meta)||(dashboard.error&&!data))return <div className="initial-error" data-testid="initial-error"><h1>Não foi possível abrir seu financeiro.</h1><Button onClick={refresh} data-testid="retry-app">Tentar novamente</Button></div>;
 if(!meta||!data)return <Loading/>;
 const props={month,version,onChanged:refresh,accounts:meta.accounts};
 const currentAlerts=alerts?.month===month?alerts:null;
 return <>
  <Layout month={month} setMonth={setMonth} meta={meta} onNew={open} alerts={currentAlerts}>
   {data.month!==month?<Loading/>:<Routes>
    <Route path="/" element={<><OverviewAlerts alerts={currentAlerts}/><Overview data={data}/></>}/>
    <Route path="/lancamentos" element={<Transactions {...props} onEdit={open}/>}/>
    <Route path="/dre" element={<Dre {...props}/>}/>
    <Route path="/comprovantes" element={<Receipts {...props} onReview={open}/>}/>
    <Route path="/diagnosticos" element={<Diagnostics data={data} month={month}/>}/>
    <Route path="/planilhas" element={<Spreadsheets {...props}/>}/>
    <Route path="/whatsapp" element={<Whatsapp/>}/>
    <Route path="/consultor" element={<Advisor data={data} month={month} alerts={currentAlerts} onUpdated={refresh}/>}/>
    <Route path="/alertas" element={<Alerts month={month} feed={currentAlerts} error={alertResource.error} onRetry={alertResource.reload} onUpdated={refresh}/>}/>
    <Route path="*" element={<Overview data={data} alerts={currentAlerts}/>}/>
   </Routes>}
  </Layout>
  <TransactionModal open={modal} onClose={()=>setModal(false)} initial={initial} accounts={meta.accounts} month={month} onSaved={m=>{setMonth(m);refresh()}}/>
 </>
}
export default function App(){return <BrowserRouter><Workspace/><Toaster theme="dark" position="bottom-right" richColors closeButton/></BrowserRouter>}