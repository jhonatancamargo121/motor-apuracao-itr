"""Conversor Markdown -> PDF com a identidade visual do projeto.

    python md_para_pdf.py ESCOPO_TECNICO.md
    python md_para_pdf.py ESCOPO_TECNICO.md -o saida/escopo.pdf --subtitulo "v1.0"

Suporta: titulos (#, ##, ###), paragrafos, listas, tabelas, blocos de codigo,
citacao (>), linha horizontal e formatacao inline (**negrito**, *italico*, `codigo`).

As fontes padrao do ReportLab usam WinAnsiEncoding: acentos e travessao renderizam,
mas setas, simbolos matematicos, emoji e caracteres de desenho de caixa viram
quadrado preto. SUBSTITUICOES resolve isso antes da renderizacao.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

ESCURO = colors.HexColor("#1F4E5F")
CLARO = colors.HexColor("#EDF3F5")
CINZA = colors.HexColor("#5A5A5A")
BORDA = colors.HexColor("#C4CDD1")
FUNDO_COD = colors.HexColor("#F4F6F7")

# Caracteres fora do WinAnsiEncoding. Sem isso, viram quadrado preto no PDF.
SUBSTITUICOES = {
    "→": "->", "⇒": "=>", "←": "<-", "↔": "<->",
    "≥": ">=", "≤": "<=", "×": "x", "÷": "/",
    "≠": "!=", "∑": "Soma", "∞": "inf",
    "✅": "[OK]", "⛔": "[BLOQ]", "⬜": "[  ]", "⬛": "[##]",
    "⚠️": "(!)", "⚠": "(!)", "️": "",
    "☑": "[x]", "☐": "[  ]", "✔": "OK", "❌": "X",
    # desenho de caixa -> ASCII
    "┌": "+", "┐": "+", "└": "+", "┘": "+",
    "├": "+", "┤": "+", "┬": "+", "┴": "+", "┼": "+",
    "─": "-", "│": "|", "▼": "v", "▲": "^",
}


def sanear(texto: str) -> str:
    for origem, destino in SUBSTITUICOES.items():
        texto = texto.replace(origem, destino)
    return texto


def escapar(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(texto: str) -> str:
    """Converte formatacao inline do Markdown para as tags do ReportLab."""
    t = escapar(sanear(texto))
    t = re.sub(r"`([^`]+)`", r'<font face="Courier" size="8.4">\1</font>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\*\w])\*([^*]+)\*(?![\*\w])", r"<i>\1</i>", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)  # link -> so o rotulo
    return t


def montar_estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"], fontSize=21, leading=26,
            textColor=ESCURO, spaceAfter=6, alignment=0,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontSize=14.5, leading=18,
            textColor=ESCURO, spaceBefore=16, spaceAfter=7,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=11.5, leading=15,
            textColor=colors.HexColor("#2C6377"), spaceBefore=11, spaceAfter=4,
        ),
        "h3": ParagraphStyle(
            "h3", parent=base["Heading3"], fontSize=10, leading=13,
            textColor=colors.HexColor("#333333"), spaceBefore=9, spaceAfter=3,
        ),
        "corpo": ParagraphStyle(
            "corpo", parent=base["Normal"], fontSize=9.3, leading=13.8,
            alignment=TA_JUSTIFY, spaceAfter=5,
        ),
        "item": ParagraphStyle(
            "item", parent=base["Normal"], fontSize=9.3, leading=13.4,
            leftIndent=15, bulletIndent=5, spaceAfter=2.5,
        ),
        "citacao": ParagraphStyle(
            "citacao", parent=base["Normal"], fontSize=9.0, leading=13,
            leftIndent=12, textColor=CINZA, borderPadding=0, spaceAfter=5,
        ),
        "codigo": ParagraphStyle(
            "codigo", parent=base["Code"], fontSize=7.6, leading=10,
            textColor=colors.HexColor("#1A1A1A"),
        ),
        "celula": ParagraphStyle(
            "celula", parent=base["Normal"], fontSize=7.9, leading=10.8,
        ),
        "celula_cab": ParagraphStyle(
            "celula_cab", parent=base["Normal"], fontSize=7.9, leading=10.5,
            fontName="Helvetica-Bold", textColor=colors.white,
        ),
    }


class Conversor:
    def __init__(self, largura_util: float):
        self.E = montar_estilos()
        self.largura = largura_util
        self.fluxo: list = []
        self.primeiro_titulo = True

    # ------------------------------------------------------------------ blocos

    def _tabela(self, linhas_md: list[str]):
        def celulas(linha: str) -> list[str]:
            return [c.strip() for c in linha.strip().strip("|").split("|")]

        cabecalho = celulas(linhas_md[0])
        corpo = [celulas(l) for l in linhas_md[2:]]
        colunas = len(cabecalho)
        corpo = [c + [""] * (colunas - len(c)) for c in corpo if any(x for x in c)]

        # Largura proporcional ao conteudo, com piso para nao espremer coluna.
        pesos = []
        for i in range(colunas):
            textos = [cabecalho[i]] + [linha[i] for linha in corpo]
            pesos.append(max(6, max((len(t) for t in textos), default=6)) ** 0.62)
        total = sum(pesos)
        larguras = [self.largura * peso / total for peso in pesos]

        dados = [[Paragraph(inline(c), self.E["celula_cab"]) for c in cabecalho]]
        dados += [[Paragraph(inline(c), self.E["celula"]) for c in linha] for linha in corpo]

        t = Table(dados, colWidths=larguras, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ESCURO),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, BORDA),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CLARO]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        self.fluxo.append(Spacer(1, 3))
        self.fluxo.append(t)
        self.fluxo.append(Spacer(1, 7))

    def _codigo(self, linhas: list[str]):
        texto = sanear("\n".join(linhas).rstrip())
        bloco = Preformatted(texto, self.E["codigo"])
        t = Table([[bloco]], colWidths=[self.largura])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), FUNDO_COD),
            ("BOX", (0, 0), (-1, -1), 0.4, BORDA),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        self.fluxo.append(Spacer(1, 3))
        self.fluxo.append(t)
        self.fluxo.append(Spacer(1, 7))

    def _citacao(self, linhas: list[str]):
        texto = " ".join(l.lstrip("> ").strip() for l in linhas)
        par = Paragraph(inline(texto), self.E["citacao"])
        t = Table([[par]], colWidths=[self.largura])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAF5")),
            ("LINEBEFORE", (0, 0), (0, -1), 2.2, colors.HexColor("#B8A24A")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        self.fluxo.append(t)
        self.fluxo.append(Spacer(1, 6))

    # ------------------------------------------------------------------ parser

    def converter(self, markdown: str) -> list:
        linhas = markdown.replace("\r\n", "\n").split("\n")
        i = 0
        paragrafo: list[str] = []

        def descarregar():
            if paragrafo:
                self.fluxo.append(Paragraph(inline(" ".join(paragrafo)), self.E["corpo"]))
                paragrafo.clear()

        while i < len(linhas):
            linha = linhas[i]
            despido = linha.strip()

            if not despido:
                descarregar()
                i += 1
                continue

            if despido.startswith("```"):
                descarregar()
                i += 1
                bloco = []
                while i < len(linhas) and not linhas[i].strip().startswith("```"):
                    bloco.append(linhas[i])
                    i += 1
                self._codigo(bloco)
                i += 1
                continue

            if despido.startswith("|"):
                descarregar()
                tabela = []
                while i < len(linhas) and linhas[i].strip().startswith("|"):
                    tabela.append(linhas[i])
                    i += 1
                if len(tabela) >= 2:
                    self._tabela(tabela)
                continue

            if despido.startswith(">"):
                descarregar()
                bloco = []
                while i < len(linhas) and linhas[i].strip().startswith(">"):
                    bloco.append(linhas[i])
                    i += 1
                self._citacao(bloco)
                continue

            if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", despido):
                descarregar()
                self.fluxo.append(Spacer(1, 5))
                self.fluxo.append(HRFlowable(width="100%", thickness=0.6, color=BORDA))
                self.fluxo.append(Spacer(1, 5))
                i += 1
                continue

            cabecalho = re.match(r"^(#{1,4})\s+(.*)", despido)
            if cabecalho:
                descarregar()
                nivel = len(cabecalho.group(1))
                texto = inline(cabecalho.group(2))
                if nivel == 1 and self.primeiro_titulo:
                    self.fluxo.append(Paragraph(texto, self.E["titulo"]))
                    self.fluxo.append(HRFlowable(width="100%", thickness=1.6, color=ESCURO))
                    self.fluxo.append(Spacer(1, 8))
                    self.primeiro_titulo = False
                else:
                    estilo = {1: "h1", 2: "h2", 3: "h3", 4: "h3"}[nivel]
                    self.fluxo.append(KeepTogether([
                        Paragraph(texto, self.E[estilo]), Spacer(1, 1)
                    ]))
                i += 1
                continue

            lista = re.match(r"^[-*+]\s+(.*)", despido)
            if lista:
                descarregar()
                self.fluxo.append(
                    Paragraph(inline(lista.group(1)), self.E["item"], bulletText="•")
                )
                i += 1
                continue

            numerada = re.match(r"^(\d+)[.)]\s+(.*)", despido)
            if numerada:
                descarregar()
                self.fluxo.append(
                    Paragraph(inline(numerada.group(2)), self.E["item"],
                              bulletText=f"{numerada.group(1)}.")
                )
                i += 1
                continue

            paragrafo.append(despido)
            i += 1

        descarregar()
        return self.fluxo


def gerar(origem: Path, destino: Path, subtitulo: str = "") -> Path:
    titulo_doc = origem.stem.replace("_", " ").title()

    def rodape(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(CINZA)
        rotulo = sanear(subtitulo or titulo_doc)
        canvas.drawString(2.0 * cm, 1.25 * cm, rotulo)
        canvas.drawRightString(A4[0] - 2.0 * cm, 1.25 * cm, f"página {doc.page}")
        canvas.setStrokeColor(colors.HexColor("#DDDDDD"))
        canvas.line(2.0 * cm, 1.62 * cm, A4[0] - 2.0 * cm, 1.62 * cm)
        canvas.restoreState()

    doc = BaseDocTemplate(
        str(destino), pagesize=A4,
        leftMargin=2.0 * cm, rightMargin=2.0 * cm,
        topMargin=1.9 * cm, bottomMargin=2.1 * cm,
        title=titulo_doc, author="Projeto itr-automacao",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="corpo")
    doc.addPageTemplates([PageTemplate(id="padrao", frames=[frame], onPage=rodape)])

    conversor = Conversor(doc.width)
    doc.build(conversor.converter(origem.read_text(encoding="utf-8")))
    return destino


def main() -> int:
    parser = argparse.ArgumentParser(description="Converte Markdown em PDF.")
    parser.add_argument("origem", help="Arquivo .md de entrada")
    parser.add_argument("-o", "--saida", default=None, help="PDF de saida")
    parser.add_argument("--subtitulo", default="", help="Texto do rodape")
    args = parser.parse_args()

    origem = Path(args.origem)
    if not origem.exists():
        print(f"ERRO: arquivo nao encontrado: {origem}", file=sys.stderr)
        return 2

    destino = Path(args.saida) if args.saida else origem.with_suffix(".pdf")
    destino.parent.mkdir(parents=True, exist_ok=True)
    gerar(origem, destino, args.subtitulo)
    print(f"PDF gerado: {destino.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
