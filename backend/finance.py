"""Tríade's chart of accounts and workbook-compatible calculations."""
from pathlib import Path
from calendar import monthrange
from datetime import datetime, timezone
from decimal import Decimal
from bisect import bisect_left
import io
import openpyxl
from workbook_export import WorkbookExporter

TEMPLATE = Path(__file__).parent / 'assets' / 'triade_original.xlsx'
ACCOUNT_ROWS = [4,5,6,8,9,10,14,15,16,17,19,20,21,23,24,26,27,29,30,31,36,37,38,40,41,42,43,44,45,47,48,49,50,52,53,54,56,57,61,62,65,66,70,71,72]
MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

GROUP_LIMITS = (6, 10, 21, 27, 31, 38, 45, 50, 54, 57, 62, 66)
GROUP_NAMES = ('Receitas', 'Impostos e deduções', 'Matéria-prima e insumos',
               'Logística e montagem', 'Comissões', 'Pessoal', 'Ocupação e infraestrutura',
               'Administrativo e TI', 'Marketing', 'Frota e mobilidade',
               'Depreciação e provisões', 'Resultado financeiro', 'Sócios e investimentos')

def group_for(row):
    return GROUP_NAMES[bisect_left(GROUP_LIMITS, row)]

_book = openpyxl.load_workbook(TEMPLATE, data_only=True)
ACCOUNTS = [{'id': str(r), 'name': _book['DRE Gerencial'].cell(r,1).value,
             'group': group_for(r), 'type': 'receita' if r in [4,5,6,66] else 'despesa'} for r in ACCOUNT_ROWS]
ACCOUNT_MAP = {a['id']: a for a in ACCOUNTS}
ROW_LABELS = {r: _book['DRE Gerencial'].cell(r,1).value for r in range(3,74)}
_book.close()

def parse_workbook(data, year):
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    if 'DRE Gerencial' not in wb.sheetnames:
        raise ValueError('A planilha precisa conter a aba DRE Gerencial no modelo Tríade.')
    sheet = wb['DRE Gerencial']
    if any(sheet.cell(r,1).value != ACCOUNT_MAP[str(r)]['name'] for r in ACCOUNT_ROWS):
        raise ValueError('O plano de contas é diferente do modelo Tríade. Use o modelo original.')
    records = []
    for r in ACCOUNT_ROWS:
        for m in range(1,13):
            amount = sheet.cell(r,m+1).value
            if amount is None or amount == 0: continue
            if not isinstance(amount,(int,float)) or amount < 0:
                raise ValueError(f'Valor inválido em {MONTHS[m-1]}, linha {r}.')
            account = ACCOUNT_MAP[str(r)]
            records.append({'id': f'planilha-{year}-{m:02}-{r}', 'description': account['name'],
                'account_id': str(r), 'category': account['group'], 'type': account['type'],
                'amount': round(float(amount),2), 'date': f'{year}-{m:02}-{monthrange(year,m)[1]}',
                'source': 'planilha', 'status': 'confirmado', 'receipt_id': None,
                'note': 'Consolidado mensal da planilha original; não representa uma transação individual.',
                'created_at': datetime.now(timezone.utc).isoformat()})
    wb.close()
    return records

def totals(records):
    sums = {r: Decimal('0') for r in ACCOUNT_ROWS}
    for t in records:
        r = int(t['account_id'])
        sums[r] += Decimal(str(t['amount']))
    def add(start,end): return sum((v for r,v in sums.items() if start <= r <= end), Decimal('0'))
    revenue, deductions = add(4,6), add(8,10)
    net = revenue - deductions
    variable, fixed = add(14,31), add(36,57)
    contribution = net - variable
    ebitda = contribution - fixed
    depreciation = add(61,62)
    profit = ebitda - depreciation - sums[65] + sums[66]
    withdrawals = add(70,72)
    values = {'revenue': revenue, 'deductions': deductions, 'net_revenue': net,
        'variable': variable, 'fixed': fixed, 'contribution': contribution, 'ebitda': ebitda,
        'depreciation': depreciation, 'profit': profit, 'withdrawals': withdrawals,
        'free_cash': profit-withdrawals, 'expenses': deductions+variable+fixed+depreciation+sums[65],
        'financial_income': sums[66], 'financial_expenses': sums[65], 'ebit': ebitda-depreciation}
    result = {k:round(float(v),2) for k,v in values.items()}
    result['margin'] = round(float(profit/net*100),2) if net else 0
    result['contribution_margin'] = round(float(contribution/net*100),2) if net else 0
    result['break_even'] = round(float((fixed+depreciation)/(contribution/net)),2) if net and contribution > 0 else None
    result['accounts'] = {str(r): round(float(v),2) for r,v in sums.items()}
    result['count'] = len(records)
    return result

def diagnostics(t):
    if not t['count']:
        return [{'id':'no-data','level':'info','title':'Sem movimentos no período','text':'Os indicadores serão calculados a partir dos lançamentos deste mês.'}]
    return [
        {'id':'profit-margin','level':'success' if t['profit'] > 0 else 'warning', 'title':'Operação lucrativa' if t['profit'] > 0 else 'Resultado exige atenção',
         'text': f"Margem líquida de {t['margin']:.1f}% sobre a receita líquida.".replace('.',',',1)},
        {'id':'owner-withdrawals','level':'warning' if t['revenue'] and t['withdrawals']/t['revenue'] > .15 else 'success', 'title':'Retiradas dos sócios',
         'text': f"Representam {t['withdrawals']/t['revenue']*100 if t['revenue'] else 0:.1f}% da receita bruta. Referência da planilha: até 15%.".replace('.',',',1)},
        {'id':'direct-costs','level':'info','title':'Acompanhe os custos diretos','text':f"Custos variáveis comprometem {t['variable']/t['net_revenue']*100 if t['net_revenue'] else 0:.1f}% da receita líquida.".replace('.',',',1)}]

def export_workbook(records,year):
    return WorkbookExporter(TEMPLATE, ACCOUNT_ROWS, ACCOUNT_MAP, totals).export(records, year)