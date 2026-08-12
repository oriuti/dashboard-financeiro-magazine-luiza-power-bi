# Metodologia

## 1. Fonte e escopo

O projeto usa o conjunto público de Demonstrações Financeiras Padronizadas (DFP) do Portal de Dados Abertos da CVM. Foram selecionados os exercícios de 2021 a 2025 da Magazine Luiza S.A., identificada pelo CNPJ `47.960.950/0001-21` na própria base.

As quatro demonstrações utilizadas são:

- DRE consolidada;
- Balanço Patrimonial Ativo consolidado;
- Balanço Patrimonial Passivo consolidado;
- DFC consolidada pelo método indireto.

## 2. Critérios de seleção

Para cada ano e demonstração, o processamento aplica os seguintes filtros:

1. `CNPJ_CIA = 47.960.950/0001-21`;
2. ano de `DT_REFER` igual ao ano do arquivo;
3. maior valor disponível em `VERSAO`;
4. `ORDEM_EXERC = ÚLTIMO`;
5. demonstrações consolidadas (`*_con_*`).

O uso da maior versão captura eventuais reapresentações disponibilizadas pela CVM. Como os arquivos são atualizados periodicamente, os hashes e a versão efetiva são registrados em `data/processed/metadados.json`.

## 3. Moeda e escala

O pipeline exige `MOEDA = REAL` e `ESCALA_MOEDA = MIL`. Os valores são convertidos para R$ milhões dividindo `VL_CONTA` por 1.000.

Se a moeda ou a escala mudarem, o processamento interrompe a execução em vez de produzir números silenciosamente incorretos.

## 4. Mapeamento das contas

As métricas reportadas são selecionadas pelos códigos contábeis da CVM, não por busca livre no texto da descrição. Exemplos:

| Métrica | Demonstração | Código CVM |
|---|---:|---:|
| Receita | DRE | 3.01 |
| Resultado operacional | DRE | 3.05 |
| Lucro líquido consolidado | DRE | 3.11 |
| Caixa e equivalentes | BPA | 1.01.01 |
| Estoques | BPA | 1.01.04 |
| Passivo circulante | BPP | 2.01 |
| Patrimônio líquido | BPP | 2.03 |
| Fluxo de caixa operacional | DFC-MI | 6.01 |

O mapeamento completo está em `data/processed/dicionario_metricas.csv`.

## 5. Indicadores calculados

- `Capex = aquisição de imobilizado + aquisição de intangível`;
- `Fluxo de caixa livre = FCO + Capex`, pois o capex é reportado com sinal negativo;
- `Dívida bruta = empréstimos e financiamentos CP + LP`;
- `Dívida líquida = dívida bruta - caixa`;
- `Margem bruta = lucro bruto / receita`;
- `Margem operacional = resultado operacional / receita`;
- `Margem líquida = lucro líquido / receita`;
- `Liquidez corrente = ativo circulante / passivo circulante`;
- `ROA = lucro líquido / ativo total`;
- `ROE = lucro líquido / patrimônio líquido`.

## 6. Controles de qualidade

O processamento é interrompido quando encontra:

- empresa ausente;
- denominação inesperada;
- conta mapeada ausente ou duplicada;
- moeda ou escala diferente do esperado;
- duplicidade na chave `Ano + Métrica`;
- valores ausentes;
- diferença entre ativo total e passivo total superior a R$ 1 mil.

Além disso, os resultados são conciliados na planilha de auditoria e o relatório PBIR é validado pela ferramenta `@microsoft/powerbi-report-authoring-cli`.

## 7. Limitações analíticas

Este projeto utiliza demonstrações anuais agregadas. Não substitui a leitura de notas explicativas, relatórios da administração, fatos relevantes ou informações segmentadas. Indicadores de caixa de 2024–2025, em especial, devem ser analisados junto do detalhamento das variações de ativos e passivos apresentado na DFC.
