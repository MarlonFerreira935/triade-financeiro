import { useRef, useState } from 'react';
import { ArrowUpRight, Loader2, UploadCloud } from 'lucide-react';

export const ReceiptUpload = ({ busy, upload }) => {
  const input = useRef(null);
  const [drag, setDrag] = useState(false);
  const selected = async event => {
    const file = event.target.files[0];
    await upload(file);
    if (input.current) input.current.value = '';
  };
  const dropped = event => {
    event.preventDefault(); setDrag(false);
    if (!busy) upload(event.dataTransfer.files[0]);
  };
  return <><input type="file" accept="image/jpeg,image/png,image/webp,application/pdf" ref={input} onChange={selected} hidden data-testid="receipt-file-input"/>
    <button className={`upload-zone ${drag ? 'dragging' : ''}`} data-testid="receipt-dropzone" disabled={busy} onClick={() => input.current?.click()} onDragOver={event => { event.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={dropped}>
      <span className="upload-icon">{busy ? <Loader2 className="spin" size={26}/> : <UploadCloud size={26}/>}</span><strong>{busy ? 'Salvando e lendo seu comprovante...' : 'Um comprovante a menos na sua mesa.'}</strong><span>{busy ? 'A identificação pode levar alguns instantes.' : 'Arraste o arquivo ou selecione uma foto do comprovante'}</span><small>JPG, PNG, WEBP ou PDF · até 10 MB</small><span className="upload-cta">{busy ? 'Identificando com IA' : 'Adicionar comprovante'} {!busy && <ArrowUpRight size={15}/>}</span>
    </button></>;
};