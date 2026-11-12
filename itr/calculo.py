"""Apuracao do ITR: imunidade, isencao, grau de utilizacao e imposto devido."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .modelo import ImovelRural
from .tabela import IMPOSTO_MINIMO, aliquota

CENTAVOS = Decimal("0.01")
HECTARE = Decimal("0.1")


def _dinheiro(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Apuracao:
    """Resultado da apuracao de um imovel em um exercicio."""

    nirf: str
    exercicio: int
    nome: str
    municipio: str
    area_total: Decimal
    area_tributavel: Decimal
    area_aproveitavel: Decimal
    area_utilizada: Decimal
    grau_utilizacao: Decimal  # em %
    vtn: Decimal
    vtn_tributavel: Decimal
    aliquota: Decimal  # em %
    imposto_devido: Decimal
    dispensado: bool = False
    motivo_dispensa: str | None = None
    alertas: tuple[str, ...] = ()

    @property
    def identificacao(self) -> str:
        rotulo = self.nome or f"NIRF {self.nirf}"
        return f"{rotulo} ({self.exercicio})"

    def resumo(self) -> str:
        if self.dispensado:
            return f"{self.identificacao}: sem imposto - {self.motivo_dispensa}"
        return (
            f"{self.identificacao}: GU {self.grau_utilizacao}% | "
            f"aliquota {self.aliquota}% | VTN tributavel R$ {self.vtn_tributavel} | "
            f"imposto R$ {self.imposto_devido}"
        )


def verificar_dispensa(imovel: ImovelRural) -> str | None:
    """Retorna o motivo da imunidade/isencao, ou None se houver imposto a apurar.

    Imunidade (art. 2): pequena gleba explorada pelo proprietario so ou com a
    familia, que nao possua outro imovel.
    Isencao (art. 3): imovel de assentamento que atenda aos requisitos legais.

    A verificacao depende de fatos declarados pelo contribuinte - o codigo apenas
    aplica as condicoes informadas, nao as comprova.
    """
    if imovel.imovel_de_assentamento:
        return "Isento: imovel de programa oficial de reforma agraria (art. 3, I)."

    e_pequena_gleba = imovel.area_total <= imovel.limite_pequena_gleba
    if (
        e_pequena_gleba
        and imovel.explora_so_ou_com_familia
        and not imovel.possui_outro_imovel_rural
    ):
        return (
            f"Imune: pequena gleba rural (<= {imovel.limite_pequena_gleba} ha na "
            f"regiao {imovel.regiao.value}) explorada pelo proprietario (art. 2)."
        )

    return None


def calcular_grau_utilizacao(imovel: ImovelRural) -> tuple[Decimal, tuple[str, ...]]:
    """GU = area utilizada / area aproveitavel * 100, limitado a 100%.

    Se a area aproveitavel for zero, nao ha o que utilizar: aplica-se a faixa mais
    favoravel (GU de 100%). CONFIRA esse tratamento contra a IN vigente - e o
    ponto da apuracao com mais divergencia de interpretacao.
    """
    alertas: list[str] = []
    utilizada = imovel.utilizadas.total

    if imovel.area_aproveitavel <= 0:
        alertas.append(
            "Area aproveitavel igual a zero: GU fixado em 100%. Confira o "
            "enquadramento antes de transmitir."
        )
        return Decimal("100"), tuple(alertas)

    if utilizada > imovel.area_aproveitavel:
        alertas.append(
            f"Area utilizada ({utilizada} ha) maior que a aproveitavel "
            f"({imovel.area_aproveitavel} ha): GU limitado a 100%. Revise as areas."
        )
        return Decimal("100"), tuple(alertas)

    gu = utilizada / imovel.area_aproveitavel * Decimal("100")
    return gu.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP), tuple(alertas)


def apurar(imovel: ImovelRural) -> Apuracao:
    """Apura o ITR devido para um imovel."""
    gu, alertas = calcular_grau_utilizacao(imovel)
    alertas_lista = list(alertas)

    motivo = verificar_dispensa(imovel)
    if motivo is not None:
        return Apuracao(
            nirf=imovel.nirf,
            exercicio=imovel.exercicio,
            nome=imovel.nome,
            municipio=imovel.municipio,
            area_total=imovel.area_total,
            area_tributavel=imovel.area_tributavel,
            area_aproveitavel=imovel.area_aproveitavel,
            area_utilizada=imovel.utilizadas.total,
            grau_utilizacao=gu,
            vtn=imovel.vtn,
            vtn_tributavel=Decimal("0.00"),
            aliquota=Decimal("0"),
            imposto_devido=Decimal("0.00"),
            dispensado=True,
            motivo_dispensa=motivo,
            alertas=tuple(alertas_lista),
        )

    aliq = aliquota(imovel.area_total, gu)
    vtn_tributavel = _dinheiro(imovel.vtn * (imovel.area_tributavel / imovel.area_total))
    imposto = _dinheiro(vtn_tributavel * aliq / Decimal("100"))

    if imposto < IMPOSTO_MINIMO:
        alertas_lista.append(
            f"Imposto apurado (R$ {imposto}) abaixo do minimo legal: "
            f"ajustado para R$ {IMPOSTO_MINIMO}."
        )
        imposto = IMPOSTO_MINIMO

    return Apuracao(
        nirf=imovel.nirf,
        exercicio=imovel.exercicio,
        nome=imovel.nome,
        municipio=imovel.municipio,
        area_total=imovel.area_total,
        area_tributavel=imovel.area_tributavel,
        area_aproveitavel=imovel.area_aproveitavel,
        area_utilizada=imovel.utilizadas.total,
        grau_utilizacao=gu,
        vtn=imovel.vtn,
        vtn_tributavel=vtn_tributavel,
        aliquota=aliq,
        imposto_devido=imposto,
        alertas=tuple(alertas_lista),
    )
