"""Workbook formatting is separate from the financial calculation rules."""
import io

import openpyxl
from openpyxl.styles import Font, PatternFill

LEDGER_NAME = 'Lançamentos do Sistema'
LEDGER_HEADERS = ['Data', 'Descrição', 'Tipo', 'Categoria', 'Conta DRE', 'Valor', 'Origem', 'Comprovante', 'Observação']


def excel_safe(value):
    if isinstance(value, str) and value.startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


class WorkbookExporter:
    def __init__(self, template, account_rows, account_map, calculate_totals):
        self.template = template
        self.account_rows = account_rows
        self.account_map = account_map
        self.calculate_totals = calculate_totals

    def update_accounts(self, workbook, records, year):
        sheet = workbook['DRE Gerencial']
        for month in range(1, 13):
            monthly = [record for record in records if record['date'].startswith(f'{year}-{month:02}')]
            totals = self.calculate_totals(monthly)
            for row in self.account_rows:
                sheet.cell(row, month + 1, totals['accounts'][str(row)])

    def ledger_row(self, record):
        values = [record['date'], record['description'], record['type'], record['category'],
                  self.account_map[record['account_id']]['name'], record['amount'], record['source'],
                  record.get('receipt_id') or '', record.get('note') or '']
        return [excel_safe(value) for value in values]

    @staticmethod
    def style_ledger(ledger):
        for cell in ledger[1]:
            cell.font = Font(bold=True, color='D9A33E')
            cell.fill = PatternFill('solid', fgColor='121418')
        for column in ('A', 'C', 'F', 'G'):
            ledger.column_dimensions[column].width = 20
        for column in ('B', 'D', 'E', 'H', 'I'):
            ledger.column_dimensions[column].width = 48
        ledger.freeze_panes = 'A2'

    def add_ledger(self, workbook, records):
        if LEDGER_NAME in workbook.sheetnames:
            del workbook[LEDGER_NAME]
        ledger = workbook.create_sheet(LEDGER_NAME)
        ledger.append(LEDGER_HEADERS)
        for record in records:
            ledger.append(self.ledger_row(record))
        self.style_ledger(ledger)

    def export(self, records, year):
        workbook = openpyxl.load_workbook(self.template)
        try:
            self.update_accounts(workbook, records, year)
            self.add_ledger(workbook, records)
            workbook.calculation.fullCalcOnLoad = True
            output = io.BytesIO()
            workbook.save(output)
            return output.getvalue()
        finally:
            workbook.close()