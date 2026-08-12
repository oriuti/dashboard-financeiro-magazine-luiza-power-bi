"""Empacota o projeto Power BI completo em um ZIP para distribuição no GitHub."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
PASTA_POWERBI = RAIZ / "powerbi"
NOME = "Dashboard Financeiro Magazine Luiza"
DESTINO = PASTA_POWERBI / f"{NOME} - PBIP.zip"


def main() -> int:
    entradas = [
        PASTA_POWERBI / f"{NOME}.pbip",
        PASTA_POWERBI / f"{NOME}.Report",
        PASTA_POWERBI / f"{NOME}.SemanticModel",
    ]
    ausentes = [str(caminho) for caminho in entradas if not caminho.exists()]
    if ausentes:
        raise FileNotFoundError(
            "Execute scripts/gerar_pbip.py antes de empacotar. Ausentes: " + ", ".join(ausentes)
        )

    arquivos: list[Path] = []
    for entrada in entradas:
        arquivos.extend([entrada] if entrada.is_file() else sorted(entrada.rglob("*")))

    with zipfile.ZipFile(DESTINO, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as pacote:
        for arquivo in arquivos:
            if not arquivo.is_file():
                continue
            caminho_relativo = arquivo.relative_to(PASTA_POWERBI)
            info = zipfile.ZipInfo.from_file(arquivo, arcname=str(caminho_relativo).replace("\\", "/"))
            info.date_time = (2026, 8, 11, 12, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            pacote.writestr(info, arquivo.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    print(f"{DESTINO} ({DESTINO.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
