import axios from 'axios';
export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const api = axios.create({baseURL:API,timeout:120000});
export const money = value => new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(value || 0);
export const shortMoney = value => new Intl.NumberFormat('pt-BR',{notation:'compact',maximumFractionDigits:0}).format(value || 0);
export const monthLabel = value => new Date(`${value}-02T12:00:00`).toLocaleDateString('pt-BR',{month:'long',year:'numeric'});
export const dateLabel = value => new Date(`${value}T12:00:00`).toLocaleDateString('pt-BR');
export const errorText = e => typeof e.response?.data?.detail==='string' ? e.response.data.detail : 'Não foi possível concluir. Confira os dados e tente novamente.';
export async function downloadFile(path,filename){
  const response=await api.get(path,{responseType:'blob'});
  const url=URL.createObjectURL(response.data);const link=document.createElement('a');link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}