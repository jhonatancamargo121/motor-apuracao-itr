"""Gera a planilha modelo para o escritorio preencher.

    python criar_modelo.py                 -> modelo em branco + aba de instrucoes
    python criar_modelo.py --com-exemplos  -> inclui 4 linhas de exemplo

As linhas de exemplo servem so para demonstrar o formato. Apague antes de usar.
"""

from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from itr.planilha import COLUNAS_MODELO

DESTINO = Path("dados/modelo_imoveis.xlsx")

AJUDA = {
    "nirf": "Codigo do imovel no Incra (NIRF/CIB). Obrigatorio.",
    "nome_imovel": "Nome da propriedade. Obrigatorio.",
    "exercicio": "Ano da declaracao. Obrigatorio.",
    "municipio": "Municipio de localizacao (domicilio tributario).",
    "uf": "Sigla da UF.",
    "regiao": "demais | poligono_secas_amazonia_oriental | amazonia_ocidental_pantanal",
    "area_total_ha": "Campo 01 do DIAT. Obrigatorio.",
    "preservacao_permanente": "Campo 02.",
    "reserva_legal": "Campo 03.",
    "rppn": "Campo 04.",
    "interesse_ecologico": "Campo 05.",
    "servidao_ambiental": "Campo 06.",
    "floresta_nativa": "Campo 07.",
    "alagada_reservatorio": "Campo 08.",
    "imprestavel": "Area comprovadamente imprestavel.",
    "benfeitorias_ha": "Campo 10. Sai da area aproveitavel, fica na tributavel.",
    "produtos_vegetais": "Campo 12.",
    "descanso": "Campo 13.",
    "reflorestamento": "Campo 14.",
    "pastagem": "Campo 15.",
    "exploracao_extrativa": "Campo 16.",
    "granjeira_aquicola": "Campo 17.",
    "frustracao_safra": "Campo 18.",
    "valor_total_imovel": "Ficha Calculo do Imposto, campo 01.",
    "valor_construcoes": "Campo 02. Subtraido do valor total.",
    "valor_culturas": "Campo 03. Subtraido do valor total.",
    "explora_com_familia": "SIM/NAO. Necessario para imunidade de pequena gleba.",
    "possui_outro_imovel": "SIM/NAO. Vazio = SIM (conservador).",
    "possui_imovel_urbano": "SIM/NAO. Vazio = SIM (conservador).",
    "assentamento": "SIM/NAO. Imovel de reforma agraria.",
}

# VTN de pastagem em Petrolina de Goias 2026, conforme laudo: R$ 29.490,00/ha.
EXEMPLOS = [
    {  # imovel do video: pequeno, unico -> imune
        "nirf": "7.721.955-4", "nome_imovel": "FAZENDA TAPERAO", "exercicio": 2026,
        "municipio": "Petrolina de Goias", "uf": "GO", "regiao": "demais",
        "area_total_ha": "5,9", "preservacao_permanente": "1,0", "pastagem": "4,9",
        "valor_total_imovel": "173991,00",
        "explora_com_familia": "SIM", "possui_outro_imovel": "NAO",
    },
    {  # medio, com imposto real
        "nirf": "6.845.427-9", "nome_imovel": "FAZENDA BEIRA RIO", "exercicio": 2026,
        "municipio": "Petrolina de Goias", "uf": "GO", "regiao": "demais",
        "area_total_ha": "320", "reserva_legal": "64", "pastagem": "240",
        "benfeitorias_ha": "6", "valor_total_imovel": "9436800,00",
        "valor_construcoes": "180000,00",
        "explora_com_familia": "SIM", "possui_outro_imovel": "SIM",
    },
    {  # gera alerta: area utilizada maior que a aproveitavel
        "nirf": "5.130.050-6", "nome_imovel": "FAZENDA SERRINHA", "exercicio": 2026,
        "municipio": "Inhumas", "uf": "GO", "regiao": "demais",
        "area_total_ha": "100", "reserva_legal": "20", "pastagem": "95",
        "valor_total_imovel": "2500000,00",
        "explora_com_familia": "SIM", "possui_outro_imovel": "SIM",
    },
    {  # rejeitado: soma das areas nao tributaveis maior que a total
        "nirf": "8.233.569-0", "nome_imovel": "CHACARA PEDACINHO DO CEU", "exercicio": 2026,
        "municipio": "Trindade", "uf": "GO", "regiao": "demais",
        "area_total_ha": "50", "reserva_legal": "40", "preservacao_permanente": "30",
        "valor_total_imovel": "1200000,00",
    },
]


def criar(destino: Path, com_exemplos: bool) -> Path:
    wb = Workbook()

    ws = wb.active
    ws.title = "imoveis"

    cabecalho_fill = PatternFill("solid", fgColor="1F4E5F")
    cabecalho_fonte = Font(color="FFFFFF", bold=True, size=10)

    for coluna, nome in enumerate(COLUNAS_MODELO, start=1):
        celula = ws.cell(row=1, column=coluna, value=nome)
        celula.fill = cabecalho_fill
        celula.font = cabecalho_fonte
        celula.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        largura = max(len(nome) + 2, 14)
        ws.column_dimensions[get_column_letter(coluna)].width = largura

    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 30

    if com_exemplos:
        for indice, exemplo in enumerate(EXEMPLOS, start=2):
            for coluna, nome in enumerate(COLUNAS_MODELO, start=1):
                ws.cell(row=indice, column=coluna, value=exemplo.get(nome))

    doc = wb.create_sheet("instrucoes")
    doc.column_dimensions["A"].width = 28
    doc.column_dimensions["B"].width = 78
    doc["A1"] = "coluna"
    doc["B1"] = "o que preencher"
    for celula in ("A1", "B1"):
        doc[celula].fill = cabecalho_fill
        doc[celula].font = cabecalho_fonte

    for linha, nome in enumerate(COLUNAS_MODELO, start=2):
        doc.cell(row=linha, column=1, value=nome).font = Font(bold=True, size=10)
        doc.cell(row=linha, column=2, value=AJUDA.get(nome, ""))

    proxima = len(COLUNAS_MODELO) + 3
    notas = [
        "REGRAS GERAIS",
        "Areas em hectares, valores em reais. Aceita 1.234,56 ou 1234.56.",
        "Campos de area vazios valem zero.",
        "Colunas SIM/NAO vazias assumem o padrao conservador (nunca isenta por engano).",
        "NAO preencha area tributavel, aproveitavel, utilizada nem GU: sao calculados.",
        "O VTN e derivado: valor_total_imovel - valor_construcoes - valor_culturas.",
        "A ordem das colunas nao importa; o nome sim (acento e maiuscula sao ignorados).",
    ]
    for deslocamento, texto in enumerate(notas):
        celula = doc.cell(row=proxima + deslocamento, column=1, value=texto)
        if deslocamento == 0:
            celula.font = Font(bold=True, size=11)

    destino.parent.mkdir(parents=True, exist_ok=True)
    wb.save(destino)
    return destino


if __name__ == "__main__":
    com_exemplos = "--com-exemplos" in sys.argv
    caminho = criar(DESTINO, com_exemplos)
    print(f"Planilha modelo criada: {caminho}")
    print(f"  {len(COLUNAS_MODELO)} colunas" + (f" + {len(EXEMPLOS)} exemplos" if com_exemplos else ""))
