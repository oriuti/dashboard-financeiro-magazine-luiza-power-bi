"""Gera prévias visuais do dashboard com os mesmos dados do modelo Power BI."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.patches import FancyBboxPatch


RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "data" / "processed" / "indicadores_anuais.csv"
SAIDA = RAIZ / "docs" / "images"

CORES = {
    "fundo": "#F4F7FB",
    "card": "#FFFFFF",
    "texto": "#0F172A",
    "subtexto": "#64748B",
    "borda": "#E2E8F0",
    "verde": "#0F766E",
    "azul": "#2563EB",
    "ambar": "#F59E0B",
    "roxo": "#7C3AED",
    "vermelho": "#DC2626",
    "cinza": "#94A3B8",
}


def dinheiro(valor: float) -> str:
    sinal = "-" if valor < 0 else ""
    absoluto = abs(valor)
    if absoluto >= 1000:
        numero = f"{absoluto / 1000:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{sinal}R$ {numero} bi"
    numero = f"{absoluto:,.0f}".replace(",", ".")
    return f"{sinal}R$ {numero} mi"


def percentual(valor: float) -> str:
    return f"{valor * 100:.1f}%".replace(".", ",")


def variacao(atual: float, anterior: float) -> float:
    return atual / anterior - 1 if anterior else np.nan


def preparar_figura(titulo: str, subtitulo: str) -> plt.Figure:
    fig = plt.figure(figsize=(16, 9), dpi=120, facecolor=CORES["fundo"])
    fig.text(0.035, 0.945, titulo, fontsize=25, fontweight="bold", color=CORES["texto"], va="top")
    fig.text(0.035, 0.902, subtitulo, fontsize=10.5, color=CORES["subtexto"], va="top")
    fig.text(
        0.965,
        0.935,
        "DFP consolidada  •  2021–2025  •  R$ milhões",
        fontsize=9.5,
        color=CORES["verde"],
        ha="right",
        va="top",
        bbox=dict(boxstyle="round,pad=0.55", facecolor="#E6F4F1", edgecolor="none"),
    )
    fig.text(
        0.035,
        0.022,
        "Fonte: Portal de Dados Abertos da CVM (DFP)  |  Estudo independente para portfólio  |  Não constitui recomendação de investimento",
        fontsize=8.2,
        color=CORES["subtexto"],
        va="bottom",
    )
    fig.text(0.965, 0.022, "Gabriel Oriuti Ferraz", fontsize=8.2, color=CORES["subtexto"], ha="right", va="bottom")
    return fig


def card(fig: plt.Figure, x: float, titulo: str, valor: str, detalhe: str, cor: str) -> None:
    y, w, h = 0.74, 0.22, 0.125
    caixa = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.008,rounding_size=0.012",
        transform=fig.transFigure,
        facecolor=CORES["card"],
        edgecolor=CORES["borda"],
        linewidth=1,
    )
    fig.patches.append(caixa)
    fig.patches.append(
        FancyBboxPatch(
            (x + 0.012, y + 0.025),
            0.006,
            h - 0.05,
            boxstyle="round,pad=0,rounding_size=0.003",
            transform=fig.transFigure,
            facecolor=cor,
            edgecolor=cor,
        )
    )
    fig.text(x + 0.03, y + 0.091, titulo.upper(), fontsize=8.5, color=CORES["subtexto"], fontweight="bold")
    fig.text(x + 0.03, y + 0.052, valor, fontsize=20, color=CORES["texto"], fontweight="bold")
    fig.text(x + 0.03, y + 0.018, detalhe, fontsize=8.5, color=cor)


def painel(fig: plt.Figure, pos: list[float], titulo: str) -> plt.Axes:
    ax = fig.add_axes(pos, facecolor=CORES["card"])
    for lado in ax.spines.values():
        lado.set_visible(False)
    ax.set_title(titulo, loc="left", fontsize=11.5, color=CORES["texto"], fontweight="bold", pad=16)
    ax.tick_params(colors=CORES["subtexto"], labelsize=8.5, length=0)
    ax.grid(axis="y", color=CORES["borda"], linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    return ax


def eixo_bilhoes(ax: plt.Axes) -> None:
    ax.yaxis.set_major_formatter(
        lambda v, _: f"{v / 1000:.1f} bi".replace(".", ",")
    )


def salvar(fig: plt.Figure, nome: str) -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA / nome, facecolor=fig.get_facecolor(), bbox_inches=None)
    plt.close(fig)


def pagina_executiva(df: pd.DataFrame) -> None:
    atual, anterior = df.iloc[-1], df.iloc[-2]
    fig = preparar_figura(
        "Análise Financeira — Magazine Luiza S.A.",
        "Visão executiva | evolução de resultado, rentabilidade, caixa e endividamento",
    )
    card(fig, 0.035, "Receita 2025", dinheiro(atual.Receita), f"{percentual(variacao(atual.Receita, anterior.Receita))} vs. 2024", CORES["verde"])
    card(fig, 0.275, "Resultado operacional", dinheiro(atual.Resultado_Operacional), f"{percentual(variacao(atual.Resultado_Operacional, anterior.Resultado_Operacional))} vs. 2024", CORES["azul"])
    card(fig, 0.515, "Lucro líquido", dinheiro(atual.Lucro_Liquido), f"{percentual(variacao(atual.Lucro_Liquido, anterior.Lucro_Liquido))} vs. 2024", CORES["ambar"])
    card(fig, 0.755, "Margem líquida", percentual(atual.Margem_Liquida), f"2024: {percentual(anterior.Margem_Liquida)}", CORES["roxo"])

    ax1 = painel(fig, [0.035, 0.12, 0.44, 0.55], "Receita e margem líquida")
    anos = df.Ano.astype(str)
    barras = ax1.bar(anos, df.Receita, color=CORES["verde"], width=0.58, label="Receita")
    eixo_bilhoes(ax1)
    ax1.set_ylim(0, df.Receita.max() * 1.25)
    ax1.bar_label(barras, labels=[f"{v / 1000:.1f} bi" for v in df.Receita], padding=4, fontsize=8, color=CORES["subtexto"])
    ax1b = ax1.twinx()
    ax1b.plot(anos, df.Margem_Liquida * 100, color=CORES["ambar"], marker="o", linewidth=2.4, label="Margem líquida")
    ax1b.axhline(0, color=CORES["cinza"], linewidth=0.8)
    ax1b.set_ylim(min(-4, df.Margem_Liquida.min() * 120), max(4, df.Margem_Liquida.max() * 150))
    ax1b.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax1b.tick_params(colors=CORES["ambar"], labelsize=8.5, length=0)
    for lado in ax1b.spines.values():
        lado.set_visible(False)
    ax1.legend(loc="upper left", frameon=False, fontsize=8.5)
    ax1b.legend(loc="upper right", frameon=False, fontsize=8.5)

    ax2 = painel(fig, [0.515, 0.12, 0.45, 0.55], "Caixa, dívida líquida e principais sinais")
    ax2.plot(anos, df.Caixa, color=CORES["azul"], marker="o", linewidth=2.5, label="Caixa")
    ax2.plot(anos, df.Divida_Liquida, color=CORES["vermelho"], marker="o", linewidth=2.5, label="Dívida líquida")
    eixo_bilhoes(ax2)
    ax2.legend(loc="upper left", frameon=False, fontsize=8.5, ncol=2)
    sinais = [
        f"Receita avançou {percentual(variacao(atual.Receita, anterior.Receita))} em 2025.",
        f"Margem operacional chegou a {percentual(atual.Margem_Operacional)}.",
        f"Lucro líquido recuou {percentual(abs(variacao(atual.Lucro_Liquido, anterior.Lucro_Liquido)))} no ano.",
        f"Liquidez corrente encerrou em {atual.Liquidez_Corrente:.2f}x.",
    ]
    ax2.text(0.03, 0.05, "\n".join(f"• {s}" for s in sinais), transform=ax2.transAxes, fontsize=9, color=CORES["texto"], linespacing=1.7, va="bottom", bbox=dict(boxstyle="round,pad=0.7", facecolor="#F8FAFC", edgecolor=CORES["borda"]))
    salvar(fig, "01-visao-executiva.png")


def pagina_dre(df: pd.DataFrame) -> None:
    atual, anterior = df.iloc[-1], df.iloc[-2]
    fig = preparar_figura("DRE e Margens", "Crescimento, lucro bruto e recuperação do resultado operacional")
    card(fig, 0.035, "Receita", dinheiro(atual.Receita), f"{percentual(variacao(atual.Receita, anterior.Receita))} vs. 2024", CORES["verde"])
    card(fig, 0.275, "Lucro bruto", dinheiro(atual.Lucro_Bruto), f"Margem: {percentual(atual.Margem_Bruta)}", CORES["azul"])
    card(fig, 0.515, "Resultado operacional", dinheiro(atual.Resultado_Operacional), f"Margem: {percentual(atual.Margem_Operacional)}", CORES["ambar"])
    card(fig, 0.755, "Lucro líquido", dinheiro(atual.Lucro_Liquido), f"Margem: {percentual(atual.Margem_Liquida)}", CORES["roxo"])

    ax1 = painel(fig, [0.035, 0.12, 0.44, 0.55], "Receita e lucro bruto")
    x = np.arange(len(df))
    largura = 0.34
    ax1.bar(x - largura / 2, df.Receita, largura, color=CORES["verde"], label="Receita")
    ax1.bar(x + largura / 2, df.Lucro_Bruto, largura, color=CORES["azul"], label="Lucro bruto")
    ax1.set_xticks(x, df.Ano.astype(str))
    eixo_bilhoes(ax1)
    ax1.legend(frameon=False, fontsize=8.5, ncol=2)

    ax2 = painel(fig, [0.515, 0.12, 0.45, 0.55], "Evolução das margens")
    for coluna, rotulo, cor in [
        ("Margem_Bruta", "Bruta", CORES["verde"]),
        ("Margem_Operacional", "Operacional", CORES["azul"]),
        ("Margem_Liquida", "Líquida", CORES["ambar"]),
    ]:
        ax2.plot(df.Ano.astype(str), df[coluna] * 100, marker="o", linewidth=2.4, label=rotulo, color=cor)
    ax2.axhline(0, color=CORES["cinza"], linewidth=0.9)
    ax2.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax2.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper left")
    ax2.text(0.03, 0.05, f"A margem operacional avançou de {percentual(anterior.Margem_Operacional)} para {percentual(atual.Margem_Operacional)},\nmas a margem líquida recuou para {percentual(atual.Margem_Liquida)}.", transform=ax2.transAxes, fontsize=9, color=CORES["texto"], va="bottom", bbox=dict(boxstyle="round,pad=0.7", facecolor="#F8FAFC", edgecolor=CORES["borda"]))
    salvar(fig, "02-dre-e-margens.png")


def pagina_fluxo(df: pd.DataFrame) -> None:
    atual, anterior = df.iloc[-1], df.iloc[-2]
    fig = preparar_figura("Fluxo de Caixa", "Geração operacional, investimentos, financiamentos e fluxo de caixa livre")
    card(fig, 0.035, "FCO", dinheiro(atual.FCO), f"2024: {dinheiro(anterior.FCO)}", CORES["verde"])
    card(fig, 0.275, "Fluxo de caixa livre", dinheiro(atual.Fluxo_Caixa_Livre), f"FCO + capex", CORES["azul"])
    card(fig, 0.515, "Capex", dinheiro(atual.Capex), f"{percentual(variacao(abs(atual.Capex), abs(anterior.Capex)))} vs. 2024", CORES["ambar"])
    card(fig, 0.755, "Caixa final", dinheiro(atual.Caixa), f"{percentual(variacao(atual.Caixa, anterior.Caixa))} vs. 2024", CORES["roxo"])

    ax1 = painel(fig, [0.035, 0.12, 0.44, 0.55], "Fluxos por atividade")
    x = np.arange(len(df))
    largura = 0.24
    ax1.bar(x - largura, df.FCO, largura, color=CORES["verde"], label="Operacional")
    ax1.bar(x, df.FCI, largura, color=CORES["azul"], label="Investimento")
    ax1.bar(x + largura, df.FCF, largura, color=CORES["roxo"], label="Financiamento")
    ax1.axhline(0, color=CORES["cinza"], linewidth=0.8)
    ax1.set_xticks(x, df.Ano.astype(str))
    eixo_bilhoes(ax1)
    ax1.legend(frameon=False, fontsize=8.5, ncol=3)

    ax2 = painel(fig, [0.515, 0.12, 0.45, 0.55], "Fluxo de caixa livre e capex")
    cores = [CORES["vermelho"] if v < 0 else CORES["verde"] for v in df.Fluxo_Caixa_Livre]
    ax2.bar(df.Ano.astype(str), df.Fluxo_Caixa_Livre, color=cores, width=0.55, label="Fluxo de caixa livre")
    ax2.plot(df.Ano.astype(str), df.Capex, color=CORES["ambar"], marker="o", linewidth=2.4, label="Capex")
    ax2.axhline(0, color=CORES["cinza"], linewidth=0.8)
    eixo_bilhoes(ax2)
    ax2.legend(
        handles=[
            Line2D([0], [0], color=CORES["ambar"], marker="o", linewidth=2.4, label="Capex"),
            Patch(facecolor=CORES["verde"], label="FCL positivo"),
            Patch(facecolor=CORES["vermelho"], label="FCL negativo"),
        ],
        frameon=False,
        fontsize=8.5,
        ncol=3,
    )
    ax2.text(0.03, 0.05, "A DFC reportada mostra forte geração operacional em 2024–2025.\nO detalhamento das variações de capital de giro deve acompanhar a leitura do indicador.", transform=ax2.transAxes, fontsize=9, color=CORES["texto"], va="bottom", bbox=dict(boxstyle="round,pad=0.7", facecolor="#F8FAFC", edgecolor=CORES["borda"]))
    salvar(fig, "03-fluxo-de-caixa.png")


def pagina_balanco(df: pd.DataFrame) -> None:
    atual, anterior = df.iloc[-1], df.iloc[-2]
    fig = preparar_figura("Balanço e Liquidez", "Capital de giro, composição do ativo circulante e endividamento")
    card(fig, 0.035, "Liquidez corrente", f"{atual.Liquidez_Corrente:.2f}x", f"2024: {anterior.Liquidez_Corrente:.2f}x", CORES["verde"])
    card(fig, 0.275, "Dívida líquida", dinheiro(atual.Divida_Liquida), f"{percentual(variacao(atual.Divida_Liquida, anterior.Divida_Liquida))} vs. 2024", CORES["vermelho"])
    card(fig, 0.515, "Estoques", dinheiro(atual.Estoques), f"{percentual(variacao(atual.Estoques, anterior.Estoques))} vs. 2024", CORES["ambar"])
    card(fig, 0.755, "Patrimônio líquido", dinheiro(atual.Patrimonio_Liquido), f"ROE: {percentual(atual.ROE)}", CORES["roxo"])

    ax1 = painel(fig, [0.035, 0.12, 0.44, 0.55], "Ativo e passivo circulantes")
    ax1.plot(df.Ano.astype(str), df.Ativo_Circulante, marker="o", linewidth=2.5, color=CORES["verde"], label="Ativo circulante")
    ax1.plot(df.Ano.astype(str), df.Passivo_Circulante, marker="o", linewidth=2.5, color=CORES["vermelho"], label="Passivo circulante")
    eixo_bilhoes(ax1)
    ax1.legend(frameon=False, fontsize=8.5, ncol=2)

    ax2 = painel(fig, [0.515, 0.12, 0.45, 0.55], "Caixa, contas a receber e estoques")
    x = np.arange(len(df))
    largura = 0.24
    ax2.bar(x - largura, df.Caixa, largura, color=CORES["azul"], label="Caixa")
    ax2.bar(x, df.Contas_a_Receber, largura, color=CORES["verde"], label="Contas a receber")
    ax2.bar(x + largura, df.Estoques, largura, color=CORES["ambar"], label="Estoques")
    ax2.set_xticks(x, df.Ano.astype(str))
    eixo_bilhoes(ax2)
    ax2.legend(frameon=False, fontsize=8.5, ncol=3)
    ax2.text(0.03, 0.05, f"Em 2025, estoques representaram {percentual(atual.Estoques / atual.Ativo_Circulante)} do ativo circulante.\nA dívida líquida aumentou enquanto o caixa recuou.", transform=ax2.transAxes, fontsize=9, color=CORES["texto"], va="bottom", bbox=dict(boxstyle="round,pad=0.7", facecolor="#F8FAFC", edgecolor=CORES["borda"]))
    salvar(fig, "04-balanco-e-liquidez.png")


def main() -> int:
    df = pd.read_csv(DADOS, sep=";", decimal=",")
    pagina_executiva(df)
    pagina_dre(df)
    pagina_fluxo(df)
    pagina_balanco(df)
    print("\n".join(str(p) for p in sorted(SAIDA.glob("*.png"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
