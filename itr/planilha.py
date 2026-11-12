"""Leitura da planilha de imoveis rurais -> ImovelRural.

Aceita .xlsx e .csv. Os cabecalhos sao normalizados (sem acento, minusculo,
underscore), entao "Area Total (ha)" e "area_total_ha" sao a mesma coluna.
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator

from .modelo import AreasNaoTributaveis, AreasUtilizadas, ImovelRural, Regiao

# Colunas obrigatorias na planilha.
OBRIGATORIAS = ("nirf", "nome_imovel", "exercicio", "area_total_ha")

# coluna da planilha -> campo de AreasNaoTributaveis
COLUNAS_NAO_TRIBUTAVEIS = {
    "preservacao_permanente": "preservacao_permanente",
    "reserva_legal": "reserva_legal",
    "rppn": "rppn",
    "interesse_ecologico": "interesse_ecologico",
    "servidao_ambiental": "servidao_ambiental",
    "floresta_nativa": "coberta_floresta_nativa",
    "alagada_reservatorio": "alagada_reservatorio",
    "imprestavel": "comprovadamente_imprestavel",
}

# coluna da planilha -> campo de AreasUtilizadas (campos 12 a 18 do PGD)
COLUNAS_UTILIZADAS = {
    "produtos_vegetais": "produtos_vegetais",
    "descanso": "descanso",
    "reflorestamento": "reflorestamento",
    "pastagem": "pastagens",
    "exploracao_extrativa": "exploracao_extrativa",
    "granjeira_aquicola": "atividade_granjeira_aquicola",
    "frustracao_safra": "frustracao_safra",
}

COLUNAS_BOOLEANAS = {
    "explora_com_familia": "explora_so_ou_com_familia",
    "possui_outro_imovel": "possui_outro_imovel_rural",
    "possui_imovel_urbano": "possui_imovel_urbano",
    "assentamento": "imovel_de_assentamento",
}

REGIOES = {
    "amazonia_ocidental_pantanal": Regiao.AMAZONIA_OCIDENTAL_PANTANAL,
    "poligono_secas_amazonia_oriental": Regiao.POLIGONO_SECAS_AMAZONIA_ORIENTAL,
    "demais": Regiao.DEMAIS,
}

# Todas as colunas que a planilha modelo traz, na ordem de exibicao.
COLUNAS_MODELO = (
    "nirf",
    "nome_imovel",
    "exercicio",
    "municipio",
    "uf",
    "regiao",
    "area_total_ha",
    *COLUNAS_NAO_TRIBUTAVEIS,
    "benfeitorias_ha",
    *COLUNAS_UTILIZADAS,
    "valor_total_imovel",
    "valor_construcoes",
    "valor_culturas",
    *COLUNAS_BOOLEANAS,
)


class ErroDeLinha(Exception):
    """Problema numa linha especifica da planilha."""


def normalizar(texto: Any) -> str:
    """'Área Total (ha)' -> 'area_total_ha'."""
    if texto is None:
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore")
    limpo = sem_acento.decode("ascii").lower().strip()
    return "_".join("".join(c if c.isalnum() else " " for c in limpo).split())


def ler_decimal(valor: Any, coluna: str) -> Decimal:
    """Aceita 1234.56, '1.234,56', '1234,56', vazio -> 0."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return Decimal("0")
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))

    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    # Formato brasileiro: ponto e milhar, virgula e decimal.
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation as e:
        raise ErroDeLinha(f"coluna '{coluna}': '{valor}' nao e um numero valido.") from e


def ler_booleano(valor: Any, coluna: str, padrao: bool) -> bool:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return padrao
    if isinstance(valor, bool):
        return valor
    texto = normalizar(valor)
    if texto in ("sim", "s", "1", "true", "verdadeiro", "x"):
        return True
    if texto in ("nao", "n", "0", "false", "falso"):
        return False
    raise ErroDeLinha(f"coluna '{coluna}': '{valor}' nao e SIM/NAO.")


@dataclass
class LinhaRejeitada:
    numero: int
    identificacao: str
    erro: str


def _linhas_xlsx(caminho: Path) -> Iterator[dict[str, Any]]:
    from openpyxl import load_workbook

    wb = load_workbook(caminho, data_only=True, read_only=True)
    ws = wb.active
    linhas = ws.iter_rows(values_only=True)
    try:
        cabecalho = [normalizar(c) for c in next(linhas)]
    except StopIteration:
        return
    for valores in linhas:
        if all(v is None or str(v).strip() == "" for v in valores):
            continue
        yield dict(zip(cabecalho, valores))
    wb.close()


def _linhas_csv(caminho: Path) -> Iterator[dict[str, Any]]:
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        amostra = f.read(4096)
        f.seek(0)
        try:
            dialeto = csv.Sniffer().sniff(amostra, delimiters=";,")
        except csv.Error:
            dialeto = csv.excel
        for bruta in csv.DictReader(f, dialect=dialeto):
            if all(not str(v or "").strip() for v in bruta.values()):
                continue
            yield {normalizar(k): v for k, v in bruta.items()}


def montar_imovel(linha: dict[str, Any]) -> ImovelRural:
    """Converte uma linha ja normalizada em ImovelRural."""
    faltando = [c for c in OBRIGATORIAS if not str(linha.get(c) or "").strip()]
    if faltando:
        raise ErroDeLinha(f"coluna(s) obrigatoria(s) vazia(s): {', '.join(faltando)}")

    regiao_txt = normalizar(linha.get("regiao")) or "demais"
    if regiao_txt not in REGIOES:
        raise ErroDeLinha(
            f"regiao '{linha.get('regiao')}' invalida. Use uma de: {', '.join(REGIOES)}."
        )

    nao_trib = AreasNaoTributaveis(
        **{
            campo: ler_decimal(linha.get(coluna), coluna)
            for coluna, campo in COLUNAS_NAO_TRIBUTAVEIS.items()
        }
    )
    utilizadas = AreasUtilizadas(
        **{
            campo: ler_decimal(linha.get(coluna), coluna)
            for coluna, campo in COLUNAS_UTILIZADAS.items()
        }
    )
    # Padrao conservador: assume que possui outros imoveis, para nunca
    # conceder imunidade por omissao de dado.
    padroes = {
        "explora_so_ou_com_familia": False,
        "possui_outro_imovel_rural": True,
        "possui_imovel_urbano": True,
        "imovel_de_assentamento": False,
    }
    booleanos = {
        campo: ler_booleano(linha.get(coluna), coluna, padroes[campo])
        for coluna, campo in COLUNAS_BOOLEANAS.items()
    }

    comuns = dict(
        nirf=str(linha["nirf"]).strip(),
        nome=str(linha.get("nome_imovel") or "").strip(),
        municipio=str(linha.get("municipio") or "").strip(),
        uf=str(linha.get("uf") or "").strip().upper(),
        exercicio=int(ler_decimal(linha["exercicio"], "exercicio")),
        area_total=ler_decimal(linha["area_total_ha"], "area_total_ha"),
        regiao=REGIOES[regiao_txt],
        nao_tributaveis=nao_trib,
        utilizadas=utilizadas,
        area_benfeitorias=ler_decimal(linha.get("benfeitorias_ha"), "benfeitorias_ha"),
        **booleanos,
    )

    return ImovelRural.com_valores(
        valor_total_imovel=ler_decimal(linha.get("valor_total_imovel"), "valor_total_imovel"),
        valor_construcoes_benfeitorias=ler_decimal(
            linha.get("valor_construcoes"), "valor_construcoes"
        ),
        valor_culturas_pastagens_florestas=ler_decimal(
            linha.get("valor_culturas"), "valor_culturas"
        ),
        **comuns,
    )


def ler_planilha(caminho: str | Path) -> tuple[list[ImovelRural], list[LinhaRejeitada]]:
    """Le a planilha e devolve (imoveis validos, linhas rejeitadas).

    Uma linha ruim nao derruba o lote: ela vai para a lista de rejeitadas com o
    numero da linha e o motivo, para conferencia manual.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Planilha nao encontrada: {caminho}")

    sufixo = caminho.suffix.lower()
    if sufixo in (".xlsx", ".xlsm"):
        origem = _linhas_xlsx(caminho)
    elif sufixo == ".csv":
        origem = _linhas_csv(caminho)
    else:
        raise ValueError(f"Formato nao suportado: {sufixo}. Use .xlsx ou .csv.")

    imoveis: list[ImovelRural] = []
    rejeitadas: list[LinhaRejeitada] = []

    for numero, linha in enumerate(origem, start=2):  # linha 1 e o cabecalho
        identificacao = str(linha.get("nirf") or linha.get("nome_imovel") or "?").strip()
        try:
            imoveis.append(montar_imovel(linha))
        except (ErroDeLinha, ValueError, TypeError, KeyError) as e:
            rejeitadas.append(LinhaRejeitada(numero, identificacao, str(e)))

    return imoveis, rejeitadas
