import { dreRowClass, dreValue, verticalValue } from '../../lib/dre';

const DreRow = ({ row, columns, current, net, months, year }) => <tr className={dreRowClass(row)} data-testid={`dre-row-${row.row}`}>
  <td>{row.account && <span className="account-indent"/>}{row.label}</td>
  {columns.map(column => <td key={`${year}-${column}`} className="amount" data-label={`${months[column]}/${String(year).slice(-2)}`} data-testid={`dre-value-${row.row}-${column + 1}`}>{dreValue(row, column)}</td>)}
  <td className="muted amount" data-testid={`dre-vertical-${row.row}`}>{verticalValue(row, current, net)}</td>
</tr>;

export const DreTable = ({ rows, columns, current, net, months, year }) => <div className="table-scroll dre-scroll"><table className="dre-table" data-testid="dre-table"><thead><tr><th>PLANO DE CONTAS GERENCIAL</th>{columns.map(column => <th key={`${year}-${column}`}>{months[column]} / {String(year).slice(-2)}</th>)}<th>AV (%)</th></tr></thead><tbody>
  {rows.map(row => <DreRow key={row.row} row={row} columns={columns} current={current} net={net} months={months} year={year}/>)}
</tbody></table></div>;