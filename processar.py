"""Apura o ITR de uma planilha inteira e emite o relatorio de conferencia.

    python processar.py dados/modelo_imoveis.xlsx
    python processar.py dados/imoveis.xlsx --csv saida/apuracao_2026.csv

Codigo de saida: 0 = nada pendente | 1 = ha itens para revisao humana.
"""

from __future__ import annotations

import argparse
import sys

from itr.relatorio import exportar_csv, formatar, processar_planilha


def main() -> int:
    parser = argparse.ArgumentParser(description="Apuracao do ITR em lote.")
    parser.add_argument("planilha", help="Caminho da planilha .xlsx ou .csv")
    parser.add_argument("--csv", help="Exporta a apuracao para este CSV", default=None)
    args = parser.parse_args()

    try:
        lote = processar_planilha(args.planilha)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2

    print(formatar(lote))

    if args.csv:
        destino = exportar_csv(lote, args.csv)
        print(f"\nApuracao exportada para: {destino}")

    return 1 if lote.precisa_revisao else 0


if __name__ == "__main__":
    raise SystemExit(main())
