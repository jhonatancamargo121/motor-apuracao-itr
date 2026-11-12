"""Modelo de dados do imovel rural para apuracao do ITR (Lei 9.393/96)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class Regiao(str, Enum):
    """Regiao do municipio, define o limite de pequena gleba (art. 2, par. unico)."""

    AMAZONIA_OCIDENTAL_PANTANAL = "amazonia_ocidental_pantanal"  # 100 ha
    POLIGONO_SECAS_AMAZONIA_ORIENTAL = "poligono_secas_amazonia_oriental"  # 50 ha
    DEMAIS = "demais"  # 30 ha


LIMITE_PEQUENA_GLEBA: dict[Regiao, Decimal] = {
    Regiao.AMAZONIA_OCIDENTAL_PANTANAL: Decimal("100"),
    Regiao.POLIGONO_SECAS_AMAZONIA_ORIENTAL: Decimal("50"),
    Regiao.DEMAIS: Decimal("30"),
}


def _d(valor: Decimal | str | int | float) -> Decimal:
    """Converte para Decimal sem passar por float binario."""
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))


@dataclass
class AreasNaoTributaveis:
    """Areas excluidas da area tributavel (art. 10, par. 1, II)."""

    preservacao_permanente: Decimal = Decimal("0")
    reserva_legal: Decimal = Decimal("0")
    rppn: Decimal = Decimal("0")
    interesse_ecologico: Decimal = Decimal("0")
    servidao_ambiental: Decimal = Decimal("0")
    coberta_floresta_nativa: Decimal = Decimal("0")
    alagada_reservatorio: Decimal = Decimal("0")
    comprovadamente_imprestavel: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        for campo in self.__dataclass_fields__:
            setattr(self, campo, _d(getattr(self, campo)))

    @property
    def total(self) -> Decimal:
        return sum(
            (getattr(self, campo) for campo in self.__dataclass_fields__),
            Decimal("0"),
        )


@dataclass
class AreasUtilizadas:
    """Areas utilizadas na atividade rural.

    Espelha os campos 12 a 18 da ficha "Utilizacao do Imovel" do PGD ITR.
    A soma corresponde ao campo 19 (AREA UTILIZADA NA ATIVIDADE RURAL).
    """

    produtos_vegetais: Decimal = Decimal("0")  # campo 12
    descanso: Decimal = Decimal("0")  # campo 13
    reflorestamento: Decimal = Decimal("0")  # campo 14
    pastagens: Decimal = Decimal("0")  # campo 15
    exploracao_extrativa: Decimal = Decimal("0")  # campo 16
    atividade_granjeira_aquicola: Decimal = Decimal("0")  # campo 17
    frustracao_safra: Decimal = Decimal("0")  # campo 18

    def __post_init__(self) -> None:
        for campo in self.__dataclass_fields__:
            setattr(self, campo, _d(getattr(self, campo)))

    @property
    def total(self) -> Decimal:
        return sum(
            (getattr(self, campo) for campo in self.__dataclass_fields__),
            Decimal("0"),
        )


@dataclass
class ImovelRural:
    """Dados de um imovel rural para um exercicio."""

    nirf: str
    exercicio: int
    area_total: Decimal
    # VTN pode ser informado direto ou derivado dos campos 01/02/03 da ficha
    # "Calculo do Imposto" do PGD, via ImovelRural.com_valores().
    vtn: Decimal
    regiao: Regiao = Regiao.DEMAIS
    nao_tributaveis: AreasNaoTributaveis = field(default_factory=AreasNaoTributaveis)
    utilizadas: AreasUtilizadas = field(default_factory=AreasUtilizadas)
    # Benfeitorias uteis/necessarias destinadas a atividade rural: saem da
    # area aproveitavel, mas continuam na area tributavel.
    area_benfeitorias: Decimal = Decimal("0")

    # Condicoes declaradas pelo contribuinte, usadas para imunidade/isencao.
    explora_so_ou_com_familia: bool = False
    possui_outro_imovel_rural: bool = True
    possui_imovel_urbano: bool = True
    imovel_de_assentamento: bool = False

    # Identificacao, so para relatorio e conferencia humana.
    nome: str = ""
    municipio: str = ""
    uf: str = ""

    def __post_init__(self) -> None:
        self.area_total = _d(self.area_total)
        self.vtn = _d(self.vtn)
        self.area_benfeitorias = _d(self.area_benfeitorias)
        self._validar()

    def _validar(self) -> None:
        if self.area_total <= 0:
            raise ValueError(f"NIRF {self.nirf}: area total deve ser positiva.")
        if self.vtn < 0:
            raise ValueError(f"NIRF {self.nirf}: VTN nao pode ser negativo.")

        soma_nt = self.nao_tributaveis.total
        if soma_nt > self.area_total:
            raise ValueError(
                f"NIRF {self.nirf}: areas nao tributaveis ({soma_nt} ha) "
                f"excedem a area total ({self.area_total} ha)."
            )
        if soma_nt + self.area_benfeitorias > self.area_total:
            raise ValueError(
                f"NIRF {self.nirf}: nao tributaveis + benfeitorias excedem a area total."
            )

    @classmethod
    def com_valores(
        cls,
        *,
        valor_total_imovel: Decimal | str,
        valor_construcoes_benfeitorias: Decimal | str = "0",
        valor_culturas_pastagens_florestas: Decimal | str = "0",
        **kwargs,
    ) -> "ImovelRural":
        """Cria o imovel derivando o VTN como o PGD faz na ficha Calculo do Imposto.

        campo 04 (VTN) = 01 valor total - 02 construcoes/benfeitorias
                            - 03 culturas/pastagens cultivadas/florestas plantadas
        """
        total = _d(valor_total_imovel)
        construcoes = _d(valor_construcoes_benfeitorias)
        culturas = _d(valor_culturas_pastagens_florestas)
        vtn = total - construcoes - culturas
        if vtn < 0:
            raise ValueError(
                f"VTN negativo: valor total (R$ {total}) menor que a soma de "
                f"construcoes (R$ {construcoes}) e culturas (R$ {culturas})."
            )
        return cls(vtn=vtn, **kwargs)

    @property
    def area_tributavel(self) -> Decimal:
        """Area total menos as areas nao tributaveis."""
        return self.area_total - self.nao_tributaveis.total

    @property
    def area_aproveitavel(self) -> Decimal:
        """Area tributavel menos benfeitorias. Nunca negativa."""
        return max(self.area_tributavel - self.area_benfeitorias, Decimal("0"))

    @property
    def limite_pequena_gleba(self) -> Decimal:
        return LIMITE_PEQUENA_GLEBA[self.regiao]
