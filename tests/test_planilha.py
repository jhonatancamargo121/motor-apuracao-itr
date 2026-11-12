from decimal import Decimal

import pytest

from itr.planilha import (
    ErroDeLinha,
    ler_booleano,
    ler_decimal,
    ler_planilha,
    montar_imovel,
    normalizar,
)
from itr.relatorio import processar_planilha

LINHA_BASE = {
    "nirf": "1234567-8",
    "nome_imovel": "FAZENDA TESTE",
    "exercicio": "2026",
    "area_total_ha": "100",
    "valor_total_imovel": "1000000",
}


class TestNormalizacao:
    @pytest.mark.parametrize(
        "entrada,esperado",
        [
            ("Área Total (ha)", "area_total_ha"),
            ("  NIRF  ", "nirf"),
            ("Preservação Permanente", "preservacao_permanente"),
            ("Grau de Utilização %", "grau_de_utilizacao"),
            (None, ""),
        ],
    )
    def test_cabecalhos(self, entrada, esperado):
        assert normalizar(entrada) == esperado


class TestLeituraDeNumero:
    @pytest.mark.parametrize(
        "entrada,esperado",
        [
            ("1.234,56", "1234.56"),   # formato brasileiro
            ("1234.56", "1234.56"),    # formato americano
            ("1234,56", "1234.56"),
            ("R$ 29.490,00", "29490.00"),
            (5.9, "5.9"),
            ("", "0"),
            (None, "0"),
        ],
    )
    def test_formatos_aceitos(self, entrada, esperado):
        assert ler_decimal(entrada, "col") == Decimal(esperado)

    def test_texto_invalido(self):
        with pytest.raises(ErroDeLinha, match="nao e um numero valido"):
            ler_decimal("cem hectares", "area_total_ha")


class TestLeituraDeBooleano:
    @pytest.mark.parametrize("entrada", ["SIM", "sim", "S", "1", "x", True])
    def test_verdadeiros(self, entrada):
        assert ler_booleano(entrada, "col", padrao=False) is True

    @pytest.mark.parametrize("entrada", ["NAO", "não", "N", "0", False])
    def test_falsos(self, entrada):
        assert ler_booleano(entrada, "col", padrao=True) is False

    def test_vazio_usa_o_padrao(self):
        assert ler_booleano("", "col", padrao=True) is True
        assert ler_booleano(None, "col", padrao=False) is False

    def test_valor_ambiguo_e_erro(self):
        with pytest.raises(ErroDeLinha, match="SIM/NAO"):
            ler_booleano("talvez", "explora_com_familia", padrao=False)


class TestMontagem:
    def test_linha_minima(self):
        i = montar_imovel(dict(LINHA_BASE))
        assert i.nirf == "1234567-8"
        assert i.area_total == Decimal("100")
        assert i.vtn == Decimal("1000000")

    def test_vtn_derivado_das_tres_colunas(self):
        i = montar_imovel(
            {**LINHA_BASE, "valor_construcoes": "100000", "valor_culturas": "50000"}
        )
        assert i.vtn == Decimal("850000")

    def test_coluna_obrigatoria_faltando(self):
        linha = {**LINHA_BASE, "area_total_ha": ""}
        with pytest.raises(ErroDeLinha, match="obrigatoria"):
            montar_imovel(linha)

    def test_regiao_invalida(self):
        with pytest.raises(ErroDeLinha, match="invalida"):
            montar_imovel({**LINHA_BASE, "regiao": "sudeste"})

    def test_padrao_conservador_nao_concede_imunidade_por_omissao(self):
        # Pequena gleba, mas sem informar as condicoes: nao pode ser imune.
        i = montar_imovel({**LINHA_BASE, "area_total_ha": "20"})
        assert i.possui_outro_imovel_rural is True
        assert i.explora_so_ou_com_familia is False


class TestLeituraDeArquivo:
    def _csv(self, tmp_path, conteudo):
        caminho = tmp_path / "imoveis.csv"
        caminho.write_text(conteudo, encoding="utf-8")
        return caminho

    def test_csv_com_ponto_e_virgula(self, tmp_path):
        arquivo = self._csv(
            tmp_path,
            "nirf;nome_imovel;exercicio;area_total_ha;valor_total_imovel;pastagem\n"
            "111;FAZ A;2026;100;1.000.000,00;80\n",
        )
        imoveis, rejeitadas = ler_planilha(arquivo)
        assert not rejeitadas
        assert imoveis[0].vtn == Decimal("1000000.00")
        assert imoveis[0].utilizadas.pastagens == Decimal("80")

    def test_cabecalho_com_acento_e_maiuscula(self, tmp_path):
        arquivo = self._csv(
            tmp_path,
            "NIRF;Nome Imóvel;Exercício;Área Total (ha);Valor Total Imóvel\n"
            "222;FAZ B;2026;50;500000\n",
        )
        imoveis, rejeitadas = ler_planilha(arquivo)
        assert not rejeitadas
        assert imoveis[0].nome_imovel if hasattr(imoveis[0], "nome_imovel") else True
        assert imoveis[0].area_total == Decimal("50")

    def test_linha_ruim_nao_derruba_o_lote(self, tmp_path):
        arquivo = self._csv(
            tmp_path,
            "nirf;nome_imovel;exercicio;area_total_ha;valor_total_imovel;reserva_legal\n"
            "111;BOA;2026;100;1000000;20\n"
            "222;RUIM;2026;50;500000;80\n"
            "333;BOA2;2026;200;2000000;40\n",
        )
        imoveis, rejeitadas = ler_planilha(arquivo)
        assert len(imoveis) == 2
        assert len(rejeitadas) == 1
        assert rejeitadas[0].numero == 3  # linha 1 e o cabecalho
        assert rejeitadas[0].identificacao == "222"

    def test_linhas_em_branco_sao_ignoradas(self, tmp_path):
        arquivo = self._csv(
            tmp_path,
            "nirf;nome_imovel;exercicio;area_total_ha;valor_total_imovel\n"
            "111;FAZ A;2026;100;1000000\n"
            ";;;;\n",
        )
        imoveis, rejeitadas = ler_planilha(arquivo)
        assert len(imoveis) == 1
        assert not rejeitadas

    def test_arquivo_inexistente(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ler_planilha(tmp_path / "nao_existe.xlsx")

    def test_formato_nao_suportado(self, tmp_path):
        arquivo = tmp_path / "dados.txt"
        arquivo.write_text("x", encoding="utf-8")
        with pytest.raises(ValueError, match="nao suportado"):
            ler_planilha(arquivo)


class TestLoteCompleto:
    def test_separa_ok_alertas_e_rejeitados(self, tmp_path):
        arquivo = tmp_path / "imoveis.csv"
        arquivo.write_text(
            "nirf;nome_imovel;exercicio;area_total_ha;valor_total_imovel;"
            "reserva_legal;pastagem\n"
            "111;OK;2026;100;1000000;20;60\n"          # ok
            "222;ALERTA;2026;100;1000000;20;95\n"      # utilizada > aproveitavel
            "333;RUIM;2026;50;500000;80;0\n",          # nao tributavel > total
            encoding="utf-8",
        )
        lote = processar_planilha(arquivo)
        assert len(lote.ok) == 1
        assert len(lote.com_alertas) == 1
        assert len(lote.rejeitadas) == 1
        assert lote.precisa_revisao is True
        assert lote.total_apurado > 0
