from decimal import Decimal

import pytest

from itr import (
    AreasNaoTributaveis,
    AreasUtilizadas,
    ImovelRural,
    Regiao,
    aliquota,
    apurar,
)


def imovel(**kwargs):
    base = dict(nirf="1234567-8", exercicio=2026, area_total="1000", vtn="1000000")
    base.update(kwargs)
    return ImovelRural(**base)


class TestTabelaAliquotas:
    @pytest.mark.parametrize(
        "area,gu,esperado",
        [
            ("50", "90", "0.03"),
            ("50", "80", "0.20"),  # limite: 80 nao e "> 80"
            ("50", "30", "1.00"),
            ("200", "81", "0.07"),
            ("500", "66", "0.60"),
            ("1000", "51", "1.90"),
            ("1000.01", "10", "20.00"),
            ("5000", "100", "0.45"),
        ],
    )
    def test_pontos_da_tabela(self, area, gu, esperado):
        assert aliquota(Decimal(area), Decimal(gu)) == Decimal(esperado)

    def test_limites_de_faixa_de_area_sao_inclusivos(self):
        assert aliquota(Decimal("50"), Decimal("90")) == Decimal("0.03")
        assert aliquota(Decimal("50.01"), Decimal("90")) == Decimal("0.07")

    def test_area_invalida(self):
        with pytest.raises(ValueError):
            aliquota(Decimal("0"), Decimal("90"))


class TestGrauUtilizacao:
    def test_gu_proporcional(self):
        r = apurar(
            imovel(
                area_total="1000",
                utilizadas=AreasUtilizadas(pastagens="400"),
            )
        )
        assert r.area_aproveitavel == Decimal("1000")
        assert r.grau_utilizacao == Decimal("40.0000")
        assert r.aliquota == Decimal("3.30")  # 1000 ha, faixa 30 < GU <= 50

    def test_benfeitorias_saem_da_aproveitavel_mas_nao_da_tributavel(self):
        r = apurar(
            imovel(
                area_total="1000",
                area_benfeitorias="200",
                utilizadas=AreasUtilizadas(produtos_vegetais="400"),
            )
        )
        assert r.area_tributavel == Decimal("1000")
        assert r.area_aproveitavel == Decimal("800")
        assert r.grau_utilizacao == Decimal("50.0000")

    def test_utilizada_maior_que_aproveitavel_limita_e_alerta(self):
        r = apurar(
            imovel(
                area_total="100",
                utilizadas=AreasUtilizadas(pastagens="150"),
            )
        )
        assert r.grau_utilizacao == Decimal("100")
        assert any("maior que a aproveitavel" in a for a in r.alertas)

    def test_aproveitavel_zero_alerta(self):
        r = apurar(
            imovel(
                area_total="100",
                nao_tributaveis=AreasNaoTributaveis(reserva_legal="100"),
            )
        )
        assert r.area_aproveitavel == Decimal("0")
        assert r.grau_utilizacao == Decimal("100")
        assert any("zero" in a for a in r.alertas)


class TestImposto:
    def test_vtn_tributavel_proporcional_a_area_tributavel(self):
        r = apurar(
            imovel(
                area_total="1000",
                vtn="2000000",
                nao_tributaveis=AreasNaoTributaveis(reserva_legal="200"),
                utilizadas=AreasUtilizadas(pastagens="800"),
            )
        )
        assert r.area_tributavel == Decimal("800")
        assert r.vtn_tributavel == Decimal("1600000.00")
        assert r.grau_utilizacao == Decimal("100.0000")
        assert r.aliquota == Decimal("0.15")
        assert r.imposto_devido == Decimal("2400.00")

    def test_imposto_minimo_de_dez_reais(self):
        r = apurar(
            imovel(
                area_total="40",
                vtn="10000",
                utilizadas=AreasUtilizadas(pastagens="40"),
                possui_outro_imovel_rural=True,
            )
        )
        # 10000 * 0.03% = R$ 3,00 -> elevado ao minimo
        assert r.imposto_devido == Decimal("10.00")
        assert any("minimo" in a for a in r.alertas)


class TestDispensa:
    def test_pequena_gleba_explorada_pelo_proprietario_e_imune(self):
        r = apurar(
            imovel(
                area_total="28",
                regiao=Regiao.DEMAIS,
                explora_so_ou_com_familia=True,
                possui_outro_imovel_rural=False,
            )
        )
        assert r.dispensado
        assert r.imposto_devido == Decimal("0.00")
        assert "Imune" in r.motivo_dispensa

    def test_pequena_gleba_com_outro_imovel_nao_e_imune(self):
        r = apurar(
            imovel(
                area_total="28",
                explora_so_ou_com_familia=True,
                possui_outro_imovel_rural=True,
            )
        )
        assert not r.dispensado

    def test_limite_de_gleba_varia_por_regiao(self):
        comum = dict(
            area_total="80", explora_so_ou_com_familia=True, possui_outro_imovel_rural=False
        )
        assert apurar(imovel(regiao=Regiao.AMAZONIA_OCIDENTAL_PANTANAL, **comum)).dispensado
        assert not apurar(imovel(regiao=Regiao.DEMAIS, **comum)).dispensado

    def test_assentamento_e_isento(self):
        r = apurar(imovel(area_total="5000", imovel_de_assentamento=True))
        assert r.dispensado
        assert "Isento" in r.motivo_dispensa


class TestValidacao:
    def test_areas_nao_tributaveis_maiores_que_o_total(self):
        with pytest.raises(ValueError, match="excedem a area total"):
            imovel(
                area_total="100",
                nao_tributaveis=AreasNaoTributaveis(reserva_legal="60", rppn="60"),
            )

    def test_area_total_zero(self):
        with pytest.raises(ValueError, match="positiva"):
            imovel(area_total="0")

    def test_vtn_negativo(self):
        with pytest.raises(ValueError, match="negativo"):
            imovel(vtn="-1")

    def test_nao_tributaveis_mais_benfeitorias_excedem_total(self):
        with pytest.raises(ValueError, match="benfeitorias excedem"):
            imovel(
                area_total="100",
                nao_tributaveis=AreasNaoTributaveis(reserva_legal="80"),
                area_benfeitorias="30",
            )


class TestValoresDoPGD:
    """Derivacao do VTN como na ficha 'Calculo do Imposto' do PGD."""

    def test_vtn_derivado_dos_campos_01_02_03(self):
        i = ImovelRural.com_valores(
            nirf="1234567-8",
            exercicio=2026,
            area_total="100",
            valor_total_imovel="1000000",
            valor_construcoes_benfeitorias="150000",
            valor_culturas_pastagens_florestas="50000",
        )
        assert i.vtn == Decimal("800000")

    def test_vtn_negativo_e_recusado(self):
        with pytest.raises(ValueError, match="VTN negativo"):
            ImovelRural.com_valores(
                nirf="1", exercicio=2026, area_total="100",
                valor_total_imovel="100000",
                valor_construcoes_benfeitorias="200000",
            )

    def test_area_utilizada_soma_campos_12_a_18(self):
        u = AreasUtilizadas(
            produtos_vegetais="10", descanso="5", reflorestamento="5",
            pastagens="20", exploracao_extrativa="3",
            atividade_granjeira_aquicola="2", frustracao_safra="5",
        )
        assert u.total == Decimal("50")
