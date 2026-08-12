"""Baixa os ZIPs anuais de DFP diretamente do Portal de Dados Abertos da CVM."""

from __future__ import annotations

import io
import sys
import urllib.request
import zipfile
from pathlib import Path


ANOS = range(2021, 2026)
URL_BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS"
RAIZ = Path(__file__).resolve().parents[1]
PASTA_RAW = RAIZ / "data" / "raw"


def main() -> int:
    PASTA_RAW.mkdir(parents=True, exist_ok=True)
    for ano in ANOS:
        nome = f"dfp_cia_aberta_{ano}.zip"
        destino = PASTA_RAW / nome
        if destino.exists() and destino.stat().st_size > 0:
            print(f"[cache] {nome}")
            continue

        url = f"{URL_BASE}/{nome}"
        print(f"[download] {url}")
        with urllib.request.urlopen(url, timeout=120) as resposta:
            conteudo = resposta.read()

        with zipfile.ZipFile(io.BytesIO(conteudo)) as arquivo:
            arquivo_invalido = arquivo.testzip()
            if arquivo_invalido:
                raise RuntimeError(f"ZIP inválido ({nome}): {arquivo_invalido}")

        destino.write_bytes(conteudo)
        print(f"[ok] {nome}: {len(conteudo) / 1_000_000:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
