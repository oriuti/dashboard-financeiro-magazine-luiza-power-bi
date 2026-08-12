"""Executa controles estáticos e de dados que não dependem do Power BI Desktop."""

from __future__ import annotations

import json
import re
import sys
import uuid
import zipfile
from pathlib import Path
from urllib.parse import unquote

import pandas as pd
from PIL import Image


RAIZ = Path(__file__).resolve().parents[1]


def exigir(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise AssertionError(mensagem)


def main() -> int:
    resultados: dict[str, object] = {}

    fato = pd.read_csv(
        RAIZ / "data" / "processed" / "fato_metricas_financeiras.csv",
        sep=";",
        decimal=",",
    )
    indicadores = pd.read_csv(
        RAIZ / "data" / "processed" / "indicadores_anuais.csv",
        sep=";",
        decimal=",",
    )
    exigir(len(fato) == 115, f"Esperados 115 registros; encontrados {len(fato)}")
    exigir(not fato.duplicated(["Ano", "Metrica"]).any(), "Chave Ano + Métrica duplicada")
    exigir(fato["Valor_R$_milhoes"].notna().all(), "Há valores ausentes")
    exigir(indicadores["Ano"].astype(int).tolist() == [2021, 2022, 2023, 2024, 2025], "Períodos inesperados")
    diferenca = (indicadores["Ativo_Total"] - indicadores["Passivo_Total"]).abs().max()
    exigir(diferenca <= 0.001, f"Balanço não fecha: {diferenca}")
    resultados["dados"] = {
        "registros": len(fato),
        "anos": indicadores["Ano"].astype(int).tolist(),
        "duplicidades": 0,
        "ausentes": 0,
        "max_diferenca_balanco_milhoes": float(diferenca),
    }

    arquivos_json = list((RAIZ / "powerbi").rglob("*.json"))
    for arquivo in arquivos_json:
        json.loads(arquivo.read_text(encoding="utf-8"))
    resultados["json"] = {"arquivos_validos": len(arquivos_json)}

    tmdl = "\n".join(
        arquivo.read_text(encoding="utf-8")
        for arquivo in (RAIZ / "powerbi").rglob("*.tmdl")
    )
    tags = re.findall(r"lineageTag:\s*([^\s]+)", tmdl)
    exigir(tags, "Nenhum lineageTag encontrado")
    for tag in tags:
        uuid.UUID(tag)
    exigir(tmdl.count("```") % 2 == 0, "Blocos TMDL com crases desbalanceadas")

    medidas = set(re.findall(r"\bmeasure\s+'([^']+)'\s*=", tmdl))
    colunas = set(re.findall(r"\bcolumn\s+([A-Za-z_][A-Za-z0-9_]*)", tmdl))
    referencias_medidas: set[str] = set()
    referencias_colunas: set[str] = set()
    visuais = list((RAIZ / "powerbi").rglob("visual.json"))
    for arquivo in visuais:
        conteudo = json.loads(arquivo.read_text(encoding="utf-8"))
        estados = conteudo.get("visual", {}).get("query", {}).get("queryState", {})
        for estado in estados.values():
            for projecao in estado.get("projections", []):
                campo = projecao.get("field", {})
                if "Measure" in campo:
                    referencias_medidas.add(campo["Measure"]["Property"])
                if "Column" in campo:
                    referencias_colunas.add(campo["Column"]["Property"])
    exigir(referencias_medidas <= medidas, f"Medidas ausentes: {referencias_medidas - medidas}")
    exigir(referencias_colunas <= colunas, f"Colunas ausentes: {referencias_colunas - colunas}")
    resultados["modelo"] = {
        "lineage_tags_uuid": len(tags),
        "medidas_dax": len(medidas),
        "visuais_pbir": len(visuais),
        "referencias_medidas_validas": len(referencias_medidas),
        "referencias_colunas_validas": len(referencias_colunas),
    }

    imagens = sorted((RAIZ / "docs" / "images").glob("*.png"))
    exigir(len(imagens) == 4, f"Esperadas 4 imagens; encontradas {len(imagens)}")
    dimensoes = {}
    for imagem in imagens:
        with Image.open(imagem) as arquivo:
            dimensoes[imagem.name] = list(arquivo.size)
            exigir(arquivo.size == (1920, 1080), f"Dimensão inesperada: {imagem.name} {arquivo.size}")
    resultados["imagens"] = dimensoes

    planilha = RAIZ / "data" / "analise-financeira-magazine-luiza.xlsx"
    exigir(planilha.exists() and planilha.stat().st_size > 0, "Planilha ausente")
    with zipfile.ZipFile(planilha) as arquivo:
        exigir(arquivo.testzip() is None, "Arquivo XLSX corrompido")
        exigir("xl/workbook.xml" in arquivo.namelist(), "Estrutura XLSX inesperada")
    resultados["planilha"] = {"arquivo_valido": True, "bytes": planilha.stat().st_size}

    pacote_pbip = RAIZ / "powerbi" / "Dashboard Financeiro Magazine Luiza - PBIP.zip"
    exigir(pacote_pbip.exists(), "Pacote PBIP ausente")
    with zipfile.ZipFile(pacote_pbip) as pacote:
        exigir(pacote.testzip() is None, "Pacote PBIP corrompido")
        nomes = set(pacote.namelist())
        exigir("Dashboard Financeiro Magazine Luiza.pbip" in nomes, "Atalho PBIP ausente no pacote")
        exigir(any(nome.endswith("Report/definition.pbir") for nome in nomes), "Definição PBIR ausente no pacote")
        exigir(any(nome.endswith("SemanticModel/definition/tables/Medidas.tmdl") for nome in nomes), "Medidas TMDL ausentes no pacote")
    resultados["pacote_pbip"] = {"arquivo_valido": True, "arquivos": len(nomes), "bytes": pacote_pbip.stat().st_size}

    markdowns = [RAIZ / "README.md", *sorted((RAIZ / "docs").glob("*.md")), RAIZ / "powerbi" / "README.md"]
    links_locais: list[str] = []
    for markdown in markdowns:
        conteudo = markdown.read_text(encoding="utf-8")
        for destino in re.findall(r"\[[^\]]+\]\(([^)]+)\)", conteudo):
            destino = destino.strip("<>")
            if destino.startswith(("http://", "https://", "mailto:", "#")):
                continue
            caminho = unquote(destino.split("#", 1)[0])
            alvo = (markdown.parent / caminho).resolve()
            exigir(alvo.exists(), f"Link local quebrado em {markdown.name}: {destino}")
            links_locais.append(str(alvo.relative_to(RAIZ)))
    candidatos_logo = [
        caminho
        for caminho in RAIZ.rglob("*logo*")
        if not {".git", "node_modules", "raw", "workbook-preview"}.intersection(caminho.parts)
    ]
    exigir(not candidatos_logo, "O projeto não deve distribuir logotipos da companhia")
    resultados["documentacao"] = {
        "arquivos_markdown_revisados": len(markdowns),
        "links_locais_validos": len(links_locais),
        "logotipos_distribuidos": 0,
    }

    relatorio = RAIZ / "docs" / "validation-summary.json"
    relatorio.write_text(json.dumps(resultados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(resultados, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
