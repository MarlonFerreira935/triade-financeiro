"""Small, deterministic rules; no network or database side effects."""
import hashlib
from collections import defaultdict
from dataclasses import dataclass

RULES = [
    {'id':'margin_drop','name':'Queda de margem líquida','criterion':'Queda de pelo menos 5 pontos percentuais em relação ao mês anterior com dados.'},
    {'id':'low_margin','name':'Margem líquida baixa','criterion':'Margem líquida menor que 15% da receita líquida, referência da planilha.'},
    {'id':'expense_spike','name':'Aumento relevante de despesas','criterion':'Categoria aumenta pelo menos 20% e R$ 500 em relação ao mês anterior; não é uma comparação com orçamento.'},
    {'id':'negative_cash','name':'Caixa livre gerado negativo','criterion':'Lucro menos retiradas e investimentos resulta em valor negativo. Não representa saldo bancário nem previsão.'},
    {'id':'withdrawals','name':'Retiradas elevadas','criterion':'Retiradas e investimentos superam o lucro do mês, ou pró-labore e distribuição ultrapassam 15% da receita bruta.'},
    {'id':'break_even','name':'Receita abaixo do equilíbrio','criterion':'Receita líquida menor que o ponto de equilíbrio operacional, segundo a metodologia da DRE.'},
]


def previous_month(month):
    year, number = map(int, month.split('-'))
    return f'{year if number > 1 else year - 1}-{number - 1 if number > 1 else 12:02}'


def brl(value):
    return 'R$ ' + f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def percentage(value):
    return f'{value:.1f}'.replace('.', ',')


def category_totals(records):
    result = defaultdict(float)
    for record in records:
        if record['type'] == 'despesa' and int(record['account_id']) < 70:
            result[record['category']] += record['amount']
    return {key: round(value, 2) for key, value in result.items()}


@dataclass(frozen=True)
class AlertContext:
    month: str
    current: dict
    previous: dict

    def make(self, rule, severity, title, description, action, metric, category=None):
        identity = hashlib.sha256(f'{self.month}:{rule}:{category or ""}'.encode()).hexdigest()[:24]
        return {'id': identity, 'month': self.month, 'rule': rule, 'severity': severity,
                'title': title, 'description': description, 'action': action, 'metric': metric,
                'category': category, 'source': 'DRE e lançamentos confirmados',
                'comparison_month': previous_month(self.month) if self.previous['count'] else None}


def margin_drop_alert(context):
    current, previous = context.current, context.previous
    if previous['net_revenue'] <= 0 or current['net_revenue'] <= 0:
        return None
    drop = previous['margin'] - current['margin']
    if drop < 5:
        return None
    return context.make('margin_drop', 'critico' if drop >= 10 else 'atencao', 'Sua margem perdeu força',
        f"A margem líquida caiu de {percentage(previous['margin'])}% para {percentage(current['margin'])}%: queda de {percentage(drop)} pontos percentuais.",
        'Revise custos de produção, descontos e preço dos projetos antes de assumir novas despesas fixas.', f'−{percentage(drop)} p.p.')


def low_margin_alert(context):
    current = context.current
    if current['net_revenue'] <= 0 or current['margin'] >= 15:
        return None
    return context.make('low_margin', 'critico' if current['profit'] < 0 else 'atencao', 'Resultado abaixo da referência',
        f"A margem líquida é de {percentage(current['margin'])}%, abaixo da referência de 15% indicada na sua planilha.",
        'Reavalie a contribuição de cada projeto e priorize a revisão dos maiores custos.', f"{percentage(current['margin'])}%")


def negative_cash_alert(context):
    cash = context.current['free_cash']
    if cash >= 0:
        return None
    return context.make('negative_cash', 'critico', 'Caixa livre gerado está negativo',
        f'O resultado após retiradas e investimentos é {brl(cash)}. Esse déficit pode pressionar o capital de giro; não informa o saldo disponível em banco.',
        'Revise retiradas, adie investimentos não essenciais e confira os vencimentos com o saldo bancário real.', brl(cash))


def withdrawals_alert(context):
    current = context.current
    if current['withdrawals'] > current['profit'] and current['withdrawals'] > 0:
        return context.make('withdrawals', 'critico', 'Saídas após o lucro superam o resultado',
            f"Retiradas e investimentos de {brl(current['withdrawals'])} superam o lucro de {brl(current['profit'])}.",
            'Defina um teto temporário de retiradas e preserve capital de giro.', brl(current['withdrawals'] - current['profit']))
    owners = current['accounts']['70'] + current['accounts']['71']
    if current['revenue'] <= 0 or owners / current['revenue'] <= .15:
        return None
    ratio = owners / current['revenue'] * 100
    return context.make('withdrawals', 'atencao', 'Retiradas merecem acompanhamento',
        f'Pró-labore e distribuição somam {brl(owners)}: {percentage(ratio)}% da receita bruta, acima da referência de 15% da planilha.',
        'Vincule as próximas retiradas ao lucro efetivo e à reserva necessária para o giro.', f'{percentage(ratio)}%')


def break_even_alert(context):
    current = context.current
    if not current['break_even'] or current['net_revenue'] >= current['break_even']:
        return None
    return context.make('break_even', 'critico', 'Receita abaixo do ponto de equilíbrio',
        f"A receita líquida de {brl(current['net_revenue'])} é inferior ao equilíbrio operacional de {brl(current['break_even'])}.",
        'Priorize projetos com maior contribuição e reavalie a estrutura de custos fixos.', brl(current['break_even'] - current['net_revenue']))


def is_material_increase(value, previous):
    return previous > 0 and value >= previous * 1.2 and value - previous >= 500


def expense_spike_alerts(context, records, previous_records):
    previous_categories = category_totals(previous_records)
    alerts = []
    for category, value in category_totals(records).items():
        previous = previous_categories.get(category, 0)
        if not is_material_increase(value, previous):
            continue
        growth = (value / previous - 1) * 100
        alerts.append(context.make('expense_spike', 'atencao', f'Aumento em {category.lower()}',
            f'A categoria passou de {brl(previous)} para {brl(value)}, alta de {percentage(growth)}% frente ao mês anterior. Não há orçamento cadastrado para comparar.',
            'Confira os lançamentos e se o aumento acompanha o volume de projetos e o faturamento.', f'+{percentage(growth)}%', category))
    return alerts


def calculate_alerts(month, current, previous, records, previous_records):
    if not current['count']:
        return []
    context = AlertContext(month, current, previous)
    rules = (margin_drop_alert, low_margin_alert, negative_cash_alert, withdrawals_alert, break_even_alert)
    alerts = [alert for rule in rules if (alert := rule(context)) is not None]
    alerts.extend(expense_spike_alerts(context, records, previous_records))
    return sorted(alerts, key=lambda item: item['severity'] != 'critico')