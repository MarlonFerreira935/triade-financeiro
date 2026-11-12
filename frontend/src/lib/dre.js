import { money } from './api';

export function visibleDreRows(rows, detailed) {
  return rows.filter(row => detailed || row.subtotal || (!row.account && !/^\d\.\d/.test(row.label)));
}

export function dreColumns(current, view) {
  if (view === 'mensal') return [current];
  return Array.from({ length: Math.min(current + 1, 3) }, (_, offset) => Math.max(0, current - 2) + offset);
}

export function dreRowClass(row) {
  return [row.subtotal && 'subtotal', !row.account && !row.subtotal && 'group-row',
    row.percentage && 'percentage-row', [67, 73].includes(row.row) && 'result-row'].filter(Boolean).join(' ');
}

export function dreValue(row, column) {
  if (!row.account && !row.subtotal) return '';
  return row.percentage ? `${row.values[column].toFixed(1).replace('.', ',')}%` : money(row.values[column]);
}

export function verticalValue(row, current, net) {
  if ((!row.account && !row.subtotal) || row.percentage || !net) return '—';
  return `${(row.values[current] / net * 100).toFixed(1).replace('.', ',')}%`;
}