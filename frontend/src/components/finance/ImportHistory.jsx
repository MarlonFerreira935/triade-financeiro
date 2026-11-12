import { CheckCheck, Clock3, FileSpreadsheet, Loader2 } from 'lucide-react';
import { Empty } from './Shared';

export const ImportHistory = ({ history, loading }) => <section className="import-history">
  <div className="section-heading"><div><h2>Histórico de importações</h2><p>Rastreabilidade da sua base financeira</p></div><Clock3 size={18} className="muted"/></div>
  {loading && <div className="history-row muted" role="status" data-testid="spreadsheet-history-loading"><Loader2 size={18} className="spin"/><span>Carregando histórico de importações...</span></div>}
  {!loading && !history.length && <Empty title="Nenhuma importação registrada" text="O histórico aparecerá após a primeira importação."/>}
  {history.map((item, index) => <div className="history-row" key={item.id} data-testid={`import-history-${index}`}><FileSpreadsheet size={23} className="green"/><div><strong>{item.filename}</strong><span>{new Date(item.created_at).toLocaleString('pt-BR')} · Ano-base {item.year}</span></div><span className="category-tag">{item.count} registros</span><span className="green history-complete"><CheckCheck size={15}/> Concluído</span></div>)}
</section>;