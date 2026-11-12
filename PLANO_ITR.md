# Plano de execução — Automação do ITR (PC Manoel.mp4)

Escopo: automatizar o processo do vídeo `PC Manoel.mp4` — declaração do ITR no
PGD ITR (Java desktop). **Não** cobre o `PC Manoel 2.mp4` (Domínio Folha), que é
outro projeto.

Última atualização: 11/08/2026

---

## 1. Situação atual

**Pronto e testado** (27 testes passando):

| Componente | Arquivo | Estado |
|---|---|---|
| Modelo do imóvel e áreas | `itr/modelo.py` | ✅ campos 01–25 do PGD |
| Tabela de alíquotas | `itr/tabela.py` | ⚠️ conferir contra a lei |
| Apuração (GU, VTN, imposto) | `itr/calculo.py` | ⚠️ 1 regra a confirmar |
| Testes | `tests/test_calculo.py` | ✅ 27 passando |

**Não existe ainda:** importação de planilha, preenchimento do PGD, emissão de
DARF, arquivamento de recibo.

**Ambiente:** o PGD ITR **não está instalado** na máquina onde o código está
sendo desenvolvido. Está no PC do Manoel. Isso bloqueia as fases 2 e 3.

---

## 2. O fluxo real, como observado no vídeo

Sequência de fichas no PGD ITR 2025 v1.7:

```
Abrir PGD
  └─ Nova Declaração  ou  Importar Dados ITR <ano-1>
       ├─ 1. Imóvel (DIAC)
       ├─ 2. Contribuinte
       ├─ 3. Demais Condôminos
       ├─ 4. Utilização do Imóvel (DIAT)      ← campos 01–20
       ├─ 5. Área Não Utilizada               ← campos 21–25
       ├─ 6. Cálculo do Imposto               ← campos 01–10
       ├─ 7. Verificar Pendências             ← erros vs avisos
       └─ 8. Entregar Declaração              ← grava + transmite (passo único)
```

### Ficha 1 — Imóvel (DIAC)

| Campo | Origem |
|---|---|
| Declaração Original / Retificadora | regra de negócio (ver §3.1) |
| Nº do recibo do exercício anterior | só se Retificadora |
| Nome do imóvel rural | cadastro |
| Área total do imóvel (ha) | cadastro |
| Código do imóvel Incra (NIRF/CIB) | cadastro |
| Tipo logradouro / Logradouro / Distrito | cadastro |
| UF / Município / CEP | cadastro |
| Contribuinte é PF ou PJ | cadastro |
| Pertence a condomínio? | cadastro |
| **Imóvel imune ou isento do ITR?** | calculado — ver §3.2 |

### Ficha 4 — Utilização do Imóvel (DIAT)

Campos **calculados pelo próprio PGD** (não preencher): `09 ÁREA TRIBUTÁVEL`,
`11 ÁREA APROVEITÁVEL`, `19 ÁREA UTILIZADA`, `20 GRAU DE UTILIZAÇÃO`.

| Nº | Campo | Atributo no `ImovelRural` |
|---|---|---|
| 01 | Área total do imóvel | `area_total` |
| 02 | Área de preservação permanente | `nao_tributaveis.preservacao_permanente` |
| 03 | Área de reserva legal | `nao_tributaveis.reserva_legal` |
| 04 | Área de RPPN | `nao_tributaveis.rppn` |
| 05 | Área de interesse ecológico | `nao_tributaveis.interesse_ecologico` |
| 06 | Área de servidão ambiental | `nao_tributaveis.servidao_ambiental` |
| 07 | Área coberta por florestas nativas | `nao_tributaveis.coberta_floresta_nativa` |
| 08 | Área alagada de reservatório | `nao_tributaveis.alagada_reservatorio` |
| 10 | Área com benfeitorias úteis/necessárias | `area_benfeitorias` |
| 12 | Área de produtos vegetais | `utilizadas.produtos_vegetais` |
| 13 | Área em descanso | `utilizadas.descanso` |
| 14 | Área de reflorestamento | `utilizadas.reflorestamento` |
| 15 | Área de pastagem | `utilizadas.pastagens` |
| 16 | Área de exploração extrativa | `utilizadas.exploracao_extrativa` |
| 17 | Área de atividade granjeira ou aquícola | `utilizadas.atividade_granjeira_aquicola` |
| 18 | Área de frustração de safra | `utilizadas.frustracao_safra` |
| — | Nº do recibo do ADA/Ibama | cadastro (opcional) |
| — | Nº do CAR | cadastro (gera aviso se ausente) |

### Ficha 6 — Cálculo do Imposto

```
01 Valor total do imóvel
02 (−) Construções, instalações e benfeitorias
03 (−) Culturas, pastagens cultivadas e melhoradas e florestas plantadas
04 (=) VALOR DA TERRA NUA          ← ImovelRural.com_valores()
05 VALOR DA TERRA NUA TRIBUTÁVEL   ← calculado
06 ALÍQUOTA (%)                    ← calculado
07 IMPOSTO CALCULADO               ← calculado
08 IMPOSTO DEVIDO                  ← calculado (mínimo R$ 10,00)
09 Quantidade de quotas
10 Valor da quota
```

### Ficha 7 — Verificar Pendências

Distinção que a automação **precisa** respeitar:

- 🔴 **Erro** — impede a gravação e a entrega. Aborta o processo.
- 🟡 **Aviso** — não impede. Registra e segue.

No vídeo: 5 erros e 6 avisos numa declaração parcialmente preenchida.

---

## 3. Regras de negócio confirmadas com o Manoel (áudio)

### 3.1 Original, não retificadora
A declaração do exercício corrente é **Original**. Importar o ano anterior serve
só para trazer o cadastro e poupar digitação — não transforma em retificadora.

### 3.2 Imune / isento
Se o imóvel tem **menos de 30 ha** e é o **único imóvel do proprietário**, marca-se
"Imóvel imune ou isento do ITR? **Sim**", opção **A** (a opção A/B é por região; a
região do escritório é a **A**). O PGD então **desabilita** os campos de VTN e
apuração. Ou seja: nesse caso a automação **não** preenche as fichas 4, 5 e 6.

### 3.3 VTN com taxa única
Não se divide o VTN por aptidão agrícola (lavoura boa/regular/restrita). Usa-se
uma **taxa única**. Na prática, os imóveis do Manoel lançam apenas **pastagem** e
**preservação**.

### 3.4 Sobra de área
O que sobra da área total, sem uso declarado, entra como **terra não utilizável**
(ficha "Área Não Utilizada", campos 21–25).

### 3.5 Condomínio
Não muda a regra de cálculo. A única distinção relevante continua sendo a de §3.2.

---

## 4. Fonte de VTN — laudos técnicos

Os VTNs vêm de laudo técnico por município (IN RFB 1877/2019), com tabela de
valores por hectare e por aptidão.

**Municípios do escritório** (12): Campinaçu, Santa Rosa de Goiás, Crixás,
Itapaci, Jaraguá, São Francisco de Goiás, Inhumas, Trombas, Pirenópolis, Vila
Propício, Trindade, Petrolina de Goiás — todos GO.

**Disponível hoje:** apenas Petrolina de Goiás (2026).

| Aptidão | VTN 2026 (R$/ha) |
|---|---|
| Lavoura aptidão boa | 34.450,00 |
| Lavoura aptidão regular | 31.500,00 |
| Lavoura aptidão restrita | 25.320,00 |
| Pastagem plantada | 29.490,00 |
| Silvicultura ou pastagem natural | 21.220,00 |
| Preservação a fauna e flora | 18.530,00 |

⚠️ Os laudos são **PDF escaneado, sem camada de texto**. Extração automática
exigiria OCR com conferência manual — não vale a pena para 12 municípios/ano.
**Decisão: tabela de VTN mantida à mão** em `dados/vtn_<ano>.csv`, com o laudo
arquivado ao lado como comprovante.

---

## 5. O que ainda não sabemos (bloqueia decisão de arquitetura)

Estes três pontos precisam ser levantados **no PC do Manoel** antes de escrever
qualquer código de automação do PGD:

- [ ] **B1.** Caminho da pasta do PGD e conteúdo dela
      (`Arquivos de Programas\Programas RFB\ITR2025` ou similar).
      Interessa: extensão e formato dos arquivos de declaração.
- [ ] **B2.** Formato de armazenamento de uma declaração já gravada.
      É banco embarcado (HSQLDB/Derby/Firebird)? Arquivo próprio?
- [ ] **B3.** Em `Declaração > Importar Dados ITR 2024`: aceita **arquivo
      externo** ou só lê a instalação do ano anterior na mesma máquina?

Como levantar (rodar no PC do Manoel, PowerShell):

```powershell
Get-ChildItem "C:\Arquivos de Programas\Programas RFB" -Recurse -Depth 2 | Select FullName, Length
```

---

## 6. Caminhos de automação do PGD — decisão

Escolha depende de B1–B3. Ordem de preferência:

| # | Caminho | Prós | Contras | Quando escolher |
|---|---|---|---|---|
| **A** | Arquivo de importação | Oficial, estável, rápido | Só se existir layout | B3 = aceita arquivo |
| **B** | Banco local do PGD | Muito rápido, sem GUI | **Não suportado**; update quebra; risco de corromper base | B2 = formato legível **e** com backup obrigatório |
| **C** | Java Access Bridge (`pyjab`) | Acessa componentes Swing de verdade, não clique cego | Trabalhoso; lento; quebra a cada versão do PGD | fallback se A e B falharem |
| **D** | `pyautogui` por coordenada | Trivial de começar | Quebra com resolução, tema, scroll. **Preenche campo errado em silêncio** | ❌ não usar |

> `pywinauto` com backend `uia` **não funciona** aqui: Swing não expõe controles
> ao UI Automation do Windows. É por isso que o caminho C passa pelo Access Bridge.

**Regra de ouro para B e C:** antes de qualquer escrita, `Ferramentas > Gravar
Cópia de Segurança`. Sem backup verificado, não roda.

---

## 7. Fases de execução

### Fase 0 — Validação jurídica ⬅️ **fazer primeiro, não depende de nada**

- [ ] Conferir os 25 valores da tabela em `itr/tabela.py` contra o Anexo da Lei 9.393/96
- [ ] Decidir o tratamento de GU quando área aproveitável = 0 (hoje: 100%, com alerta)
- [ ] Confirmar com o Manoel a regra §3.2 (opção A/B e o que o PGD desabilita)

**Pronto quando:** as duas marcações `ATENCAO`/`CONFIRA` saírem do código.

### Fase 1 — Entrada de dados e conferência

- [ ] `itr/planilha.py` — lê a planilha de imóveis → `ImovelRural`
- [ ] `dados/vtn_2026.csv` — VTN por município e aptidão, preenchido à mão
- [ ] `itr/relatorio.py` — roda `apurar()` em lote e emite três listas:
      **OK** · **com alertas** · **rejeitados** (`ValueError`)
- [ ] Comparativo com o exercício anterior (variação de VTN e de área)

**Pronto quando:** rodar a carteira inteira e o resultado bater com o que o
Manoel apurou à mão em pelo menos 5 imóveis conferidos um a um.

**Bloqueia?** Não. Pode começar hoje. Falta só o cabeçalho de uma planilha real.

### Fase 2 — Preenchimento do PGD

- [ ] Resolver B1, B2, B3
- [ ] Escolher o caminho (§6) e registrar a decisão aqui
- [ ] Rotina de backup obrigatório antes de qualquer escrita
- [ ] Preenchimento das fichas 1 a 6
- [ ] Ler `Verificar Pendências` e classificar erro × aviso
- [ ] Parar e devolver controle se houver **erro**

**Pronto quando:** uma declaração completa for gerada pela automação e conferida
campo a campo contra a mesma declaração feita à mão.

**Bloqueia?** Sim — depende de B1–B3.

### Fase 3 — DARF e arquivamento

- [ ] Emissão de DARF via Sicalc (Playwright — **não exige certificado**)
- [ ] Validação do PDF baixado (`%PDF` nos 4 primeiros bytes, tamanho > 2 KB)
- [ ] Arquivamento: `recibo_itr_{nirf}_{exercicio}.pdf`
- [ ] (Opcional) Download de recibos no e-CAC — exige A1 + procuração + troca de perfil

**Bloqueia?** Não. Independente das fases 1 e 2.

---

## 8. Passos que continuam humanos

Não automatizar, em nenhuma fase:

- **Transmissão da declaração** — é ato do contador, com procuração eletrônica
- **Pagamento do DARF** — emitir a guia é automação; pagar não
- **Resolução de erro em Verificar Pendências** — a automação para e avisa
- **Captcha ou 2FA**, se aparecer em qualquer portal — para e devolve o controle

---

## 9. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Automação preenche campo errado sem erro | **Alto** — declaração incorreta transmitida | Conferência campo a campo na Fase 2; nunca usar caminho D |
| Escrita direta na base corrompe declaração | **Alto** | Backup obrigatório antes de cada execução |
| Atualização anual do PGD quebra tudo | Médio | Concentrar seletores/campos num módulo só; prever retrabalho todo ano |
| Tabela de alíquotas errada | **Alto** | Fase 0 |
| Laudo de VTN desatualizado | Médio | Data do laudo registrada junto do valor no CSV |
| Perfil/cliente trocado no e-CAC | **Alto** — recibo de outro contribuinte | Validar perfil ativo antes de baixar |

---

## 10. Próximo passo imediato

Duas coisas em paralelo, nenhuma bloqueada:

1. **Fase 0** — conferir a tabela de alíquotas. É rápido e destrava a confiança
   no motor inteiro.
2. **Cabeçalho de uma planilha real** de imóveis (pode ter dados fictícios) →
   destrava a Fase 1 inteira.

E, quando houver acesso ao PC do Manoel, o levantamento B1–B3 (§5) para decidir
a arquitetura da Fase 2.
