# Tríade Financeiro — Documento do produto

## Solicitação original
“Quero desenvolver uma ferramenta financeira via WhatsApp bussines Onde eu mando uma planilha Dre e integre a ferramenta cada despesa eu informo ou tudo cá foto o sistema identifica lê lança na planilha salva e vai dando diagnósticos Sistema financeiro Triade Porto Alegre Obs Salva em os comprovantes por mês e por tipo de despesa”.

O usuário enviou a planilha `TRIADE_ERP_FINANCEIRO FINAL PADRÃO (2).xlsx` e a marca Tríade Móveis sob Medida Porto Alegre. As opções iniciais foram puladas, aceitando painel primeiro, leitura de fotos com IA Gemini, importação dos dados reais e conexão WhatsApp em fase posterior.

### Preferências confirmadas
- “quero enviar o modelo de Dre que uso para não alterar a não ser que seja para melhorar”.
- “Planilha DRE (manter estrutura, só melhorar se necessário)”.
- “Logo da Tríade (preto e dourado, identidade visual a ser preservada)”.
- Os arquivos reenviados pelo usuário são byte a byte idênticos aos primeiros. SHA256 Excel: `18331159c57726acba343f7a8db0c6323dad9c5cb796b1bc25d09fbb48095782`.

### Solicitação adicional — consultor conversacional
“Adicionar ao Tríade Financeiro um módulo de IA conversacional como consultor financeiro virtual. O consultor deve:
- Ter acesso em tempo real aos dados financeiros do app (DRE, lançamentos, KPIs)
- Conversar via chat dentro do app web, respondendo perguntas sobre saúde financeira do negócio
- Criar alertas automáticos de pontos críticos nas finanças, como queda de margem, despesas acima do esperado ou risco de fluxo de caixa negativo
- Sugerir ações, alertar sobre pontos fracos e identificar oportunidades com base nos dados reais
- Ter linguagem de consultor financeiro especialista, não de chatbot genérico
- Futuramente preparado para integração via WhatsApp Business”.

## Personas
- Sócio/gestor da Tríade: acompanha resultado, margem, retiradas, riscos e oportunidades.
- Responsável financeiro: importa a DRE, registra movimentos e confere comprovantes.
- Contador/consultor: consulta o modelo original e recebe Excel atualizado para análise.

## Requisitos permanentes
- Português brasileiro, moeda BRL, marca preta/dourada.
- Preservar contas, fórmulas, abas e identidade do modelo original.
- Não inventar lançamentos, saldos bancários ou dados de orçamento.
- Dados importados são consolidados mensais, não comprovantes de pagamentos individuais.
- Comprovantes organizados por competência mensal e categoria, com ligação ao lançamento confirmado.
- IA somente leitura no consultor; nenhuma movimentação financeira executada pelo chat.
- WhatsApp deve mostrar status verdadeiro; não há envio real sem conexão oficial.

## Arquitetura
- React 19, React Router, componentes Radix/Shadcn, Sonner, Lucide, Recharts, React Markdown.
- FastAPI, MongoDB/Motor, openpyxl para preservar workbook e gerar exportação.
- Frontend usa exclusivamente `REACT_APP_BACKEND_URL`; MongoDB usa `MONGO_URL`. Serviços gerenciados nas portas existentes.
- Gemini `gemini-3-flash-preview` via emergentintegrations. Chave em ambiente, nunca no frontend.
- Object storage gerenciado para comprovantes; arquivos servidos por rotas backend, metadados no MongoDB.
- `finance.py`: plano de contas fiel às linhas originais, importação idempotente, totais com Decimal e exportação.
- `advisor_service.py`: serviço independente de canal, retrato financeiro atualizado em cada pergunta, regras determinísticas de alertas e consultoria streaming.
- `advisor_routes.py`: conversas persistentes por período, histórico, SSE POST, proteção contra geração concorrente e limite de mensagem.
- Alertas são calculados a partir dos dados atuais na leitura e atualizados no painel após mutações; não há agendamento, envio externo, timer de tarefas nem orçamento fictício.
- Coleções: transactions, receipts, imports, settings, diagnostics, conversations, advisor_messages, alert_acknowledgements.

## Implementado — 2026-10-05
- Painel real com receitas, custos/despesas, lucro, geração de caixa, evolução mensal/acumulada e distribuição por categoria.
- Importação inicial dos consolidados reais da DRE de maio a julho de 2026, sem lançamentos financeiros fictícios.
- CRUD de receitas/despesas, busca, filtros, confirmação de exclusão e recálculo de DRE.
- DRE fiel ao plano de contas com visualização mensal/comparativa, linhas recolhíveis, AV e exportação.
- Excel mantém as **14 abas originais**, fórmulas e estilos, adicionando somente uma aba de auditoria dos lançamentos. Original disponível intacto.
- Reimportação do modelo idempotente; reimportação de export do sistema bloqueada para evitar somar novamente os mesmos lançamentos.
- Upload de JPG/PNG/WEBP com IA para data, valor, descrição e conta. Confirmação antes do lançamento. PDFs armazenados com preenchimento manual.
- Arquivo de comprovantes, filtros por mês/categoria, visualização/download, status pendente/lançado e bloqueio de vínculo duplicado sequencial.
- Diagnósticos Gemini reais, streaming, persistência e simulação independente de resultado.
- Página WhatsApp com checklist e estado **não conectado**; nenhum webhook real ou mensagem WhatsApp implementado ainda.

## Implementado — 2026-10-06
- Rota `/consultor`: chat financeiro especializado, mensagens em streaming, sugestões de perguntas baseadas no negócio, fontes/competência e contadores reais.
- Conversas por período, seleção do histórico, nova conversa, exclusão confirmada, memória de múltiplos turnos e persistência após recarregamento.
- Retrato consultado do banco a cada pergunta: DRE, contas, KPIs, comparativo mensal, até 36 meses de histórico e até 80 movimentos detalhados do período; contagem total é informada ao modelo.
- Guardrail determinístico para período sem dados: resposta explica a ausência e orienta a selecionar/importar dados, sem importar conclusões de outro mês.
- Consultor distingue caixa livre gerado de saldo bancário e não promete alterações, pagamentos ou envio WhatsApp.
- Rota `/alertas`: severidades, filtro todos/críticos/não lidos, critérios transparentes, marcar visto/não lido e analisar alerta no consultor com pergunta pré-preenchida.
- Regras: queda de margem ≥5 p.p.; margem <15%; aumento de categoria ≥20% e ≥R$500; caixa livre negativo; retiradas elevadas; receita abaixo do equilíbrio.
- Critérios de aumento comparam histórico, NÃO orçamento inexistente. Caixa negativo não é apresentado como saldo bancário ou previsão.
- Notificações reais no cabeçalho, contador no menu e faixa de atenção no dashboard.
- Um alerta visto volta a não lido se a métrica monitorada mudar.
- Serviço de consultoria preparado para futuro adaptador WhatsApp, sem afirmar conexão ativa.
- Melhorias mobile: lançamentos em linhas adaptadas, DRE comparativa com rótulos por mês, menu móvel, chat e formulários responsivos.
- Correção de estado obsoleto ao alternar meses e de persistência/liberação de conversa interrompida.

## Referência de conferência — julho/2026
- Receita bruta: R$ 266.000,00.
- Receita líquida: R$ 248.428,86.
- Custos/despesas: R$ 165.070,21.
- Lucro líquido: R$ 102.522,79.
- Retiradas: R$ 45.000,00.
- Caixa livre gerado: R$ 57.522,79.
- Margem líquida: 41,27% da receita líquida.
- Ponto de equilíbrio operacional: R$ 39.279,10 conforme método da planilha.

## Validação
- Build React concluído com sucesso.
- Testador especialista executou backend e fluxos UI: consultor, histórico, alertas, lançamentos, DRE, comprovantes, planilhas, diagnósticos e WhatsApp pendente.
- Corrigida hipótese do teste original: 14 abas, não 15.
- Corrigida inferência indevida de saúde financeira de outro mês quando período estava sem dados.
- Reexecução final: **16 testes aprovados, zero falhas**, em `/app/test_reports/pytest/final_results.xml` e `/app/test_reports/final_pytest.log`.
- Relatório inicial da nova funcionalidade: `/app/test_reports/iteration_2.json`; seu único defeito HIGH foi corrigido e retestado na suíte final.
- Screenshots main agent em 1920×800 e 390×844. Overflow horizontal final vazio no consultor, dashboard com gráficos após animação, lançamentos e DRE comparativa.
- Integrações de IA e object storage são reais, sem APIs simuladas.

## Limitações e backlog priorizado
### P0 — antes de uso amplo com dados privados
- Controle de acesso para o workspace e rotas de arquivos/chat. A versão atual é single-workspace, sem autenticação; não tratar a URL como controle de acesso.
### P1 — próxima etapa do produto
- Receber credenciais oficiais Meta e conectar WhatsApp Business: webhook assinado, mídia, permissões do remetente e adaptação do serviço consultor existente.
- Implementar orçamentos/metas por categoria para comparar realizado versus esperado em vez de somente histórico.
- OCR de PDF, além do armazenamento atual com preenchimento manual.
- Refinar proteção de concorrência no vínculo comprovante/lançamento e importações atômicas conforme aumento de uso.
### P2 — evolução
- Configuração dos limiares de alertas pelo gestor.
- Projeções reais de caixa com vencimentos e saldos fornecidos, sem inferir da DRE.
- Monitoramento entre múltiplas sessões/push; atualmente consulta atual em cada pergunta e após ações no painel.
- Eventuais lembretes agendados: se solicitados, usar mecanismo de agendamento da plataforma, não loops no app.

## Próximas ações
1. Definir/ativar acesso privado antes de compartilhar o workspace com terceiros.
2. Conectar número oficial WhatsApp quando as credenciais estiverem disponíveis.
3. Adicionar metas por categoria para tornar os alertas de desvio mais precisos.
