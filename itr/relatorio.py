"""Relatorio de conferencia em lote: OK / com alertas / rejeitados."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .calculo import Apuracao, apurar
from .modelo import ImovelRural
from .planilha import LinhaRejeitada, ler_planilha


@dataclass
class Lote:
    ok: list[Apuracao]
    com_alertas: list[Apuracao]
    rejeitadas: list[LinhaRejeitada]

    @property
    def total_apurado(self) -> Decimal:
        return sum(
            (a.imposto_devido for a in self.ok + self.com_alertas), Decimal("0.00")
        )

    @property
    def dispensados(self) -> list[Apuracao]:
        return [a for a in self.ok + self.com_alertas if a.dispensado]

    @property
    def precisa_revisao(self) -> bool:
        return bool(self.com_alertas or self.rejeitadas)


def processar(imoveis: list[ImovelRural], rejeitadas: list[LinhaRejeitada]) -> Lote:
    ok: list[Apuracao] = []
    com_alertas: list[Apuracao] = []
    for imovel in imoveis:
        resultado = apurar(imovel)
        (com_alertas if resultado.alertas else ok).append(resultado)
    return Lote(ok=ok, com_alertas=com_alertas, rejeitadas=rejeitadas)


def processar_planilha(caminho: str | Path) -> Lote:
    imoveis, rejeitadas = ler_planilha(caminho)
    return processar(imoveis, rejeitadas)


def _linha_tabela(a: Apuracao) -> str:
    rotulo = f"{a.nirf:<14} {(a.nome or '')[:26]:<26}"
    if a.dispensado:
        return f"  {rotulo} {'DISPENSADO':>14}   {a.motivo_dispensa.split(':')[0]}"
    return (
        f"  {rotulo} {a.imposto_devido:>14,.2f}   "
        f"GU {a.grau_utilizacao:>7.2f}%  aliq {a.aliquota:>5.2f}%"
    )


def formatar(lote: Lote) -> str:
    """Relatorio em texto para conferencia humana."""
    linhas: list[str] = []
    add = linhas.append

    add("=" * 72)
    add("RELATORIO DE CONFERENCIA - ITR")
    add("=" * 72)

    total = len(lote.ok) + len(lote.com_alertas) + len(lote.rejeitadas)
    add(f"Imoveis na planilha : {total}")
    add(f"  OK                : {len(lote.ok)}")
    add(f"  Com alertas       : {len(lote.com_alertas)}  <- revisar antes de transmitir")
    add(f"  Rejeitados        : {len(lote.rejeitadas)}  <- corrigir na planilha")
    add(f"  Dispensados       : {len(lote.dispensados)}  (imunes/isentos)")
    add(f"Total de imposto    : R$ {lote.total_apurado:,.2f}")

    if lote.ok:
        add("")
        add("-" * 72)
        add("OK - sem ressalvas")
        add("-" * 72)
        for a in lote.ok:
            add(_linha_tabela(a))

    if lote.com_alertas:
        add("")
        add("-" * 72)
        add("COM ALERTAS - conferir cada um antes de transmitir")
        add("-" * 72)
        for a in lote.com_alertas:
            add(_linha_tabela(a))
            for alerta in a.alertas:
                add(f"      [!] {alerta}")

    if lote.rejeitadas:
        add("")
        add("-" * 72)
        add("REJEITADOS - nao foram apurados")
        add("-" * 72)
        for r in lote.rejeitadas:
            add(f"  linha {r.numero:<4} {r.identificacao:<20} {r.erro}")

    add("")
    add("=" * 72)
    if lote.precisa_revisao:
        add("ATENCAO: ha itens pendentes de revisao humana.")
    else:
        add("Nenhuma pendencia. Ainda assim, confira por amostragem.")
    add("Transmissao e pagamento continuam sendo passos manuais.")
    add("=" * 72)

    return "\n".join(linhas)


def exportar_csv(lote: Lote, caminho: str | Path) -> Path:
    """Exporta a apuracao para conferencia em planilha."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    with caminho.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(
            [
                "nirf", "nome", "municipio", "exercicio", "situacao", "area_total_ha", "area_tributavel_ha",
                "area_aproveitavel_ha", "area_utilizada_ha", "grau_utilizacao_pct",
                "vtn", "vtn_tributavel", "aliquota_pct", "imposto_devido", "alertas",
            ]
        )
        for a in lote.ok + lote.com_alertas:
            w.writerow(
                [
                    a.nirf, a.nome, a.municipio, a.exercicio,
                    "DISPENSADO" if a.dispensado else ("ALERTA" if a.alertas else "OK"),
                    a.area_total, a.area_tributavel, a.area_aproveitavel,
                    a.area_utilizada, a.grau_utilizacao, a.vtn, a.vtn_tributavel,
                    a.aliquota, a.imposto_devido, " | ".join(a.alertas),
                ]
            )
        for r in lote.rejeitadas:
            w.writerow([r.identificacao, "", "", "", "REJEITADO", "", "", "", "", "", "", "", "", "", r.erro])

    return caminho
