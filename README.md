# Motor de Apuração do ITR

Biblioteca em Python puro que apura o ITR (Lei 9.393/96) de imóveis rurais a partir de uma planilha, com validações e alertas para os casos ambíguos.

![Python](https://img.shields.io/badge/Python-3.12-3776AB) ![pytest](https://img.shields.io/badge/pytest-testes-0A9EDC) ![Decimal](https://img.shields.io/badge/Decimal-sem%20float-555555) ![status](https://img.shields.io/badge/status-Em%20evolu%C3%A7%C3%A3o-blueviolet) ![licença](https://img.shields.io/badge/licen%C3%A7a-propriet%C3%A1ria-lightgrey)

> Projeto real. Este repositório é uma **cópia de portfólio**: segredos, servidores e nomes de empresas foram removidos ou trocados pelo nome fictício "Natela".

## Sumário

1. [O que o projeto faz](#1-o-que-o-projeto-faz)
2. [Instalação e requisitos](#2-instalação-e-requisitos)
3. [Como rodar e usar](#3-como-rodar-e-usar)
4. [Demo visual](#4-demo-visual)
5. [Suporte e ajuda](#5-suporte-e-ajuda)
6. [Contribuição e manutenção](#6-contribuição-e-manutenção)
7. [Licença e status](#7-licença-e-status)

## 1. O que o projeto faz

**O que resolve:** Escritórios que declaram o ITR de muitos imóveis calculam área tributável, grau de utilização e imposto em planilhas frágeis, sem aviso quando um caso foge da regra.

**Como resolve:** Um motor de cálculo testado que recebe os dados do imóvel, aplica a tabela de alíquotas da lei e devolve o imposto, um resumo e alertas — sem depender do portal, do certificado ou do layout da Receita.

**Para quem é:** Escritórios de contabilidade e consultores rurais que declaram ITR em volume.

**Por que importa:** Cálculo reproduzível e auditável, que avisa em vez de decidir sozinho quando a lei permite mais de uma leitura.

### Principais benefícios

| Cálculo testado | Alertas nos casos ambíguos | Planilha de entrada e relatório |
|---|---|---|

### Funcionalidades

- Área tributável, área aproveitável e grau de utilização
- Tabela de alíquotas do Anexo da Lei 9.393/96 (área × GU)
- VTN tributável proporcional à área tributável e imposto mínimo de R$ 10,00
- Imunidade de pequena gleba por região e isenção de assentamento
- Validações de consistência das áreas na entrada
- Leitura de planilha modelo e geração de relatório (`processar.py`)

## 2. Instalação e requisitos

### Pré-requisitos

| Ferramenta | Versão |
|---|---|
| Python | 3.12 |
| openpyxl | para planilhas |
| pytest | para os testes |

### Instalação

```bash
git clone https://github.com/jhonatancamargo121/motor-apuracao-itr.git
cd motor-apuracao-itr
pip install openpyxl pytest
```

Não há variáveis de ambiente: tudo entra pelos objetos Python ou pela planilha modelo (`python criar_modelo.py`).

### Variáveis de ambiente

| Variável | Para que serve |
|---|---|
| `ImovelRural` | Dados do imóvel: NIRF, exercício, área total, VTN |
| `AreasNaoTributaveis` | Reserva legal, APP etc. |
| `AreasUtilizadas` | Pastagens, lavoura etc. |
| `Regiao` | Define o limite de pequena gleba |

A lista completa, com comentários, está no `.env.example`. Nenhum valor real é versionado.

## 3. Como rodar e usar

### Quick start

```bash
python -m pytest tests/ -q
python exemplo.py
```

### Exemplo de uso

Requisição:

```bash
python -c "from itr import ImovelRural, AreasNaoTributaveis, AreasUtilizadas, apurar; r = apurar(ImovelRural(nirf='1234567-8', exercicio=2026, area_total='1200', vtn='4800000', nao_tributaveis=AreasNaoTributaveis(reserva_legal='240'), utilizadas=AreasUtilizadas(pastagens='800'))); print(r.resumo())"
```

Resposta esperada:

```text
Resumo da apuração: área tributável, grau de utilização, alíquota, VTN tributável e imposto devido, além da lista de alertas.
```

## 4. Demo visual

Fluxo principal:

```mermaid
flowchart LR
  E[Planilha ou objetos Python] --> V[Validação das áreas]
  V --> A[Área tributável e GU]
  A --> T[Tabela de alíquotas]
  T --> I[Imposto + alertas]
  I --> R[Relatório]
```

> Prints e GIF com dados fictícios estão no roadmap. Para ver o sistema rodando, siga o [Quick start](#3-como-rodar-e-usar).

## 5. Suporte e ajuda

- **Documentação:**
  - [Uso e escopo](docs/DETALHES.md)
  - [Escopo técnico](ESCOPO_TECNICO.md)
  - [Plano](PLANO_ITR.md)
- **Issues:** abra uma [issue](https://github.com/jhonatancamargo121/motor-apuracao-itr/issues) para reportar problemas ou sugerir melhorias.
- **Discussions:** dúvidas gerais em [Discussions](https://github.com/jhonatancamargo121/motor-apuracao-itr/discussions).
- **Contato:** pelo perfil [@jhonatancamargo121](https://github.com/jhonatancamargo121)

## 6. Contribuição e manutenção

### Como contribuir

1. Faça um **fork** do repositório
2. Crie uma **branch** a partir da `main` (`git checkout -b feat/minha-melhoria`)
3. Abra um **Pull Request** descrevendo o que mudou e por quê

### Padrões

- Commits no padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/) (`feat:`, `fix:`, `docs:`…)
- Lint e formatação passando antes do PR
- Testes rodando antes do PR

### Como rodar os testes

```bash
python -m pytest tests/ -q
```

### Mantenedores

| | |
|---|---|
| **Jhonatan Camargo** ([@jhonatancamargo121](https://github.com/jhonatancamargo121)) | Mantenedor |

## 7. Licença e status

### Licença

Código proprietário, publicado para fins de portfólio. Todos os direitos reservados; veja o arquivo [LICENSE](LICENSE).

### Status

![status](https://img.shields.io/badge/status-Em%20evolu%C3%A7%C3%A3o-blueviolet)

### Próximos passos

- [ ] Conferir a tabela de alíquotas contra a IN vigente
- [ ] Exportar no formato de importação do PGD
