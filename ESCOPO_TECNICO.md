# Escopo Técnico — Automação da Declaração do ITR

| | |
|---|---|
| **Projeto** | `itr-automacao` |
| **Versão do documento** | 1.0 |
| **Data** | 12/08/2026 |
| **Domínio** | Imposto sobre a Propriedade Territorial Rural (Lei 9.393/96) |
| **Sistema alvo** | PGD ITR 2025 v1.7 (Java Swing, desktop) |
| **Stack** | Python 3.10+ · stdlib · openpyxl · (Playwright, pyjab conforme fase) |
| **Origem dos requisitos** | Captura de tela `PC Manoel.mp4`, transcrição de áudio do responsável técnico, laudo de VTN de Petrolina de Goiás 2026 |

---

## 1. Objetivo e enquadramento

Automatizar a preparação, apuração e instrumentação da declaração do ITR para uma
carteira de imóveis rurais, mantendo sob responsabilidade humana todo ato com
efeito jurídico ou financeiro irreversível.

O sistema é uma **ferramenta de apoio ao responsável técnico**, não um substituto.
Essa distinção não é retórica: ela determina o desenho de erros (§8), a política de
falha (§9) e os limites de escopo (§13).

### 1.1 Métricas de sucesso

| Métrica | Linha de base | Alvo |
|---|---|---|
| Tempo de preparação por imóvel | manual, integral | redução ≥ 70% nas etapas de coleta, cálculo e conferência |
| Erros de digitação em áreas/valores | não medido | zero na etapa automatizada (validação bloqueia na entrada) |
| Rastreabilidade da apuração | inexistente | 100% — toda linha apurada aponta para a origem |
| Divergência vs. apuração manual | — | zero em amostra de conferência de 5 imóveis |

---

## 2. Glossário de domínio

Termos usados com significado preciso ao longo do documento.

| Termo | Definição operacional |
|---|---|
| **VTN** | Valor da Terra Nua. Campo 04 do PGD; derivado, não digitado (§4.3) |
| **VTNt** | VTN Tributável. VTN proporcional à razão área tributável / área total |
| **Área tributável** | Área total menos as áreas não tributáveis (campos 02–08) |
| **Área aproveitável** | Área tributável menos a área de benfeitorias (campo 10) |
| **GU** | Grau de Utilização. Área utilizada ÷ área aproveitável × 100 |
| **Pequena gleba** | Limite de área para imunidade, variável por região: 30/50/100 ha |
| **Dispensa** | Termo do sistema que agrupa imunidade (art. 2º) e isenção (art. 3º) |
| **Pendência bloqueante** | Item classificado como *erro* pelo PGD; impede gravação e entrega |
| **Alerta** | Decisão discutível tomada pelo sistema, sinalizada para revisão humana |
| **Rejeição** | Linha de entrada que violou invariante e não foi apurada |

---

## 3. Arquitetura

### 3.1 Estilo

**Ports & Adapters (hexagonal).** O núcleo de domínio — apuração — não conhece
planilha, PGD nem navegador. Integrações entram por interfaces declaradas no
núcleo e implementadas na borda.

A justificativa é concreta: o mecanismo de integração com o PGD **ainda não foi
decidido** (§5, ADR-004) e depende de levantamento externo. O desenho permite
escrever e testar toda a orquestração antes dessa decisão, trocando apenas o
adaptador.

### 3.2 Camadas

```
┌─────────────────────────────────────────────────────────────┐
│  Interface de linha de comando                              │
│  processar.py · criar_modelo.py · gerar_pdf_escopo.py       │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Aplicação — orquestração e políticas                        │
│  relatorio.py (lote, classificação)                          │
│  [F2] orquestrador.py (backup → preenche → verifica → para)  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Domínio — puro, sem I/O, determinístico                     │
│  modelo.py    invariantes estruturais                        │
│  tabela.py    Anexo da Lei 9.393/96                          │
│  calculo.py   dispensa · GU · VTNt · alíquota · imposto      │
└───────────────────────────┬─────────────────────────────────┘
                            │  (portas)
┌───────────────────────────▼─────────────────────────────────┐
│  Adaptadores                                                 │
│  planilha.py         .xlsx/.csv  → ImovelRural   ✅ pronto   │
│  [F2] driver_*.py    DriverPGD                    ⛔ bloq.   │
│  [F3] sicalc.py      Playwright → DARF            ⬜ spec    │
│  [F3] ecac.py        Playwright + A1 → recibo     ⬜ spec    │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Regra de dependência

Dependências apontam **sempre para dentro**. `calculo.py` não importa `planilha.py`.
Violar isso quebra a testabilidade do núcleo, que hoje roda sem nenhuma dependência
externa além da stdlib.

---

## 4. Modelo de domínio e invariantes

### 4.1 Tipos

Todo valor numérico do domínio é `Decimal`. **`float` é proibido** em qualquer
grandeza monetária ou de área — a soma de áreas em ponto flutuante binário produz
divergência de centavos na apuração, e divergência de centavos em declaração
fiscal é retrabalho.

Conversão de entrada sempre via `str`: `Decimal(str(valor))`, nunca `Decimal(float)`.

### 4.2 Invariantes

Verificados na construção de `ImovelRural`. Violação levanta `ValueError` e a linha
é **rejeitada, não corrigida** — corrigir dado de cliente em silêncio é inaceitável.

| ID | Invariante | Onde |
|---|---|---|
| **I1** | `area_total > 0` | `modelo._validar` |
| **I2** | `vtn >= 0` | `modelo._validar` |
| **I3** | `Σ areas_nao_tributaveis <= area_total` | `modelo._validar` |
| **I4** | `Σ areas_nao_tributaveis + area_benfeitorias <= area_total` | `modelo._validar` |
| **I5** | `area_tributavel = area_total − Σ nao_tributaveis` | `modelo.area_tributavel` |
| **I6** | `area_aproveitavel = max(area_tributavel − benfeitorias, 0)` | `modelo.area_aproveitavel` |
| **I7** | `0 <= GU <= 100` | `calculo.calcular_grau_utilizacao` |
| **I8** | `VTNt = VTN × (area_tributavel ÷ area_total)` | `calculo.apurar` |
| **I9** | `imposto >= 10,00` quando não dispensado | `calculo.apurar` |
| **I10** | Nenhuma dispensa sem fato declarado explicitamente | `calculo.verificar_dispensa` |

**I10 é a invariante de segurança do sistema.** Campos booleanos omitidos assumem o
caso desfavorável ao contribuinte (`possui_outro_imovel_rural = True`). O sistema
pode apurar imposto a mais numa conferência interna — nunca isentar por omissão.

### 4.3 Derivação do VTN

Espelha a ficha *Cálculo do Imposto* do PGD:

```
campo 04 (VTN) = campo 01 (valor total do imóvel)
               − campo 02 (construções, instalações e benfeitorias)
               − campo 03 (culturas, pastagens cultivadas, florestas plantadas)
```

Resultado negativo é erro de entrada, não zero implícito. `ImovelRural.com_valores()`
recusa com mensagem explícita.

### 4.4 Ponto de interpretação em aberto

`area_aproveitavel == 0` → GU fixado em **100%**, com alerta emitido.

É o ponto de maior divergência interpretativa da apuração. A implementação atual é
uma decisão **provisória e sinalizada**, não uma conclusão. Ver ADR-005 e §14/Q2.

---

## 5. Decisões de arquitetura (ADR)

### ADR-001 — `Decimal` obrigatório, `float` proibido
**Status:** aceito · **Contexto:** valores monetários e áreas somadas em cadeia.
**Decisão:** `Decimal` com `ROUND_HALF_UP` e quantização a 2 casas apenas na saída
monetária; precisão plena no cálculo intermediário.
**Consequência:** entrada precisa passar por `str`; ganho de exatidão exata,
custo de performance irrelevante nesta escala.

### ADR-002 — Rejeitar linha inválida, não sanear
**Status:** aceito · **Contexto:** planilha preenchida por humanos, com erros.
**Decisão:** invariante violada → `ValueError` → linha vai para `rejeitadas` com
número de linha e motivo; o lote continua.
**Consequência:** o operador vê exatamente o que corrigir; o sistema nunca inventa
dado. Custo: exige revisão da lista de rejeitados a cada execução.

### ADR-003 — Padrão conservador em campos omitidos
**Status:** aceito · **Contexto:** imunidade depende de fato declarado pelo contribuinte.
**Decisão:** booleanos vazios assumem o caso que **não** concede benefício fiscal.
**Consequência:** falso positivo de tributação (detectável na conferência) em vez de
falso negativo (risco fiscal). Assimetria deliberada.

### ADR-004 — Mecanismo de integração com o PGD adiado
**Status:** **pendente de levantamento** · **Contexto:** PGD é Java Swing, sem API,
sem CLI, sem formato documentado. Quatro caminhos possíveis com ordens de grandeza
diferentes de esforço (§7.2).
**Decisão:** definir a porta `DriverPGD` agora; escolher o adaptador após responder
Q3–Q5 (§14).
**Consequência:** toda a orquestração pode ser escrita e testada contra um driver
simulado antes da decisão. Sem essa separação, a escolha errada custaria reescrita
total do módulo.

### ADR-005 — GU com área aproveitável zero
**Status:** **provisório** · **Decisão:** GU = 100%, com alerta obrigatório.
**Consequência:** nenhuma declaração passa por esse caminho sem sinalização. Requer
ratificação da contabilidade antes do uso em produção.

### ADR-006 — `pywinauto`/UIA descartado para o PGD
**Status:** aceito · **Contexto:** Swing não expõe controles ao UI Automation do Windows.
**Decisão:** se for automação de tela, será via Java Access Bridge (`pyjab`).
**Consequência:** exige habilitar a ponte de acessibilidade na JVM do PGD.

### ADR-007 — Automação por coordenada de tela proibida
**Status:** aceito · **Contexto:** `pyautogui` e equivalentes.
**Decisão:** vedado em qualquer fase.
**Consequência:** o modo de falha dessa técnica é preencher **o campo errado em
silêncio** quando a tela muda (resolução, tema, scroll, versão). Em declaração
fiscal, falha silenciosa é a categoria de risco inaceitável. Restrição arquitetural,
não preferência.

### ADR-008 — Tabela de VTN mantida manualmente
**Status:** aceito · **Contexto:** laudos são PDF escaneado sem camada de texto.
**Decisão:** CSV versionado por exercício, com data do laudo; laudo arquivado ao lado.
**Consequência:** ~12 municípios/ano de digitação, contra um pipeline de OCR que
exigiria conferência integral de qualquer forma. Custo-benefício desfavorável ao OCR.

---

## 6. Especificação dos componentes

### 6.1 Módulo 1 — Apuração e conferência ✅ implementado

| Unidade | Responsabilidade | Estado |
|---|---|---|
| `itr/modelo.py` | Entidades, invariantes I1–I6, derivação do VTN | ✅ |
| `itr/tabela.py` | Anexo da Lei 9.393/96; faixas de área × GU | ✅ ⚠️ pendente ratificação |
| `itr/calculo.py` | Dispensa, GU, VTNt, alíquota, imposto, alertas | ✅ |
| `itr/planilha.py` | Adaptador .xlsx/.csv → `ImovelRural` | ✅ |
| `itr/relatorio.py` | Classificação do lote, formatação, export CSV | ✅ |
| `tests/` | 65 casos | ✅ |

**Contrato de saída:**

```python
@dataclass(frozen=True)
class Apuracao:
    nirf: str; exercicio: int; nome: str; municipio: str
    area_total: Decimal; area_tributavel: Decimal
    area_aproveitavel: Decimal; area_utilizada: Decimal
    grau_utilizacao: Decimal          # %
    vtn: Decimal; vtn_tributavel: Decimal
    aliquota: Decimal                 # %
    imposto_devido: Decimal
    dispensado: bool = False
    motivo_dispensa: str | None = None
    alertas: tuple[str, ...] = ()     # nunca None; vazio = sem ressalva
```

`Apuracao` é imutável. Reprocessar a mesma entrada produz resultado idêntico
(§7.1, NFR-02).

### 6.2 Módulo 2 — Integração com o PGD ⛔ bloqueado

**Porta a ser definida** (implementável hoje, independe do levantamento):

```python
class TipoDeclaracao(StrEnum):
    ORIGINAL = "original"
    RETIFICADORA = "retificadora"

class Ficha(StrEnum):
    IMOVEL = "imovel"                    # DIAC
    CONTRIBUINTE = "contribuinte"
    CONDOMINOS = "demais_condominos"
    UTILIZACAO = "utilizacao_do_imovel"  # DIAT, campos 01–20
    NAO_UTILIZADA = "area_nao_utilizada" # campos 21–25
    CALCULO = "calculo_do_imposto"       # campos 01–10

@dataclass(frozen=True)
class CampoPGD:
    ficha: Ficha
    numero: str          # "02", "15" — número impresso na tela
    rotulo: str          # texto do campo, para conferência em log
    valor: str

@dataclass(frozen=True)
class Pendencias:
    erros: tuple[str, ...]    # bloqueiam gravação e entrega
    avisos: tuple[str, ...]   # não bloqueiam

    @property
    def bloqueia(self) -> bool:
        return bool(self.erros)

class DriverPGD(Protocol):
    """Porta de integração. Adaptadores: importacao | banco | acessibilidade | simulado."""
    def abrir(self, exercicio: int) -> None: ...
    def gravar_backup(self) -> Path: ...
    def abrir_declaracao(self, nirf: str, tipo: TipoDeclaracao) -> None: ...
    def preencher(self, campo: CampoPGD) -> None: ...
    def ler_campo(self, ficha: Ficha, numero: str) -> str: ...
    def verificar_pendencias(self) -> Pendencias: ...
    def salvar(self) -> None: ...
    def fechar(self) -> None: ...
```

**Campos calculados pelo PGD — não preencher:** DIAT `09` (área tributável),
`11` (área aproveitável), `19` (área utilizada), `20` (GU). O sistema os **lê de
volta** e compara com a própria apuração; divergência é falha bloqueante.

**Fluxo do orquestrador:**

```
1. gravar_backup()                    → falha ⇒ aborta (NFR-05)
2. abrir_declaracao(nirf, ORIGINAL)
3. se imune_ou_isento:
       preenche apenas ficha IMOVEL, marca dispensa, encerra
4. preenche IMOVEL → CONTRIBUINTE → CONDOMINOS
                   → UTILIZACAO → NAO_UTILIZADA → CALCULO
5. lê campos 09/11/19/20 e confere contra Apuracao   → divergência ⇒ aborta
6. verificar_pendencias()
       erros  ⇒ PendenciaBloqueante, aborta, não salva
       avisos ⇒ registra e segue
7. salvar()
8. PARA. Entrega/transmissão é ato humano (§13).
```

O passo 5 é a defesa contra a falha mais perigosa do módulo: preencher campo
errado sem erro aparente. Os totais calculados pelo PGD funcionam como checksum
independente da nossa apuração.

### 6.3 Módulo 3 — DARF e arquivamento ⬜ especificado

**Sicalc** — sem certificado digital, formulário público. Ordem de tentativa para
capturar o PDF, porque o comportamento varia:

1. `page.expect_download()` — download direto
2. `context.expect_page()` + `context.request.get(url)` — abre em nova aba
3. falha ⇒ `IntervencaoManual`

**Validação obrigatória do artefato** (`pypdf`): tamanho > 2 KB **e** assinatura
`%PDF` nos 4 primeiros bytes. Um HTML de erro salvo com extensão `.pdf` é o modo
de falha mais comum e mais silencioso desta etapa.

**Nomenclatura:** `darf_itr_{nirf}_{exercicio}.pdf` · `recibo_itr_{nirf}_{exercicio}.pdf`

**e-CAC** (opcional) — exige certificado A1 e procuração ativa. Antes de qualquer
download, **validar o perfil ativo** contra o CNPJ/CPF esperado. Sem essa checagem,
o sistema baixa o recibo do contribuinte errado sem emitir erro algum.

> Certificado **A3** (token/cartão) é tecnicamente incompatível: a chave privada não
> é exportável. Se a carteira usar A3, esta subetapa permanece manual.

---

## 7. Requisitos não-funcionais

| ID | Requisito | Verificação |
|---|---|---|
| **NFR-01** | Exatidão decimal; `float` proibido em valor/área | Revisão de código + testes de invariante |
| **NFR-02** | Determinismo: mesma entrada ⇒ mesma saída, sem dependência de locale/TZ | Teste de idempotência |
| **NFR-03** | Rastreabilidade: toda apuração aponta para a linha de origem | `LinhaRejeitada.numero`; NIRF em toda saída |
| **NFR-04** | Isolamento de falha: linha inválida não derruba o lote | Teste de lote misto |
| **NFR-05** | Backup verificado antes de qualquer escrita no PGD | Pré-condição do orquestrador |
| **NFR-06** | Sem segredos em código; `.pfx` e senha via variável de ambiente | Revisão de código |
| **NFR-07** | Código de saída: `0` limpo, `1` requer revisão, `2` erro de execução | Contrato de CLI |
| **NFR-08** | Escala alvo: carteira de centenas de imóveis, processamento < 5 s | Medição |
| **NFR-09** | Mapeamento de campos do PGD concentrado em um único módulo | Restrição estrutural |

NFR-09 existe porque o PGD é substituído anualmente. Retrabalho anual é certo; o
objetivo é confiná-lo a um arquivo.

---

## 8. Modelo de erros

Hierarquia explícita — cada categoria tem tratamento distinto e **nenhuma é
tratada por retry genérico**.

| Exceção | Significado | Tratamento |
|---|---|---|
| `ValueError` | Invariante de domínio violada | Rejeita a linha, segue o lote |
| `ErroDeLinha` | Célula ilegível na planilha | Rejeita a linha, segue o lote |
| `PendenciaBloqueante` | PGD reportou *erro* | Aborta o imóvel, não salva, registra |
| `IntervencaoManual` | Captcha, 2FA, tela mudou, saída inesperada | Para e devolve o controle ao operador |
| `BackupIndisponivel` | Backup falhou ou não foi verificado | Aborta antes de qualquer escrita |
| `FalhaTransitoria` | Indisponibilidade de rede/portal | Retry com backoff exponencial |

**Regra:** `IntervencaoManual` **nunca** é reprocessada automaticamente. Retry sobre
condição que exige julgamento humano é como se produz erro em massa.

---

## 9. Estratégia de testes

| Nível | Alvo | Ferramenta | Estado |
|---|---|---|---|
| Unitário | Domínio: tabela, GU, dispensa, invariantes | pytest | ✅ 65 casos |
| Fronteira | Limites de faixa (50/200/500/1000 ha; GU 30/50/65/80) | pytest paramétrico | ✅ |
| Adaptador | Formatos numéricos BR/US, acentos, linha vazia, arquivo ausente | pytest | ✅ |
| Lote | Isolamento de falha; classificação OK/alerta/rejeitado | pytest | ✅ |
| Propriedade | Invariantes I5–I9 sob entrada aleatória | hypothesis | ⬜ F1 |
| Regressão | Declarações reais conferidas à mão viram fixture congelada | pytest | ⬜ F1 |
| Contrato | Orquestração do Módulo 2 contra `DriverSimulado` | pytest | ⬜ F2 |
| Integração | PGD e portais reais | manual assistido | ⬜ F2/F3 |

**Teste de regressão é a rede de segurança do projeto.** Cada declaração conferida
manualmente vira caso congelado. Sem isso, não há como detectar que uma mudança na
tabela ou na regra de GU alterou apuração de exercícios anteriores.

---

## 10. Observabilidade e auditoria

- Registro estruturado por imóvel: NIRF, exercício, decisão tomada, alertas emitidos.
- **Toda decisão discutível é registrada como alerta**, nunca resolvida em silêncio.
- Export CSV da apuração como trilha de conferência, com uma linha por imóvel e
  coluna de situação (`OK` · `ALERTA` · `DISPENSADO` · `REJEITADO`).
- No Módulo 2, log do par (campo, valor) efetivamente escrito — é o que permite
  auditar depois qual valor entrou em qual campo.

---

## 11. Riscos

Probabilidade × Impacto, com mitigação atribuída.

| # | Risco | P | I | Mitigação | Estado |
|---|---|---|---|---|---|
| R1 | Automação preenche campo errado sem erro | M | **Crítico** | ADR-007; leitura de volta dos campos calculados (§6.2 passo 5); conferência campo a campo na primeira declaração | Mitigado por desenho |
| R2 | Escrita direta corrompe base do PGD | M | **Crítico** | NFR-05: backup verificado como pré-condição | Mitigado |
| R3 | Tabela de alíquotas incorreta | B | **Crítico** | Ratificação pela contabilidade antes de produção | **Aberto** |
| R4 | Conceder dispensa indevida | B | **Alto** | ADR-003 + I10 | Mitigado |
| R5 | Atualização anual do PGD quebra integração | **Alta** | Médio | NFR-09; retrabalho anual orçado | Aceito |
| R6 | ADR-005 (GU com aproveitável zero) diverge do entendimento fiscal | M | Alto | Alerta obrigatório em 100% dos casos | **Aberto** |
| R7 | Recibo do contribuinte errado no e-CAC | M | **Alto** | Validação de perfil ativo antes do download | Mitigado por desenho |
| R8 | Carteira usa certificado A3 | M | Médio | Subetapa permanece manual; sem impacto nos Módulos 1 e 2 | Contingência definida |
| R9 | Nenhum dos caminhos de integração viável | B | **Alto** | Módulo 1 entrega valor de forma autônoma | Aceito |

R9 merece explicitação: **mesmo na hipótese de o Módulo 2 se mostrar inviável**, o
Módulo 1 entrega a maior parte do ganho de tempo — coleta, cálculo e conferência.
A digitação no PGD permaneceria manual, mas sobre dados já apurados e validados.

---

## 12. Plano de execução

Estimativas em dias/pessoa, indicativas, para um desenvolvedor com o contexto deste
documento.

### F0 — Ratificação normativa `sem dependência técnica`
| Item | Resp. | Est. |
|---|---|---|
| Conferir os 25 valores da tabela contra o Anexo da Lei 9.393/96 | Contabilidade | 0,5 |
| Ratificar ou substituir ADR-005 | Contabilidade | 0,5 |
| Confirmar regra de dispensa e opção A/B do PGD | Contabilidade | 0,5 |

**Aceite:** marcações `ATENCAO`/`CONFIRA` removidas do código-fonte.
**Bloqueia:** uso em cliente real. Não bloqueia desenvolvimento.

### F1 — Consolidação do Módulo 1 `parcialmente entregue`
| Item | Est. |
|---|---|
| ✅ Domínio, adaptador de planilha, relatório, 65 testes | — |
| Testes de propriedade (hypothesis) sobre I5–I9 | 1 |
| Suíte de regressão com declarações reais conferidas | 1 |
| `dados/vtn_2026.csv` — 12 municípios | 0,5 |
| Comparativo com exercício anterior (variação de VTN e área) | 1,5 |

**Aceite:** carteira real processada; divergência zero contra conferência manual de
5 imóveis.

### F2 — Integração com o PGD `bloqueado`
| Item | Est. |
|---|---|
| Levantamento Q3–Q5 na máquina alvo | 0,5 |
| Decisão do adaptador; ADR-004 fechado | 0,5 |
| `DriverPGD` + `DriverSimulado` + testes de contrato | 2 |
| Orquestrador com backup, conferência de checksum e política de pendência | 2 |
| Adaptador real — **A** ~2 · **B** ~5 · **C** ~15 | 2–15 |
| Conferência campo a campo da primeira declaração gerada | 1 |

**Aceite:** declaração gerada pela automação idêntica, campo a campo, à mesma
declaração preenchida manualmente.

### F3 — DARF e arquivamento `não bloqueado`
| Item | Est. |
|---|---|
| Adaptador Sicalc com as três estratégias de captura | 2 |
| Validação de artefato PDF e arquivamento nomeado | 0,5 |
| e-CAC com A1, validação de perfil e download de recibo *(opcional)* | 3 |

**Aceite:** DARF emitido e validado para uma amostra da carteira, sem intervenção.

---

## 13. Fora de escopo

Exclusões **deliberadas**. Nenhuma decorre de limitação técnica.

| Excluído | Fundamento |
|---|---|
| **Transmissão da declaração** | Ato do responsável técnico sob procuração eletrônica. A automação encerra na tela anterior. |
| **Pagamento do DARF** | Emissão de guia é instrumentação; pagamento é movimentação financeira. |
| **Resolução automática de pendência bloqueante** | Erro do PGD indica inconsistência de dado. Resolver automaticamente é mascarar. |
| **Contorno de captcha ou segundo fator** | Vedado. O processo para e devolve o controle. |
| **OCR dos laudos de VTN** | ADR-008. |
| **Automação do Domínio Folha** | Projeto distinto, observado em `PC Manoel 2.mp4`. Sem interseção de domínio. |

---

## 14. Premissas e questões abertas

### Premissas
- **P1.** A carteira opera em municípios de Goiás; região de pequena gleba = `demais` (30 ha).
- **P2.** VTN aplicado com taxa única, sem segregação por aptidão agrícola.
- **P3.** Declaração do exercício corrente é **Original**; importação do ano anterior serve apenas ao cadastro.
- **P4.** Um único operador por vez; sem concorrência sobre a base do PGD.

### Questões abertas

| # | Questão | Bloqueia | Resp. |
|---|---|---|---|
| **Q1** | Os 25 valores da tabela conferem com o texto legal vigente? | Produção | Contabilidade |
| **Q2** | GU com área aproveitável zero: 100% está correto? | Produção | Contabilidade |
| **Q3** | Caminho e conteúdo da pasta de instalação do PGD? | F2 | TI |
| **Q4** | Formato de armazenamento de uma declaração gravada? | F2 | TI |
| **Q5** | `Importar Dados ITR` aceita arquivo externo? | F2 | TI |
| **Q6** | Certificado da carteira é A1 ou A3? | F3 (e-CAC) | Escritório |

Comando de levantamento para Q3, na máquina alvo:

```powershell
Get-ChildItem "C:\Arquivos de Programas\Programas RFB" -Recurse -Depth 3 |
  Select-Object FullName, Length | Format-Table -AutoSize
```

---

## 15. Definition of Done

Uma entrega só é considerada concluída quando:

1. Testes automatizados cobrem o caminho feliz **e** os modos de falha previstos.
2. Nenhuma decisão discutível é tomada em silêncio — há alerta ou exceção.
3. Erros carregam contexto acionável: identificação do imóvel, campo e valor recebido.
4. A documentação de escopo reflete o estado real, incluindo ADRs revisados.
5. Nenhum segredo em código-fonte ou em arquivo versionado.
6. O comportamento foi conferido contra a apuração manual em amostra representativa.

---

*O responsável técnico permanece integralmente responsável pela declaração
transmitida. Este sistema instrumenta e confere; não assina.*
