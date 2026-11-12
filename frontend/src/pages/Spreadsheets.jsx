import { useRef, useState } from 'react';
import { CheckCheck, Download, FileSpreadsheet, Loader2, Sheet, ShieldCheck, Upload } from 'lucide-react';
import { toast } from 'sonner';
import { useApiResource } from '../hooks/useApiResource';
import { api, downloadFile, errorText } from '../lib/api';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '../components/ui/dialog';
import { ImportHistory } from '../components/finance/ImportHistory';

const download = (path, filename) => downloadFile(path, filename).catch(error => toast.error(errorText(error)));

export default function Spreadsheets({ month, version, onChanged }) {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [year, setYear] = useState(Number(month.slice(0, 4)));
  const input = useRef(null);
  const resource = useApiResource('/spreadsheet/history', null, version);
  const resetFile = () => { setFile(null); if (input.current) input.current.value = ''; };
  const importFile = async () => {
    if (!file || busy) return;
    setBusy(true);
    try {
      const form = new FormData(); form.append('file', file); form.append('year', year);
      const { data } = await api.post('/spreadsheet/import', form);
      toast.success(`${data.count} registros importados sem duplicidade.`);
      resetFile(); onChanged();
    } catch (error) { toast.error(errorText(error)); }
    finally { setBusy(false); }
  };
  return <>
    <section className="spreadsheet-intro"><div className="spreadsheet-symbol"><Sheet size={44} strokeWidth={1.3}/></div><div><div className="eyebrow">MODELO OFICIAL TRÍADE</div><h2 data-testid="spreadsheet-name">TRIADE ERP FINANCEIRO</h2><p>DRE Gerencial · Ponto de Equilíbrio · Indicadores · Sócios</p><span className="green original-check" data-testid="structure-preserved"><CheckCheck size={15}/> Estrutura e fórmulas originais preservadas</span></div><span className="file-format">.XLSX</span></section>
    <div className="spreadsheet-actions-grid">
      <article><Upload size={26} className="gold"/><h2>Atualizar a base</h2><p>Importação do modelo Tríade, com o mesmo plano de contas.</p><input type="file" accept=".xlsx" hidden ref={input} data-testid="spreadsheet-file-input" onChange={event => { setFile(event.target.files[0]); setYear(Number(month.slice(0, 4))); }}/><Button className="gold-button" data-testid="spreadsheet-upload" onClick={() => input.current?.click()}><Upload size={16}/>Importar planilha</Button></article>
      <article><Download size={26} className="green"/><h2>Seu Excel, em dia</h2><p>Todas as abas originais e os lançamentos atuais de {month.slice(0, 4)}.</p><Button variant="outline" data-testid="spreadsheet-export-current" onClick={() => download(`/spreadsheet/export?year=${month.slice(0, 4)}`, `TRIADE_FINANCEIRO_${month.slice(0, 4)}.xlsx`)}><Download size={16}/>Baixar planilha atualizada</Button></article>
      <article><ShieldCheck size={26} className="blue"/><h2>Original sempre disponível</h2><p>Uma cópia intacta da planilha que você enviou.</p><Button variant="outline" data-testid="spreadsheet-download-original" onClick={() => download('/spreadsheet/original', 'TRIADE_ORIGINAL.xlsx')}><FileSpreadsheet size={16}/>Baixar original</Button></article>
    </div>
    {resource.error ? <div className="empty" role="alert" data-testid="spreadsheet-history-error"><p>{errorText(resource.error)}</p><Button onClick={resource.reload} data-testid="spreadsheet-history-retry">Tentar novamente</Button></div> : <ImportHistory history={resource.data || []} loading={resource.loading}/>}
    <Dialog open={Boolean(file)} onOpenChange={open => { if (!open && !busy) resetFile(); }}><DialogContent className="finance-modal" data-testid="spreadsheet-import-modal"><DialogTitle>Importar sua DRE</DialogTitle><DialogDescription>Os consolidados da planilha deste ano serão atualizados. Lançamentos manuais e comprovantes serão mantidos. Abas, contas e fórmulas do modelo original não serão modificadas.</DialogDescription><p className="filename-text" data-testid="import-filename">{file?.name}</p><label className="form-label">Ano-base<input type="number" min="2000" max="2100" required value={year} onChange={event => setYear(event.target.value)} data-testid="spreadsheet-import-year"/></label><Button className="gold-button" onClick={importFile} disabled={busy} data-testid="spreadsheet-import-confirm">{busy ? <Loader2 size={16} className="spin"/> : <Upload size={16}/>} {busy ? 'Importando...' : 'Confirmar importação'}</Button></DialogContent></Dialog>
  </>;
}