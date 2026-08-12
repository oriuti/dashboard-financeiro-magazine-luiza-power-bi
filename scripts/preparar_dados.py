"""Prepara a camada analítica anual da Magazine Luiza a partir das DFPs da CVM."""

from __future__ import annotations

import hashlib
import json
import sys
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd


ANOS = range(2021, 2026)
CNPJ = "47.960.950/0001-21"
EMPRESA = "MAGAZINE LUIZA S.A."
ORDEM_ATUAL = "\u00daLTIMO"
RAIZ = Path(__file__).resolve().parents[1]
PASTA_RAW = RAIZ / "data" / "raw"
PASTA_PROCESSADA = RAIZ / "data" / "processed"


@dataclass(frozen=True)
class Conta:
    metrica: str
    demonstracao: str
    codigo: str
    categoria: str
    rotulo: str


CONTAS = (
    Conta("Receita", "DRE", "3.01", "Resultado", "Receita líquida"),
    Conta("Custos", "DRE", "3.02", "Resultado", "Custos dos bens e serviços"),
    Conta("Lucro_Bruto", "DRE", "3.03", "Resultado", "Lucro bruto"),
    Conta("Despesas_Operacionais", "DRE", "3.04", "Resultado", "Despesas/receitas operacionais"),
    Conta("Resultado_Operacional", "DRE", "3.05", "Resultado", "Resultado operacional (antes do financeiro e tributos)"),
    Conta("Resultado_Financeiro", "DRE", "3.06", "Resultado", "Resultado financeiro"),
    Conta("Lucro_Liquido", "DRE", "3.11", "Resultado", "Lucro/prejuízo consolidado"),
    Conta("Ativo_Total", "BPA", "1", "Balanço", "Ativo total"),
    Conta("Ativo_Circulante", "BPA", "1.01", "Balanço", "Ativo circulante"),
    Conta("Caixa", "BPA", "1.01.01", "Balanço", "Caixa e equivalentes"),
    Conta("Contas_a_Receber", "BPA", "1.01.03", "Balanço", "Contas a receber"),
    Conta("Estoques", "BPA", "1.01.04", "Balanço", "Estoques"),
    Conta("Passivo_Total", "BPP", "2", "Balanço", "Passivo total e patrimônio líquido"),
    Conta("Passivo_Circulante", "BPP", "2.01", "Balanço", "Passivo circulante"),
    Conta("Divida_CP", "BPP", "2.01.04", "Balanço", "Empréstimos e financiamentos de curto prazo"),
    Conta("Divida_LP", "BPP", "2.02.01", "Balanço", "Empréstimos e financiamentos de longo prazo"),
    Conta("Patrimonio_Liquido", "BPP", "2.03", "Balanço", "Patrimônio líquido consolidado"),
    Conta("FCO", "DFC_MI", "6.01", "Fluxo de caixa", "Fluxo de caixa operacional"),
    Conta("FCI", "DFC_MI", "6.02", "Fluxo de caixa", "Fluxo de caixa de investimento"),
    Conta("FCF", "DFC_MI", "6.03", "Fluxo de caixa", "Fluxo de caixa de financiamento"),
    Conta("Variacao_Caixa", "DFC_MI", "6.05", "Fluxo de caixa", "Variação de caixa"),
    Conta("Capex_Imobilizado", "DFC_MI", "6.02.01", "Fluxo de caixa", "Aquisição de imobilizado"),
    Conta("Capex_Intangivel", "DFC_MI", "6.02.02", "Fluxo de caixa", "Aquisição de intangível"),
)

ARQUIVOS = {
    "DRE": "DRE_con",
    "BPA": "BPA_con",
    "BPP": "BPP_con",
    "DFC_MI": "DFC_MI_con",
}


def sem_acento(texto: str) -> str:
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )


def sha256(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def ler_csv_do_zip(arquivo_zip: Path, identificador: str) -> pd.DataFrame:
    with zipfile.ZipFile(arquivo_zip) as arquivo:
        candidatos = [
            nome
            for nome in arquivo.namelist()
            if identificador in nome and nome.lower().endswith(".csv")
        ]
        if len(candidatos) != 1:
            raise RuntimeError(
                f"Esperado 1 CSV com '{identificador}' em {arquivo_zip.name}; encontrados {candidatos}"
            )
        with arquivo.open(candidatos[0]) as fluxo:
            return pd.read_csv(
                fluxo,
                sep=";",
                encoding="latin1",
                dtype={"VL_CONTA": "string", "CD_CONTA": "string"},
                low_memory=False,
            )


def filtrar_empresa_versao(df: pd.DataFrame, ano: int) -> tuple[pd.DataFrame, int]:
    base = df[
        (df["CNPJ_CIA"] == CNPJ)
        & (pd.to_datetime(df["DT_REFER"]).dt.year == ano)
    ].copy()
    if base.empty:
        raise RuntimeError(f"Empresa não encontrada para {ano}")

    denominacoes = {sem_acento(nome.upper()) for nome in base["DENOM_CIA"].dropna().unique()}
    if sem_acento(EMPRESA) not in denominacoes:
        raise RuntimeError(f"Denominação inesperada em {ano}: {denominacoes}")

    versao = int(base["VERSAO"].max())
    base = base[(base["VERSAO"] == versao) & (base["ORDEM_EXERC"] == ORDEM_ATUAL)].copy()
    if base.empty:
        raise RuntimeError(f"Não há linhas da ordem atual na versão {versao} de {ano}")

    escalas = set(base["ESCALA_MOEDA"].dropna().unique())
    moedas = set(base["MOEDA"].dropna().unique())
    if escalas != {"MIL"} or moedas != {"REAL"}:
        raise RuntimeError(f"Escala/moeda inesperada em {ano}: {escalas} / {moedas}")

    base["VL_CONTA"] = pd.to_numeric(
        base["VL_CONTA"].str.replace(",", ".", regex=False), errors="raise"
    )
    return base, versao


def main() -> int:
    PASTA_PROCESSADA.mkdir(parents=True, exist_ok=True)
    linhas: list[dict[str, object]] = []
    versoes: dict[str, int] = {}

    por_demonstracao: dict[str, list[Conta]] = {}
    for conta in CONTAS:
        por_demonstracao.setdefault(conta.demonstracao, []).append(conta)

    for ano in ANOS:
        arquivo_zip = PASTA_RAW / f"dfp_cia_aberta_{ano}.zip"
        if not arquivo_zip.exists():
            raise FileNotFoundError(
                f"Arquivo ausente: {arquivo_zip}. Execute scripts/download_dados_cvm.py."
            )

        for demonstracao, contas in por_demonstracao.items():
            df = ler_csv_do_zip(arquivo_zip, ARQUIVOS[demonstracao])
            base, versao = filtrar_empresa_versao(df, ano)
            versoes[f"{ano}_{demonstracao}"] = versao

            for conta in contas:
                encontrada = base[base["CD_CONTA"] == conta.codigo]
                if len(encontrada) != 1:
                    raise RuntimeError(
                        f"{ano} {demonstracao} {conta.codigo}: esperado 1 registro, encontrado {len(encontrada)}"
                    )
                registro = encontrada.iloc[0]
                linhas.append(
                    {
                        "Ano": ano,
                        "Data_Referencia": registro["DT_REFER"],
                        "Empresa": EMPRESA,
                        "CNPJ": CNPJ,
                        "Demonstracao": demonstracao,
                        "Categoria": conta.categoria,
                        "Metrica": conta.metrica,
                        "Rotulo": conta.rotulo,
                        "Codigo_Conta": conta.codigo,
                        "Descricao_CVM": registro["DS_CONTA"],
                        "Valor_R$_mil": float(registro["VL_CONTA"]),
                        "Valor_R$_milhoes": float(registro["VL_CONTA"]) / 1000.0,
                        "Moeda": registro["MOEDA"],
                        "Escala_Original": registro["ESCALA_MOEDA"],
                        "Versao_DFP": versao,
                        "Fonte": f"DFP {ano} - CVM",
                    }
                )

    fato = pd.DataFrame(linhas).sort_values(["Ano", "Demonstracao", "Codigo_Conta"])
    if fato.duplicated(["Ano", "Metrica"]).any():
        raise RuntimeError("Há duplicidade na chave Ano + Métrica")

    fato.to_csv(
        PASTA_PROCESSADA / "fato_metricas_financeiras.csv",
        sep=";",
        decimal=",",
        index=False,
        encoding="utf-8-sig",
    )

    wide = fato.pivot(index="Ano", columns="Metrica", values="Valor_R$_milhoes").reset_index()
    wide.columns.name = None
    wide["Capex"] = wide["Capex_Imobilizado"] + wide["Capex_Intangivel"]
    wide["Fluxo_Caixa_Livre"] = wide["FCO"] + wide["Capex"]
    wide["Divida_Bruta"] = wide["Divida_CP"] + wide["Divida_LP"]
    wide["Divida_Liquida"] = wide["Divida_Bruta"] - wide["Caixa"]
    wide["Margem_Bruta"] = wide["Lucro_Bruto"] / wide["Receita"]
    wide["Margem_Operacional"] = wide["Resultado_Operacional"] / wide["Receita"]
    wide["Margem_Liquida"] = wide["Lucro_Liquido"] / wide["Receita"]
    wide["Liquidez_Corrente"] = wide["Ativo_Circulante"] / wide["Passivo_Circulante"]
    wide["ROA"] = wide["Lucro_Liquido"] / wide["Ativo_Total"]
    wide["ROE"] = wide["Lucro_Liquido"] / wide["Patrimonio_Liquido"]
    wide["Crescimento_Receita"] = wide["Receita"].pct_change()
    wide["Crescimento_Lucro"] = wide["Lucro_Liquido"].pct_change()
    wide["Data_Referencia"] = pd.to_datetime(wide["Ano"].astype(str) + "-12-31")
    wide["Empresa"] = EMPRESA
    wide["CNPJ"] = CNPJ
    wide.to_csv(
        PASTA_PROCESSADA / "indicadores_anuais.csv",
        sep=";",
        decimal=",",
        index=False,
        encoding="utf-8-sig",
    )

    dicionario = pd.DataFrame(
        [
            {
                "Metrica": conta.metrica,
                "Rotulo": conta.rotulo,
                "Categoria": conta.categoria,
                "Demonstracao": conta.demonstracao,
                "Codigo_Conta_CVM": conta.codigo,
                "Unidade_Modelo": "R$ milhões",
                "Regra": "Valor CVM em R$ mil dividido por 1.000",
            }
            for conta in CONTAS
        ]
        + [
            {"Metrica": "Capex", "Rotulo": "Capex", "Categoria": "Calculado", "Demonstracao": "DFC_MI", "Codigo_Conta_CVM": "6.02.01 + 6.02.02", "Unidade_Modelo": "R$ milhões", "Regra": "Aquisição de imobilizado + aquisição de intangível"},
            {"Metrica": "Fluxo_Caixa_Livre", "Rotulo": "Fluxo de caixa livre", "Categoria": "Calculado", "Demonstracao": "DFC_MI", "Codigo_Conta_CVM": "6.01 + 6.02.01 + 6.02.02", "Unidade_Modelo": "R$ milhões", "Regra": "FCO + Capex (capex já vem com sinal negativo)"},
            {"Metrica": "Divida_Bruta", "Rotulo": "Dívida bruta", "Categoria": "Calculado", "Demonstracao": "BPP", "Codigo_Conta_CVM": "2.01.04 + 2.02.01", "Unidade_Modelo": "R$ milhões", "Regra": "Empréstimos e financiamentos CP + LP"},
            {"Metrica": "Divida_Liquida", "Rotulo": "Dívida líquida", "Categoria": "Calculado", "Demonstracao": "BPA/BPP", "Codigo_Conta_CVM": "2.01.04 + 2.02.01 - 1.01.01", "Unidade_Modelo": "R$ milhões", "Regra": "Dívida bruta - caixa"},
            {"Metrica": "Margem_Bruta", "Rotulo": "Margem bruta", "Categoria": "Calculado", "Demonstracao": "DRE", "Codigo_Conta_CVM": "3.03 / 3.01", "Unidade_Modelo": "%", "Regra": "Lucro bruto / receita"},
            {"Metrica": "Margem_Operacional", "Rotulo": "Margem operacional", "Categoria": "Calculado", "Demonstracao": "DRE", "Codigo_Conta_CVM": "3.05 / 3.01", "Unidade_Modelo": "%", "Regra": "Resultado operacional / receita"},
            {"Metrica": "Margem_Liquida", "Rotulo": "Margem líquida", "Categoria": "Calculado", "Demonstracao": "DRE", "Codigo_Conta_CVM": "3.11 / 3.01", "Unidade_Modelo": "%", "Regra": "Lucro líquido / receita"},
            {"Metrica": "Liquidez_Corrente", "Rotulo": "Liquidez corrente", "Categoria": "Calculado", "Demonstracao": "BPA/BPP", "Codigo_Conta_CVM": "1.01 / 2.01", "Unidade_Modelo": "x", "Regra": "Ativo circulante / passivo circulante"},
        ]
    )
    dicionario.to_csv(
        PASTA_PROCESSADA / "dicionario_metricas.csv",
        sep=";",
        index=False,
        encoding="utf-8-sig",
    )

    checks = {
        "periodos": len(wide),
        "anos": wide["Ano"].astype(int).tolist(),
        "chave_ano_metrica_unica": not fato.duplicated(["Ano", "Metrica"]).any(),
        "balanco_fecha_max_diferenca_milhoes": float(
            (wide["Ativo_Total"] - wide["Passivo_Total"]).abs().max()
        ),
        "valores_ausentes": int(fato["Valor_R$_milhoes"].isna().sum()),
        "moeda": "REAL",
        "escala_origem": "MIL",
        "escala_modelo": "R$ milhões",
    }
    if checks["balanco_fecha_max_diferenca_milhoes"] > 0.001:
        raise RuntimeError(f"Balanço não fecha: {checks}")
    if checks["valores_ausentes"] != 0:
        raise RuntimeError(f"Valores ausentes: {checks}")

    metadados = {
        "projeto": "Dashboard Financeiro Magazine Luiza",
        "empresa": EMPRESA,
        "cnpj": CNPJ,
        "fonte": "Portal de Dados Abertos da CVM - DFP",
        "url_dataset": "https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp",
        "data_acesso": date.today().isoformat(),
        "criterio": "Demonstrações consolidadas; ORDEM_EXERC=ÚLTIMO; maior VERSAO por ano",
        "versoes_dfp": versoes,
        "arquivos_origem": {
            str(ano): {
                "arquivo": f"dfp_cia_aberta_{ano}.zip",
                "sha256": sha256(PASTA_RAW / f"dfp_cia_aberta_{ano}.zip"),
            }
            for ano in ANOS
        },
        "checks": checks,
    }
    (PASTA_PROCESSADA / "metadados.json").write_text(
        json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
