import { useState } from 'react';
import { useDiagnostics } from '../hooks/useDiagnostics';
import { DiagnosticAnalysis, DiagnosticMetrics, DiagnosticScenario, DiagnosticSignals } from '../components/finance/diagnostics/DiagnosticSections';

export default function Diagnostics({ data, month }) {
  const analysis = useDiagnostics(month);
  const [growth, setGrowth] = useState(0);
  const [reduction, setReduction] = useState(0);
  return <>
    <DiagnosticMetrics totals={data.totals}/>
    <div className="diagnostic-grid"><DiagnosticAnalysis analysis={analysis} hasData={Boolean(data.totals.count)}/><DiagnosticSignals signals={data.diagnostics}/></div>
    <DiagnosticScenario totals={data.totals} growth={growth} setGrowth={setGrowth} reduction={reduction} setReduction={setReduction}/>
  </>;
}