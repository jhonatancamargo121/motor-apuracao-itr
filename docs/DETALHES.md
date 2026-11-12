# Automação ITR

Motor de apuração do ITR (Lei 9.393/96) em Python puro — sem dependência de
portal, certificado digital ou layout da Receita.

## Uso

```bash
python -m pytest tests/ -q
python exemplo.py
```

```python
from itr import ImovelRural, AreasNaoTributaveis, AreasUtilizadas, Regiao, apurar

r = apurar(ImovelRural(
    nirf="1234567-8", exercicio=2026,
    area_total="1200", vtn="4800000",
    nao_tributaveis=AreasNaoTributaveis(reserva_legal="240"),
    utilizadas=AreasUtilizadas(pastagens="800"),
))
print(r.resumo(), r.alertas)
```

## O que já está implementado

- Área tributável, área aproveitável e grau de utilização
- Tabela de alíquotas do Anexo da Lei 9.393/96 (área × GU)
- VTN tributável proporcional à área tributável
- Imposto mínimo de R$ 10,00
- Imunidade de pequena gleba (limite por região) e isenção de assentamento
- Validações de consistência de áreas (erro na entrada, não na transmissão)
- Alertas para os casos ambíguos, em vez de decidir silenciosamente

## Conferir antes de usar em produção

Dois pontos foram implementados a partir do texto da lei e **precisam de
conferência** contra a legislação e a IN vigentes:

1. **Valores da tabela de alíquotas** (`itr/tabela.py`) — estáveis há anos, mas
   confira uma vez.
2. **GU quando a área aproveitável é zero** (`itr/calculo.py`) — implementado
   como GU de 100%. É o ponto de maior divergência de interpretação; o código
   emite alerta sempre que cai nesse caso.

## Escopo

Este módulo apura. Ele **não** preenche DIAC/DIAT nem transmite — o PGD ITR é
aplicação Java desktop e a transmissão é do Receitanet.

Próximas camadas previstas:

- Importação de planilhas de clientes → `ImovelRural`
- Relatório de conferência com comparativo do exercício anterior
- Emissão de DARF via Sicalc (Playwright) — não exige certificado
- Download de recibos no e-CAC (Playwright + certificado A1 + procuração)

Pagamento do DARF e transmissão da declaração são passos humanos.
