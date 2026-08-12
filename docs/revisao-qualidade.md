# Revisões de qualidade

## Revisão 1 — técnica e de dados

Status: **aprovada**.

- Fonte oficial e URLs conferidas.
- Empresa confirmada na base pelo CNPJ `47.960.950/0001-21`.
- Demonstrações consolidadas e maior versão anual selecionadas.
- Escala original `MIL` validada antes da conversão para R$ milhões.
- 115 registros de métricas reportadas processados: 23 métricas × 5 anos.
- Chave `Ano + Métrica` sem duplicidades.
- Nenhum valor ausente nas contas selecionadas.
- Reconciliação `Ativo Total - Passivo Total = 0` em todos os anos.
- Fórmulas da planilha de auditoria inspecionadas; status geral `PASS`.
- Definição PBIR validada: **0 erros e 0 avisos**.
- Pacote de distribuição PBIP validado: arquivo ZIP íntegro, com 30 itens e todos os componentes de relatório e modelo presentes.

## Revisão 2 — visual, documental e de portfólio

Status: **aprovada**.

- Quatro páginas em 16:9 revisadas visualmente.
- Títulos, unidades, período e fonte visíveis.
- Paleta neutra e consistente, sem uso de logotipo ou aparência de material oficial da companhia.
- Números dos cards conciliados com a camada processada.
- Observação específica para a leitura do fluxo de caixa de 2024–2025.
- README revisado para explicar objetivo, perguntas, insights, pipeline, execução e limitações.
- Aviso de estudo independente incluído no README, imagens e planilha.
- Separação entre licença do código/documentação e licença dos dados.
- Links de contato do autor conferidos.

## Limitação do ambiente de validação

O Power BI Desktop não estava instalado no ambiente automatizado. O PBIR foi validado estruturalmente com a CLI oficial da Microsoft, e as imagens foram geradas a partir da mesma camada de dados, mas a abertura do `.pbip` no aplicativo deve ser feita após o clone como verificação final de execução local.
