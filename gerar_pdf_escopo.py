"""Gera o PDF de escopo e guia de instalacao da automacao do ITR.

    python gerar_pdf_escopo.py

Os identificadores do codigo ficam sem acento; o texto exibido no PDF e acentuado.
As fontes padrao do ReportLab cobrem Latin-1, entao acentos renderizam bem - mas
simbolos fora dessa faixa (caixas de selecao, setas) viram quadrado preto.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

DESTINO = Path("ESCOPO_AUTOMACAO_ITR.pdf")

ESCURO = colors.HexColor("#1F4E5F")
CLARO = colors.HexColor("#E8F1F4")
CINZA = colors.HexColor("#666666")
VERDE = colors.HexColor("#1B7A43")
VERMELHO = colors.HexColor("#A32020")
AMBAR = colors.HexColor("#8A6100")

base = getSampleStyleSheet()

E = {
    "titulo_capa": ParagraphStyle(
        "titulo_capa", parent=base["Title"], fontSize=26, leading=32,
        textColor=ESCURO, spaceAfter=10,
    ),
    "sub_capa": ParagraphStyle(
        "sub_capa", parent=base["Normal"], fontSize=13, leading=18,
        textColor=CINZA, alignment=TA_CENTER,
    ),
    "h1": ParagraphStyle(
        "h1", parent=base["Heading1"], fontSize=16, leading=20, textColor=ESCURO,
        spaceBefore=16, spaceAfter=8,
    ),
    "h2": ParagraphStyle(
        "h2", parent=base["Heading2"], fontSize=12.5, leading=16, textColor=ESCURO,
        spaceBefore=12, spaceAfter=5,
    ),
    "corpo": ParagraphStyle(
        "corpo", parent=base["Normal"], fontSize=9.8, leading=14.5,
        alignment=TA_JUSTIFY, spaceAfter=6,
    ),
    "item": ParagraphStyle(
        "item", parent=base["Normal"], fontSize=9.8, leading=14,
        leftIndent=14, bulletIndent=4, spaceAfter=3,
    ),
    "codigo": ParagraphStyle(
        "codigo", parent=base["Code"], fontSize=8.6, leading=12,
        backColor=colors.HexColor("#F4F4F4"), textColor=colors.HexColor("#1A1A1A"),
        borderPadding=6, leftIndent=6, spaceBefore=4, spaceAfter=8,
    ),
    "celula": ParagraphStyle("celula", parent=base["Normal"], fontSize=8.4, leading=11.5),
    "celula_neg": ParagraphStyle(
        "celula_neg", parent=base["Normal"], fontSize=8.4, leading=11.5,
        fontName="Helvetica-Bold",
    ),
    "cabecalho_tab": ParagraphStyle(
        "cabecalho_tab", parent=base["Normal"], fontSize=8.4, leading=11,
        fontName="Helvetica-Bold", textColor=colors.white,
    ),
}


def p(texto, estilo="corpo"):
    return Paragraph(texto, E[estilo])


def bullets(itens):
    return [Paragraph(t, E["item"], bulletText="\u2022") for t in itens]


def cod(texto):
    escapado = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(escapado.replace("\n", "<br/>"), E["codigo"])


def _celulas(linha):
    return [
        c if isinstance(c, Paragraph) else Paragraph(str(c), E["celula"]) for c in linha
    ]


def tabela(cabecalho, linhas, larguras, meio=True):
    dados = [[Paragraph(c, E["cabecalho_tab"]) for c in cabecalho]]
    dados.extend(_celulas(linha) for linha in linhas)
    t = Table(dados, colWidths=larguras, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ESCURO),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE" if meio else "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CLARO]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def ficha(linhas, larguras):
    """Tabela rotulo/valor, sem linha de cabecalho."""
    t = Table([_celulas(linha) for linha in linhas], colWidths=larguras)
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, CLARO]),
                ("TEXTCOLOR", (0, 0), (0, -1), CINZA),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return t


def aviso(titulo, texto, cor=AMBAR, fundo="#FBF7EC"):
    t = Table(
        [[[
            Paragraph(f'<font color="{cor.hexval()}"><b>{titulo}</b></font>', E["celula_neg"]),
            Paragraph(texto, E["celula"]),
        ]]],
        colWidths=[16.4 * cm],
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fundo)),
                ("BOX", (0, 0), (-1, -1), 0.9, cor),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return t


def destaque(texto, cor):
    return Paragraph(f'<font color="{cor}"><b>{texto}</b></font>', E["celula"])


def rodape(canvas, doc):
    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(2.3 * cm, 1.3 * cm, "Automa\u00e7\u00e3o do ITR \u2014 Escopo e Instala\u00e7\u00e3o")
    canvas.drawRightString(A4[0] - 2.3 * cm, 1.3 * cm, f"p\u00e1gina {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#DDDDDD"))
    canvas.line(2.3 * cm, 1.7 * cm, A4[0] - 2.3 * cm, 1.7 * cm)
    canvas.restoreState()


def construir():
    doc = BaseDocTemplate(
        str(DESTINO), pagesize=A4,
        leftMargin=2.3 * cm, rightMargin=2.3 * cm,
        topMargin=2.0 * cm, bottomMargin=2.2 * cm,
        title="Automação do ITR — Escopo e Guia de Instalação",
        author="Projeto itr-automacao",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="corpo")
    doc.addPageTemplates([PageTemplate(id="padrao", frames=[frame], onPage=rodape)])
    doc.build(conteudo())
    return DESTINO


def conteudo():
    hoje = date.today().strftime("%d/%m/%Y")
    s = []

    # ------------------------------------------------------------------ capa
    s.append(Spacer(1, 4.5 * cm))
    s.append(Paragraph("Automação do ITR", E["titulo_capa"]))
    s.append(Paragraph("Escopo do projeto e guia de instalação", E["sub_capa"]))
    s.append(Spacer(1, 1.2 * cm))
    s.append(ficha(
        [
            ["Projeto", Paragraph("<b>itr-automacao</b>", E["celula"])],
            ["Base", "Processo do vídeo PC Manoel.mp4 (PGD ITR 2025 v1.7)"],
            ["Linguagem", "Python 3.10 ou superior"],
            ["Data", hoje],
            ["Situação", Paragraph(
                '<font color="#1B7A43"><b>Módulo 1 pronto</b></font> '
                '&mdash; módulos 2 e 3 especificados', E["celula"])],
        ],
        [4.2 * cm, 12.2 * cm],
    ))
    s.append(Spacer(1, 1.4 * cm))
    s.append(aviso(
        "Leia antes de começar",
        "Este documento descreve o que será automatizado e o que continua sendo feito por "
        "uma pessoa. A <b>transmissão da declaração</b> e o <b>pagamento do DARF</b> não "
        "são automatizados em nenhuma fase do projeto &mdash; são atos do responsável "
        "técnico.",
    ))
    s.append(PageBreak())

    # ------------------------------------------------------------------ 1
    s.append(p("1. Resumo do escopo", "h1"))
    s.append(p(
        "O processo do ITR observado no vídeo tem oito etapas, da abertura do programa até "
        "a transmissão. O projeto divide essas etapas em três módulos independentes, para "
        "que a falha ou o atraso de um não trave os outros."
    ))
    s.append(tabela(
        ["Módulo", "O que faz", "Depende de", "Situação"],
        [
            [Paragraph("<b>1. Apuração<br/>e conferência</b>", E["celula"]),
             "Lê a planilha de imóveis, calcula área tributável, grau de utilização, VTN e "
             "imposto devido. Emite relatório de conferência.",
             "Nada. Python puro.",
             destaque("PRONTO<br/>65 testes", "#1B7A43")],
            [Paragraph("<b>2. Preenchimento<br/>do PGD</b>", E["celula"]),
             "Leva os dados apurados para dentro do programa da Receita e lê a tela de "
             "pendências.",
             "Acesso ao PC com o PGD instalado.",
             destaque("BLOQUEADO<br/>faltam 3 respostas", "#8A6100")],
            [Paragraph("<b>3. DARF e<br/>arquivamento</b>", E["celula"]),
             "Emite a guia de pagamento no Sicalc e arquiva o PDF com nome padronizado.",
             "Navegador automatizado (Playwright).",
             destaque("ESPECIFICADO", "#666666")],
        ],
        [3.0 * cm, 6.4 * cm, 3.5 * cm, 3.5 * cm], meio=False,
    ))

    s.append(p("1.1 O que entra no escopo", "h2"))
    s.extend(bullets([
        "Leitura da planilha de imóveis rurais, em <b>.xlsx</b> ou <b>.csv</b>.",
        "Validação dos dados <b>antes</b> de virar declaração: soma de áreas, valores "
        "negativos, campos obrigatórios ausentes.",
        "Cálculo completo da apuração: área tributável, área aproveitável, grau de "
        "utilização, VTN, VTN tributável, alíquota e imposto devido.",
        "Aplicação das regras de <b>imunidade</b> (pequena gleba) e <b>isenção</b> "
        "(assentamento).",
        "Relatório de conferência separando: sem ressalvas, com alertas, rejeitados.",
        "Exportação da apuração em CSV para conferência em planilha.",
        "Preenchimento das fichas do PGD e leitura da tela <i>Verificar Pendências</i>.",
        "Emissão do DARF pelo Sicalc e arquivamento do PDF.",
    ]))

    s.append(p("1.2 O que fica fora do escopo", "h2"))
    s.append(p(
        "Estes pontos <b>não serão automatizados</b>, por decisão de projeto. Não é "
        "limitação técnica: são passos em que o erro automatizado custa caro demais."
    ))
    s.append(tabela(
        ["Fora do escopo", "Por quê"],
        [
            ["Transmissão da declaração",
             "É ato do responsável técnico, feito com procuração eletrônica. A automação "
             "para na tela anterior e devolve o controle."],
            ["Pagamento do DARF",
             "Emitir a guia é automação; pagar é movimentação financeira."],
            ["Resolver erro de pendência",
             "Erro em <i>Verificar Pendências</i> significa dado inconsistente. A automação "
             "aborta e informa qual é o erro."],
            ["Captcha ou segundo fator",
             "Se aparecer em qualquer portal, o processo para e avisa o operador."],
            ["Extração automática dos laudos de VTN",
             "Os laudos são PDF escaneado, sem camada de texto. O OCR exigiria conferência "
             "manual de tudo. A tabela de VTN é mantida à mão, em CSV."],
        ],
        [5.2 * cm, 11.2 * cm], meio=False,
    ))
    s.append(PageBreak())

    # ------------------------------------------------------------------ 2
    s.append(p("2. Programas que precisam ser instalados", "h1"))
    s.append(p(
        "A tabela abaixo separa o que é obrigatório para cada módulo. <b>Para usar o Módulo "
        "1, que já está pronto, bastam o Python e uma biblioteca.</b> O resto só é "
        "necessário quando os módulos 2 e 3 entrarem."
    ))

    def sim(t="Sim"):
        return destaque(t, "#A32020")

    def opc(t="Opcional"):
        return Paragraph(f'<font color="#666666">{t}</font>', E["celula"])

    s.append(tabela(
        ["Programa", "Para que serve", "Módulo", "Obrigatório"],
        [
            [Paragraph("<b>Python 3.10+</b>", E["celula"]),
             "Interpretador da linguagem. Base de tudo.", "1, 2, 3", sim()],
            [Paragraph("<b>openpyxl</b>", E["celula"]),
             "Ler e gravar planilhas .xlsx.", "1", sim()],
            [Paragraph("<b>pytest</b>", E["celula"]),
             "Rodar a bateria de testes do cálculo.", "1", opc("Recomendado")],
            [Paragraph("<b>PGD ITR</b>", E["celula"]),
             "Programa da Receita Federal onde a declaração é preenchida. Instalado na "
             "máquina de trabalho.", "2", sim()],
            [Paragraph("<b>Java Access<br/>Bridge</b>", E["celula"]),
             "Ponte de acessibilidade da JVM. É o que permite ler os campos do PGD sem "
             "clicar às cegas em coordenada de tela.", "2", sim("Se via tela")],
            [Paragraph("<b>pyjab</b>", E["celula"]),
             "Biblioteca Python que conversa com o Java Access Bridge.", "2",
             sim("Se via tela")],
            [Paragraph("<b>Playwright</b>", E["celula"]),
             "Navegador automatizado, para o Sicalc e o e-CAC.", "3", sim()],
            [Paragraph("<b>pypdf</b>", E["celula"]),
             "Validar que o DARF baixado é mesmo um PDF, e não página de erro.", "3", sim()],
            [Paragraph("<b>Certificado A1</b>", E["celula"]),
             "Arquivo .pfx do certificado digital. Só para baixar recibos no e-CAC.", "3",
             opc()],
            [Paragraph("<b>Git</b>", E["celula"]),
             "Versionar o código e voltar atrás quando algo quebrar.", "\u2014",
             opc("Recomendado")],
        ],
        [3.1 * cm, 7.6 * cm, 2.1 * cm, 3.6 * cm], meio=False,
    ))
    s.append(Spacer(1, 0.3 * cm))
    s.append(aviso(
        "Sobre o certificado digital",
        "O <b>A1</b> é um arquivo e funciona com automação. O <b>A3</b>, que fica em token "
        "ou cartão, <b>não funciona</b>: a chave não pode ser exportada. Se os clientes "
        "usarem A3, a parte de recibos no e-CAC continua manual.",
    ))
    s.append(PageBreak())

    # ------------------------------------------------------------------ 3
    s.append(p("3. Passo a passo da instalação", "h1"))

    s.append(p("Passo 1 &mdash; Instalar o Python", "h2"))
    s.append(p(
        "Baixe em <b>python.org/downloads</b> a versão 3.10 ou superior. Na primeira tela do "
        "instalador, marque <b>Add Python to PATH</b> antes de continuar &mdash; sem isso os "
        "comandos seguintes não funcionam."
    ))
    s.append(p("Confira no terminal:"))
    s.append(cod("python --version"))
    s.append(p("Deve responder algo como <b>Python 3.12.10</b>."))

    s.append(p("Passo 2 &mdash; Instalar as bibliotecas do Módulo 1", "h2"))
    s.append(p("Só estas duas já fazem o módulo pronto funcionar:"))
    s.append(cod("python -m pip install openpyxl pytest"))

    s.append(p("Passo 3 &mdash; Conferir que está tudo certo", "h2"))
    s.append(p("Entre na pasta do projeto e rode a bateria de testes:"))
    s.append(cod("cd C:\\Users\\<usuario>\\Documents\\itr-automacao\npython -m pytest tests/ -q"))
    s.append(p(
        "A resposta esperada termina com <b>65 passed</b>. Se algum teste falhar, pare e "
        "resolva antes de usar o sistema com dados reais."
    ))

    s.append(p("Passo 4 &mdash; Gerar a planilha modelo", "h2"))
    s.append(cod("python criar_modelo.py"))
    s.append(p(
        "Cria <b>dados/modelo_imoveis.xlsx</b>, com 30 colunas e uma aba de instruções "
        "explicando o que vai em cada uma. Para ver exemplos preenchidos, use "
        "<b>--com-exemplos</b>."
    ))

    s.append(p("Passo 5 &mdash; Rodar a apuração", "h2"))
    s.append(cod("python processar.py dados/modelo_imoveis.xlsx --csv saida/apuracao_2026.csv"))
    s.append(p(
        "Imprime o relatório de conferência na tela e grava o CSV. O comando termina com "
        "código <b>1</b> quando há algo para revisar e <b>0</b> quando não há."
    ))

    s.append(KeepTogether([
        p("Passo 6 &mdash; Preparar o Módulo 3 (DARF), quando for a hora", "h2"),
        cod("python -m pip install playwright pypdf\npython -m playwright install chromium"),
        p("O segundo comando baixa o navegador que o Playwright controla. Sem ele, a "
          "automação do Sicalc não abre."),
    ]))

    s.append(KeepTogether([
        p("Passo 7 &mdash; Preparar o Módulo 2 (PGD), quando destravar", "h2"),
        p("Somente se o caminho escolhido for automação de tela. Primeiro habilite a ponte "
          "de acessibilidade do Java, depois instale a biblioteca:"),
        cod("jabswitch -enable\npython -m pip install pyjab"),
        p("O <b>jabswitch</b> vem junto com o Java. Se o comando não for reconhecido, o Java "
          "precisa ser instalado ou localizado &mdash; o PGD costuma trazer a própria cópia, "
          "que nem sempre está no PATH do sistema."),
    ]))
    s.append(PageBreak())

    # ------------------------------------------------------------------ 4
    s.append(p("4. O que trava o Módulo 2 hoje", "h1"))
    s.append(p(
        "O preenchimento do PGD não pode ser escrito antes de três respostas. Elas só podem "
        "ser obtidas na máquina onde o programa está instalado. A escolha da arquitetura "
        "depende inteiramente delas."
    ))
    s.append(tabela(
        ["#", "Pergunta", "Por que importa"],
        [
            ["B1", "Onde fica a pasta de instalação do PGD e o que há dentro dela?",
             "Define se existe arquivo de declaração acessível."],
            ["B2", "Em que formato uma declaração gravada é armazenada?",
             "Se for banco legível, dá para gravar direto e pular a tela toda."],
            ["B3", "O menu <i>Importar Dados ITR</i> aceita arquivo externo ou só lê a "
             "instalação do ano anterior?",
             "Se aceitar arquivo, esse é o caminho oficial e o mais seguro."],
        ],
        [1.1 * cm, 7.3 * cm, 8.0 * cm], meio=False,
    ))
    s.append(Spacer(1, 0.3 * cm))
    s.append(p("Comando para levantar B1, no PowerShell da máquina do PGD:"))
    s.append(cod('Get-ChildItem "C:\\Arquivos de Programas\\Programas RFB" -Recurse -Depth 2 |\n'
                 '  Select-Object FullName, Length'))

    s.append(p("4.1 Caminhos possíveis, em ordem de preferência", "h2"))
    s.append(tabela(
        ["Caminho", "Vantagem", "Risco", "Quando usar"],
        [
            [Paragraph("<b>A.</b> Arquivo de<br/>importação", E["celula"]),
             "Oficial, estável, rápido.", "Nenhum relevante.",
             "Se B3 confirmar que aceita arquivo."],
            [Paragraph("<b>B.</b> Banco local<br/>do PGD", E["celula"]),
             "Muito rápido, dispensa tela.",
             destaque("Não suportado. Atualização do PGD pode quebrar, e há risco de "
                      "corromper a base.", "#A32020"),
             "Só com backup verificado a cada execução."],
            [Paragraph("<b>C.</b> Java Access<br/>Bridge", E["celula"]),
             "Lê os campos de verdade, não chuta posição.",
             "Trabalhoso e lento; quebra a cada versão nova do PGD.",
             "Se A e B não forem viáveis."],
            [Paragraph("<b>D.</b> Clique por<br/>coordenada", E["celula"]),
             "Fácil de começar.",
             destaque("Descartado. Preenche o campo errado em silêncio quando a tela muda.",
                      "#A32020"),
             "Nunca."],
        ],
        [2.9 * cm, 4.0 * cm, 5.3 * cm, 4.2 * cm], meio=False,
    ))
    s.append(Spacer(1, 0.3 * cm))
    s.append(aviso(
        "Regra inegociável para os caminhos B e C",
        "Antes de qualquer escrita, gerar backup pelo próprio PGD, em <i>Ferramentas &gt; "
        "Gravar Cópia de Segurança</i>. Sem backup conferido, a automação não roda.",
        VERMELHO, "#FBEDED",
    ))
    s.append(PageBreak())

    # ------------------------------------------------------------------ 5
    s.append(p("5. Riscos e como são tratados", "h1"))
    alta = destaque("Alta", "#A32020")
    media = destaque("Média", "#8A6100")
    s.append(tabela(
        ["Risco", "Gravidade", "Como é tratado"],
        [
            ["Automação preenche campo errado sem dar erro", alta,
             "Conferência campo a campo na primeira declaração gerada. Caminho D descartado."],
            ["Escrita direta na base corrompe declaração", alta,
             "Backup obrigatório antes de cada execução."],
            ["Tabela de alíquotas incorreta", alta,
             "Conferência contra o Anexo da Lei 9.393/96 antes do uso em cliente real."],
            ["Isentar quem deveria pagar", alta,
             "Campos SIM/NÃO em branco assumem o pior caso. O sistema nunca concede "
             "imunidade por dado omitido."],
            ["Atualização anual do PGD quebra a automação", media,
             "Mapeamento de campos concentrado em um módulo só. Retrabalho anual previsto."],
            ["Laudo de VTN desatualizado", media,
             "Data do laudo registrada junto do valor, no CSV de VTN."],
            ["Baixar recibo do contribuinte errado", alta,
             "Validação do perfil ativo no e-CAC antes de qualquer download."],
        ],
        [5.0 * cm, 2.0 * cm, 9.4 * cm], meio=False,
    ))

    # ------------------------------------------------------------------ 6
    s.append(p("6. Checklist de implantação", "h1"))
    s.append(p("Na ordem. Os quatro primeiros itens não dependem de ninguém externo."))
    s.append(tabela(
        ["", "Item", "Responsável"],
        [
            ["[  ]", "Instalar o Python e as bibliotecas do Módulo 1", "TI"],
            ["[  ]", "Rodar os testes e confirmar 65 passed", "TI"],
            ["[  ]", "Conferir a tabela de alíquotas contra a Lei 9.393/96", "Contabilidade"],
            ["[  ]", "Definir o tratamento de grau de utilização quando a área aproveitável "
                     "é zero", "Contabilidade"],
            ["[  ]", "Preencher a planilha modelo com a carteira real", "Contabilidade"],
            ["[  ]", "Conferir à mão pelo menos 5 imóveis contra o resultado do sistema",
             "Contabilidade"],
            ["[  ]", "Levantar B1, B2 e B3 na máquina do PGD", "TI"],
            ["[  ]", "Escolher o caminho do Módulo 2 e registrar a decisão", "TI"],
            ["[  ]", "Instalar o Playwright e implantar o Módulo 3 (DARF)", "TI"],
        ],
        [1.2 * cm, 11.2 * cm, 4.0 * cm], meio=False,
    ))
    s.append(Spacer(1, 0.5 * cm))
    s.append(aviso(
        "Antes do primeiro uso com cliente real",
        "Rodar a carteira inteira pelo sistema e conferir à mão uma amostra dos imóveis. O "
        "sistema separa o que precisa de atenção, mas quem assina a declaração continua "
        "sendo o responsável técnico.",
        VERDE, "#EDF6F0",
    ))

    return s


if __name__ == "__main__":
    print(f"PDF gerado: {construir().resolve()}")
