"""Tabela de aliquotas do ITR - Anexo da Lei 9.393/96.

ATENCAO: confira estes valores contra o texto legal vigente antes de usar em
producao. A tabela nao muda ha anos, mas a conferencia e barata e o erro e caro.

Eixo 1 - area total do imovel (ha).
Eixo 2 - grau de utilizacao (GU, em %), em faixas decrescentes.
"""

from __future__ import annotations

from decimal import Decimal

# Limites superiores das faixas de GU, em ordem decrescente.
# Faixa 0: GU > 80 | 1: 65 < GU <= 80 | 2: 50 < GU <= 65
# Faixa 3: 30 < GU <= 50 | 4: GU <= 30
FAIXAS_GU: tuple[Decimal, ...] = (
    Decimal("80"),
    Decimal("65"),
    Decimal("50"),
    Decimal("30"),
)

# (limite superior da area em ha, aliquotas em % por faixa de GU)
TABELA_ALIQUOTAS: tuple[tuple[Decimal, tuple[str, ...]], ...] = (
    (Decimal("50"), ("0.03", "0.20", "0.40", "0.70", "1.00")),
    (Decimal("200"), ("0.07", "0.40", "0.80", "1.40", "2.00")),
    (Decimal("500"), ("0.10", "0.60", "1.30", "2.30", "3.30")),
    (Decimal("1000"), ("0.15", "0.85", "1.90", "3.30", "4.70")),
    (Decimal("Infinity"), ("0.45", "3.00", "6.40", "12.00", "20.00")),
)

# Imposto minimo devido por imovel (art. 11, par. 2).
IMPOSTO_MINIMO = Decimal("10.00")


def indice_faixa_gu(gu: Decimal) -> int:
    """Indice da faixa de GU (0 = mais utilizado, 4 = menos utilizado)."""
    for indice, limite in enumerate(FAIXAS_GU):
        if gu > limite:
            return indice
    return len(FAIXAS_GU)


def aliquota(area_total: Decimal, gu: Decimal) -> Decimal:
    """Aliquota em percentual (ex.: Decimal('0.40') significa 0,40%)."""
    if area_total <= 0:
        raise ValueError("Area total deve ser positiva para obter a aliquota.")

    faixa = indice_faixa_gu(gu)
    for limite, linha in TABELA_ALIQUOTAS:
        if area_total <= limite:
            return Decimal(linha[faixa])

    raise AssertionError("Tabela de aliquotas incompleta.")  # pragma: no cover
