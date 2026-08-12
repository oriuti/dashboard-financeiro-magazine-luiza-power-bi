"""Gera um projeto Power BI (PBIP/PBIR/TMDL) versionável a partir dos dados tratados."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import uuid
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "data" / "processed" / "indicadores_anuais.csv"
PASTA_PBI = RAIZ / "powerbi"
NOME = "Dashboard Financeiro Magazine Luiza"
PASTA_MODELO = PASTA_PBI / f"{NOME}.SemanticModel"
PASTA_RELATORIO = PASTA_PBI / f"{NOME}.Report"
SCHEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json"
TEMA = "PortfolioDados-7b6d4e2a.json"


def gravar_json(caminho: Path, conteudo: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def identificador(texto: str) -> str:
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:20]


def lineage_guid(texto: str) -> str:
    namespace = uuid.UUID("f32b3710-c5ee-47f0-82f8-11fd70a65bb9")
    return str(uuid.uuid5(namespace, texto))


def literal(texto: str) -> dict:
    seguro = texto.replace("'", "''")
    return {"expr": {"Literal": {"Value": f"'{seguro}'"}}}


def projecao_medida(nome: str) -> dict:
    return {
        "field": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": "Medidas"}},
                "Property": nome,
            }
        },
        "queryRef": f"Medidas.{nome}",
        "nativeQueryRef": nome,
    }


def projecao_ano() -> dict:
    return {
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": "Financeiro"}},
                "Property": "Ano",
            }
        },
        "queryRef": "Financeiro.Ano",
        "nativeQueryRef": "Ano",
    }


def titulo_visual(texto: str) -> dict:
    return {
        "title": [
            {
                "properties": {
                    "text": literal(texto),
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                }
            }
        ]
    }


def visual_card(nome: str, medidas: list[str], posicao: dict) -> dict:
    return {
        "$schema": SCHEMA_VISUAL,
        "name": nome,
        "position": posicao,
        "visual": {
            "visualType": "cardVisual",
            "query": {
                "queryState": {
                    "Data": {"projections": [projecao_medida(m) for m in medidas]}
                }
            },
            "drillFilterOtherVisuals": True,
        },
    }


def visual_grafico(
    nome: str,
    tipo: str,
    medidas_y: list[str],
    posicao: dict,
    titulo: str,
    medidas_y2: list[str] | None = None,
) -> dict:
    estado = {
        "Category": {"projections": [projecao_ano()]},
        "Y": {"projections": [projecao_medida(m) for m in medidas_y]},
    }
    if medidas_y2:
        estado["Y2"] = {"projections": [projecao_medida(m) for m in medidas_y2]}
    return {
        "$schema": SCHEMA_VISUAL,
        "name": nome,
        "position": posicao,
        "visual": {
            "visualType": tipo,
            "query": {"queryState": estado},
            "drillFilterOtherVisuals": True,
            "visualContainerObjects": titulo_visual(titulo),
        },
    }


def medida_tmdl(nome: str, expressao: str, formato: str, tag: str) -> str:
    corpo = "\n".join(f"\t\t{linha}" for linha in expressao.splitlines())
    return (
        f"\tmeasure '{nome}' = ```\n{corpo}\n\t\t```\n"
        f"\t\tlineageTag: {tag}\n"
        f"\t\tformatString: {formato}\n"
    )


def gerar_tmdl(df: pd.DataFrame) -> None:
    definicao = PASTA_MODELO / "definition"
    tabelas = definicao / "tables"
    tabelas.mkdir(parents=True, exist_ok=True)

    gravar_json(
        PASTA_MODELO / "definition.pbism",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "4.2",
            "settings": {"qnaEnabled": True},
        },
    )
    gravar_json(
        PASTA_MODELO / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "config": {
                "version": "2.0",
                "logicalId": "3f9a4b55-ae55-49f8-9d31-4a0fe6f29b0e",
            },
            "metadata": {"type": "SemanticModel", "displayName": NOME},
        },
    )
    (definicao / "database.tmdl").write_text(
        "database\n\tcompatibilityLevel: 1604\n", encoding="utf-8"
    )
    (definicao / "model.tmdl").write_text(
        "model Model\n"
        "\tculture: pt-BR\n"
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tsourceQueryCulture: en-US\n\n"
        "ref table Financeiro\n"
        "ref table Medidas\n",
        encoding="utf-8",
    )

    colunas_excluidas = {"Empresa", "CNPJ", "Data_Referencia"}
    colunas_numericas = [
        coluna
        for coluna in df.columns
        if coluna not in colunas_excluidas and coluna != "Ano"
    ]

    linhas_m: list[str] = []
    for _, linha in df.iterrows():
        valores = [str(int(linha["Ano"]))]
        for coluna in colunas_numericas:
            valor = linha[coluna]
            valores.append("null" if pd.isna(valor) else format(float(valor), ".10g"))
        valores.extend(
            [
                f'#date({int(linha["Ano"])}, 12, 31)',
                '"MAGAZINE LUIZA S.A."',
                '"47.960.950/0001-21"',
            ]
        )
        linhas_m.append("\t\t\t{" + ", ".join(valores) + "}")

    definicoes_tipo = ["Ano = Int64.Type"]
    definicoes_tipo.extend(f"{coluna} = nullable number" for coluna in colunas_numericas)
    definicoes_tipo.extend(
        ["Data_Referencia = date", "Empresa = text", "CNPJ = text"]
    )
    tipos_m = ", ".join(definicoes_tipo)
    dados_m = ",\n".join(linhas_m)

    colunas_tmdl = [
        f"\tcolumn Ano\n\t\tlineageTag: {lineage_guid('coluna-Ano')}\n\t\tdataType: int64\n\t\tsummarizeBy: none\n\t\tsourceColumn: Ano\n\t\tformatString: 0\n"
    ]
    for indice, coluna in enumerate(colunas_numericas, start=1):
        colunas_tmdl.append(
            f"\tcolumn {coluna}\n"
            f"\t\tlineageTag: {lineage_guid('coluna-' + coluna)}\n"
            "\t\tdataType: double\n"
            "\t\tsummarizeBy: sum\n"
            f"\t\tsourceColumn: {coluna}\n"
            "\t\tformatString: #,##0.0\n"
        )
    colunas_tmdl.extend(
        [
            f"\tcolumn Data_Referencia\n\t\tlineageTag: {lineage_guid('coluna-Data_Referencia')}\n\t\tdataType: dateTime\n\t\tsummarizeBy: none\n\t\tsourceColumn: Data_Referencia\n\t\tformatString: yyyy\n",
            f"\tcolumn Empresa\n\t\tlineageTag: {lineage_guid('coluna-Empresa')}\n\t\tdataType: string\n\t\tsummarizeBy: none\n\t\tsourceColumn: Empresa\n",
            f"\tcolumn CNPJ\n\t\tlineageTag: {lineage_guid('coluna-CNPJ')}\n\t\tdataType: string\n\t\tsummarizeBy: none\n\t\tsourceColumn: CNPJ\n",
        ]
    )

    financeiro = (
        "table Financeiro\n"
        f"\tlineageTag: {lineage_guid('tabela-financeiro')}\n\n"
        + "\n".join(colunas_tmdl)
        + "\n\tpartition Financeiro = m\n"
        "\t\tmode: import\n"
        "\t\tsource =\n"
        "\t\t\tlet\n"
        f"\t\t\t\tFonte = #table(type table [{tipos_m}],\n"
        "\t\t\t\t{\n"
        f"{dados_m}\n"
        "\t\t\t\t})\n"
        "\t\t\tin\n"
        "\t\t\t\tFonte\n"
    )
    (tabelas / "Financeiro.tmdl").write_text(financeiro, encoding="utf-8")

    f_moeda = "R$ #,##0.0;[Red]-R$ #,##0.0"
    f_percentual = "0.0%;[Red]-0.0%"
    f_indice = "0.00x"
    medidas: list[tuple[str, str, str]] = [
        ("Receita", "SUM(Financeiro[Receita])", f_moeda),
        ("Lucro Bruto", "SUM(Financeiro[Lucro_Bruto])", f_moeda),
        ("Resultado Operacional", "SUM(Financeiro[Resultado_Operacional])", f_moeda),
        ("Lucro Líquido", "SUM(Financeiro[Lucro_Liquido])", f_moeda),
        ("FCO", "SUM(Financeiro[FCO])", f_moeda),
        ("FCI", "SUM(Financeiro[FCI])", f_moeda),
        ("FCF", "SUM(Financeiro[FCF])", f_moeda),
        ("Fluxo de Caixa Livre", "SUM(Financeiro[Fluxo_Caixa_Livre])", f_moeda),
        ("Capex", "SUM(Financeiro[Capex])", f_moeda),
        ("Caixa", "SUM(Financeiro[Caixa])", f_moeda),
        ("Contas a Receber", "SUM(Financeiro[Contas_a_Receber])", f_moeda),
        ("Estoques", "SUM(Financeiro[Estoques])", f_moeda),
        ("Ativo Circulante", "SUM(Financeiro[Ativo_Circulante])", f_moeda),
        ("Passivo Circulante", "SUM(Financeiro[Passivo_Circulante])", f_moeda),
        ("Dívida Líquida", "SUM(Financeiro[Divida_Liquida])", f_moeda),
        ("Patrimônio Líquido", "SUM(Financeiro[Patrimonio_Liquido])", f_moeda),
        ("Margem Bruta", "DIVIDE([Lucro Bruto], [Receita])", f_percentual),
        ("Margem Operacional", "DIVIDE([Resultado Operacional], [Receita])", f_percentual),
        ("Margem Líquida", "DIVIDE([Lucro Líquido], [Receita])", f_percentual),
        ("Liquidez Corrente", "DIVIDE([Ativo Circulante], [Passivo Circulante])", f_indice),
        ("ROE", "DIVIDE([Lucro Líquido], SUM(Financeiro[Patrimonio_Liquido]))", f_percentual),
    ]

    medidas_atuais = [
        ("Receita Atual", "Receita", f_moeda),
        ("Lucro Líquido Atual", "Lucro Líquido", f_moeda),
        ("Margem Líquida Atual", "Margem Líquida", f_percentual),
        ("Margem Bruta Atual", "Margem Bruta", f_percentual),
        ("Resultado Operacional Atual", "Resultado Operacional", f_moeda),
        ("FCO Atual", "FCO", f_moeda),
        ("Fluxo de Caixa Livre Atual", "Fluxo de Caixa Livre", f_moeda),
        ("Capex Atual", "Capex", f_moeda),
        ("Caixa Atual", "Caixa", f_moeda),
        ("Dívida Líquida Atual", "Dívida Líquida", f_moeda),
        ("Liquidez Corrente Atual", "Liquidez Corrente", f_indice),
        ("Estoques Atual", "Estoques", f_moeda),
        ("Patrimônio Líquido Atual", "Patrimônio Líquido", f_moeda),
        ("ROE Atual", "ROE", f_percentual),
    ]
    for nome, base, formato in medidas_atuais:
        expressao = (
            "VAR AnoAtual = MAXX(ALL(Financeiro), Financeiro[Ano])\n"
            f"RETURN CALCULATE([{base}], FILTER(ALL(Financeiro), Financeiro[Ano] = AnoAtual))"
        )
        medidas.append((nome, expressao, formato))

    medidas.extend(
        [
            (
                "Crescimento Receita Atual",
                "VAR AnoAtual = MAXX(ALL(Financeiro), Financeiro[Ano])\n"
                "VAR Atual = CALCULATE([Receita], FILTER(ALL(Financeiro), Financeiro[Ano] = AnoAtual))\n"
                "VAR Anterior = CALCULATE([Receita], FILTER(ALL(Financeiro), Financeiro[Ano] = AnoAtual - 1))\n"
                "RETURN DIVIDE(Atual - Anterior, Anterior)",
                f_percentual,
            ),
            (
                "Ano Atual",
                "MAXX(ALL(Financeiro), Financeiro[Ano])",
                "0",
            ),
        ]
    )

    blocos = []
    for indice, (nome, expressao, formato) in enumerate(medidas, start=1):
        tag = lineage_guid(f"medida-{indice}-{nome}")
        blocos.append(medida_tmdl(nome, expressao, formato, tag))

    tabela_medidas = (
        "table Medidas\n"
        f"\tlineageTag: {lineage_guid('tabela-medidas')}\n\n"
        + "\n".join(blocos)
        + "\n\tpartition Medidas = m\n"
        "\t\tmode: import\n"
        "\t\tsource =\n"
        "\t\t\tlet\n"
        "\t\t\t\tFonte = #table(type table [Chave = nullable number], {})\n"
        "\t\t\tin\n"
        "\t\t\t\tFonte\n"
    )
    (tabelas / "Medidas.tmdl").write_text(tabela_medidas, encoding="utf-8")


def gerar_relatorio() -> None:
    gravar_json(
        PASTA_PBI / f"{NOME}.pbip",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{NOME}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    gravar_json(
        PASTA_RELATORIO / "definition.pbir",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {"byPath": {"path": f"../{NOME}.SemanticModel"}},
        },
    )
    gravar_json(
        PASTA_RELATORIO / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "config": {
                "version": "2.0",
                "logicalId": "9cb38ba1-2fbf-4fe5-a4f4-89c0e55b839d",
            },
            "metadata": {"type": "Report", "displayName": NOME},
        },
    )
    gravar_json(
        PASTA_RELATORIO / "definition" / "version.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "2.0.0",
        },
    )

    versoes_tema = {"visual": "1.8.95", "report": "2.0.95", "page": "1.3.95"}
    gravar_json(
        PASTA_RELATORIO / "definition" / "report.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.2.0/schema.json",
            "themeCollection": {
                "baseTheme": {
                    "name": "CY24SU10",
                    "reportVersionAtImport": versoes_tema,
                    "type": "SharedResources",
                },
                "customTheme": {
                    "name": TEMA,
                    "reportVersionAtImport": versoes_tema,
                    "type": "RegisteredResources",
                },
            },
            "resourcePackages": [
                {
                    "name": "SharedResources",
                    "type": "SharedResources",
                    "items": [
                        {
                            "name": "CY24SU10",
                            "path": "BaseThemes/CY24SU10.json",
                            "type": "BaseTheme",
                        }
                    ],
                },
                {
                    "name": "RegisteredResources",
                    "type": "RegisteredResources",
                    "items": [
                        {"name": TEMA, "path": TEMA, "type": "CustomTheme"}
                    ],
                },
            ],
            "settings": {
                "useStylableVisualContainerHeader": True,
                "exportDataMode": "AllowSummarized",
                "defaultDrillFilterOtherVisuals": True,
                "allowChangeFilterTypes": True,
                "useEnhancedTooltips": True,
                "useDefaultAggregateDisplayName": True,
            },
        },
    )

    gravar_json(
        PASTA_RELATORIO / "StaticResources" / "RegisteredResources" / TEMA,
        {
            "name": TEMA,
            "dataColors": [
                "#0F766E",
                "#2563EB",
                "#F59E0B",
                "#7C3AED",
                "#DC2626",
                "#0891B2",
                "#65A30D",
                "#475569",
            ],
            "background": "#F6F8FC",
            "foreground": "#0F172A",
            "tableAccent": "#0F766E",
            "good": "#15803D",
            "neutral": "#D97706",
            "bad": "#B91C1C",
            "textClasses": {
                "title": {"fontFace": "Segoe UI Semibold", "color": "#0F172A"},
                "header": {"fontFace": "Segoe UI Semibold", "color": "#0F172A"},
                "label": {"fontFace": "Segoe UI", "color": "#334155"},
                "callout": {"fontFace": "Segoe UI Semibold", "color": "#0F172A"},
            },
        },
    )

    paginas = [
        {
            "chave": "visao-executiva",
            "nome": "Visão Executiva",
            "cards": ["Receita Atual", "Crescimento Receita Atual", "Lucro Líquido Atual", "Margem Líquida Atual"],
            "graficos": [
                ("lineClusteredColumnComboChart", ["Receita"], ["Margem Líquida"], "Receita e margem líquida"),
                ("lineChart", ["Caixa", "Dívida Líquida"], None, "Caixa e dívida líquida"),
            ],
        },
        {
            "chave": "resultado",
            "nome": "DRE e Margens",
            "cards": ["Receita Atual", "Lucro Bruto", "Resultado Operacional Atual", "Lucro Líquido Atual"],
            "graficos": [
                ("clusteredColumnChart", ["Receita", "Lucro Bruto"], None, "Receita e lucro bruto"),
                ("lineChart", ["Margem Bruta", "Margem Operacional", "Margem Líquida"], None, "Evolução das margens"),
            ],
        },
        {
            "chave": "fluxo-caixa",
            "nome": "Fluxo de Caixa",
            "cards": ["FCO Atual", "Fluxo de Caixa Livre Atual", "Capex Atual", "Caixa Atual"],
            "graficos": [
                ("clusteredColumnChart", ["FCO", "FCI", "FCF"], None, "Fluxos por atividade"),
                ("clusteredColumnChart", ["Fluxo de Caixa Livre", "Capex"], None, "Fluxo de caixa livre e capex"),
            ],
        },
        {
            "chave": "balanco",
            "nome": "Balanço e Liquidez",
            "cards": ["Liquidez Corrente Atual", "Dívida Líquida Atual", "Estoques Atual", "Patrimônio Líquido Atual"],
            "graficos": [
                ("lineChart", ["Ativo Circulante", "Passivo Circulante"], None, "Ativo e passivo circulantes"),
                ("clusteredColumnChart", ["Caixa", "Contas a Receber", "Estoques"], None, "Componentes do ativo circulante"),
            ],
        },
    ]

    ordem = [identificador(f"pagina-{pagina['chave']}") for pagina in paginas]
    gravar_json(
        PASTA_RELATORIO / "definition" / "pages" / "pages.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": ordem,
            "activePageName": ordem[0],
        },
    )

    for pagina_indice, pagina in enumerate(paginas):
        pagina_id = ordem[pagina_indice]
        pasta_pagina = PASTA_RELATORIO / "definition" / "pages" / pagina_id
        gravar_json(
            pasta_pagina / "page.json",
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
                "name": pagina_id,
                "displayName": pagina["nome"],
                "displayOption": "FitToPage",
                "width": 1280,
                "height": 720,
            },
        )

        pos_card = {"x": 20, "y": 25, "z": 1000, "height": 120, "width": 1240, "tabOrder": 1000}
        card_id = identificador(f"{pagina_id}-cards")
        gravar_json(
            pasta_pagina / "visuals" / card_id / "visual.json",
            visual_card(card_id, pagina["cards"], pos_card),
        )

        for grafico_indice, (tipo, y, y2, titulo) in enumerate(pagina["graficos"]):
            x = 20 if grafico_indice == 0 else 650
            pos = {
                "x": x,
                "y": 170,
                "z": 1001 + grafico_indice,
                "height": 520,
                "width": 610,
                "tabOrder": 1001 + grafico_indice,
            }
            visual_id = identificador(f"{pagina_id}-{grafico_indice}-{titulo}")
            gravar_json(
                pasta_pagina / "visuals" / visual_id / "visual.json",
                visual_grafico(visual_id, tipo, y, pos, titulo, y2),
            )


def main() -> int:
    df = pd.read_csv(DADOS, sep=";", decimal=",")
    gerar_tmdl(df)
    gerar_relatorio()

    origem_tema = (
        RAIZ.parent
        / "powerbi-mcp-server"
        / "sample"
        / "Contoso Coffee Shop.Report"
        / "StaticResources"
        / "SharedResources"
        / "BaseThemes"
        / "CY24SU10.json"
    )
    destino_tema = (
        PASTA_RELATORIO
        / "StaticResources"
        / "SharedResources"
        / "BaseThemes"
        / "CY24SU10.json"
    )
    if origem_tema.exists() and not destino_tema.exists():
        destino_tema.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origem_tema, destino_tema)
    if not destino_tema.exists():
        raise FileNotFoundError(
            "Tema base CY24SU10.json ausente. Consulte THIRD_PARTY_NOTICES.md."
        )

    print(PASTA_PBI / f"{NOME}.pbip")
    return 0


if __name__ == "__main__":
    sys.exit(main())
