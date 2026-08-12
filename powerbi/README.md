# Como abrir o projeto Power BI

1. Baixe ou clone o repositório.
2. Extraia `Dashboard Financeiro Magazine Luiza - PBIP.zip` nesta pasta.
3. Use uma versão atual do Power BI Desktop com suporte ao formato PBIP/PBIR.
4. Abra `Dashboard Financeiro Magazine Luiza.pbip`.
5. Aguarde o carregamento do modelo semântico e do relatório.

Os cinco exercícios anuais estão incorporados ao modelo por Power Query M. Portanto, a primeira abertura não depende de um caminho local para CSV nem de credenciais da CVM.

## Conteúdo

- `Dashboard Financeiro Magazine Luiza.pbip`: atalho do projeto;
- `Dashboard Financeiro Magazine Luiza.SemanticModel`: modelo TMDL, dados M e 37 medidas DAX;
- `Dashboard Financeiro Magazine Luiza.Report`: páginas e visuais em PBIR.

## Atualização dos dados

Para reconstruir a camada anual de 2021–2025 com a versão disponível no portal no momento da execução:

```bash
python scripts/download_dados_cvm.py
python scripts/preparar_dados.py
python scripts/gerar_pbip.py
python scripts/empacotar_pbip.py
```

O processamento recalcula os hashes dos ZIPs e usa a maior versão da DFP encontrada para cada ano.

## Validação

A definição PBIR deste repositório foi validada com `@microsoft/powerbi-report-authoring-cli` e passou com zero erros e zero avisos. O Power BI Desktop não estava disponível no ambiente automatizado utilizado para construir o repositório; por isso, a abertura no aplicativo permanece como teste final de execução local.
