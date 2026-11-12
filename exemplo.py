"""Exemplo de uso do motor de apuracao."""

from itr import AreasNaoTributaveis, AreasUtilizadas, ImovelRural, Regiao, apurar

fazenda = ImovelRural(
    nirf="1234567-8",
    exercicio=2026,
    area_total="1200",
    vtn="4800000",
    regiao=Regiao.DEMAIS,
    nao_tributaveis=AreasNaoTributaveis(
        reserva_legal="240",
        preservacao_permanente="60",
    ),
    area_benfeitorias="20",
    utilizadas=AreasUtilizadas(pastagens="500", produtos_vegetais="300"),
)

resultado = apurar(fazenda)
print(resultado.resumo())
print(f"  area tributavel:  {resultado.area_tributavel} ha")
print(f"  area aproveitavel:{resultado.area_aproveitavel} ha")
for alerta in resultado.alertas:
    print(f"  [!] {alerta}")
