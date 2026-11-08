"""Testes dos models do app `cardapio` (BD-01, parte 2).

Cada teste vem de uma regra do Nível 4 do banco (dicionário de dados e tabela
"Constraints principais") ou de uma lacuna apontada no review do PR #108.
"""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.cardapio.models import (
    AlertaLeituraCardapio,
    Campus,
    Categoria,
    ContadorAlerta,
    Dieta,
    Marcador,
    Prato,
    PratoMarcador,
    Refeicao,
    StatusLeitura,
    TipoAlerta,
    TipoRefeicao,
)

pytestmark = pytest.mark.django_db

_contador = 0


def _proximo():
    global _contador
    _contador += 1
    return _contador


def criar_campus(**kwargs):
    n = _proximo()
    dados = {
        "nome": f"Campus {n}",
        "ru_latitude": Decimal("-15.763100"),
        "ru_longitude": Decimal("-47.866900"),
        "raio_confirmacao_metros": 150,
        "centro_latitude": Decimal("-15.765000"),
        "centro_longitude": Decimal("-47.868000"),
        "raio_deteccao_metros": 1500,
    }
    dados.update(kwargs)
    return Campus.objects.create(**dados)


def criar_refeicao(**kwargs):
    dados = {
        "data": date(2026, 11, 9),
        "tipo": TipoRefeicao.ALMOCO,
        "horario_inicio": time(11, 0),
        "horario_fim": time(14, 0),
        "fonte_pdf_url": "https://ru.unb.br/cardapio.pdf",
    }
    dados.update(kwargs)
    if "campus" not in dados:
        dados["campus"] = criar_campus()
    return Refeicao.objects.create(**dados)


def criar_categoria(**kwargs):
    dados = {"nome": "Prato principal", "ordem": 1}
    dados.update(kwargs)
    if "refeicao" not in dados:
        dados["refeicao"] = criar_refeicao()
    return Categoria.objects.create(**dados)


def criar_prato(**kwargs):
    dados = {"nome": "Arroz", "ordem": 1}
    dados.update(kwargs)
    if "categoria" not in dados:
        dados["categoria"] = criar_categoria()
    return Prato.objects.create(**dados)


def criar_marcador(**kwargs):
    dados = {"nome": f"marcador{_proximo()}"}
    dados.update(kwargs)
    return Marcador.objects.create(**dados)


def criar_alerta(**kwargs):
    dados = {
        "tipo": TipoAlerta.LEGENDA_INVALIDA,
        "mensagem": "Ícone desconhecido na legenda.",
    }
    dados.update(kwargs)
    if "campus" not in dados:
        dados["campus"] = criar_campus()
    return AlertaLeituraCardapio.objects.create(**dados)


def criar_contador(**kwargs):
    dados = {"tipo": TipoAlerta.FALHA_LEITURA_PDF, "data": date(2026, 11, 9)}
    dados.update(kwargs)
    if "campus" not in dados:
        dados["campus"] = criar_campus()
    return ContadorAlerta.objects.create(**dados)


class TestCampus:
    def test_nome_deve_ser_unico(self):
        criar_campus(nome="Gama")
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_campus(nome="Gama")

    def test_coordenadas_guardam_as_6_casas_decimais(self):
        # Com 6 casas reais, uma coluna com menos casas arredondaria o valor.
        # O limite de `max_digits` só é garantido no MySQL (SQLite não o aplica).
        campus = criar_campus(
            ru_latitude=Decimal("-15.763147"),
            ru_longitude=Decimal("-47.866912"),
            centro_latitude=Decimal("-15.765031"),
            centro_longitude=Decimal("-47.868044"),
        )
        campus.refresh_from_db()
        assert campus.ru_latitude == Decimal("-15.763147")
        assert campus.ru_longitude == Decimal("-47.866912")
        assert campus.centro_latitude == Decimal("-15.765031")
        assert campus.centro_longitude == Decimal("-47.868044")

    def test_campus_protegido_nao_apaga_alertas_nem_contadores(self):
        # O PROTECT de Refeicao prevalece sobre o CASCADE dos alertas.
        refeicao = criar_refeicao()
        campus = refeicao.campus
        criar_alerta(campus=campus)
        criar_contador(campus=campus)
        with pytest.raises(ProtectedError):
            campus.delete()
        assert AlertaLeituraCardapio.objects.count() == 1
        assert ContadorAlerta.objects.count() == 1


class TestRefeicao:
    def test_uma_refeicao_por_campus_data_e_tipo(self):
        campus = criar_campus()
        criar_refeicao(campus=campus)
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_refeicao(campus=campus)

    def test_unicidade_ignora_horario_e_status_de_leitura(self):
        campus = criar_campus()
        criar_refeicao(campus=campus)
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_refeicao(
                campus=campus,
                horario_inicio=time(12, 0),
                status_leitura=StatusLeitura.LEITURA_FALHOU,
            )

    def test_mesmo_campus_e_tipo_em_outro_dia_sao_permitidos(self):
        campus = criar_campus()
        criar_refeicao(campus=campus, data=date(2026, 11, 9))
        criar_refeicao(campus=campus, data=date(2026, 11, 10))
        assert Refeicao.objects.filter(campus=campus).count() == 2

    def test_tipos_diferentes_no_mesmo_dia_sao_permitidos(self):
        campus = criar_campus()
        criar_refeicao(campus=campus, tipo=TipoRefeicao.ALMOCO)
        criar_refeicao(campus=campus, tipo=TipoRefeicao.JANTAR)
        assert Refeicao.objects.filter(campus=campus).count() == 2

    def test_campi_diferentes_podem_ter_a_mesma_refeicao(self):
        criar_refeicao(campus=criar_campus())
        criar_refeicao(campus=criar_campus())
        assert Refeicao.objects.count() == 2

    def test_status_de_leitura_comeca_ok(self):
        refeicao = criar_refeicao()
        refeicao.refresh_from_db()
        assert refeicao.status_leitura == StatusLeitura.OK
        assert refeicao.alergenos_indisponivel is False

    def test_alergenos_indisponivel_vem_do_status(self):
        refeicao = criar_refeicao(status_leitura=StatusLeitura.ALERGENOS_INDISPONIVEIS)
        assert refeicao.alergenos_indisponivel is True

    def test_leitura_falhou_nao_indica_alergenos_indisponiveis(self):
        refeicao = criar_refeicao(status_leitura=StatusLeitura.LEITURA_FALHOU)
        assert refeicao.alergenos_indisponivel is False

    def test_lida_em_e_preenchida_automaticamente(self):
        assert criar_refeicao().lida_em is not None

    def test_lida_em_e_atualizada_a_cada_gravacao(self, monkeypatch):
        refeicao = criar_refeicao()
        refeicao.refresh_from_db()
        depois = refeicao.lida_em + timedelta(hours=1)
        monkeypatch.setattr(timezone, "now", lambda: depois)
        refeicao.save()
        refeicao.refresh_from_db()
        assert refeicao.lida_em == depois

    def test_campus_com_refeicao_nao_pode_ser_removido(self):
        refeicao = criar_refeicao()
        with pytest.raises(ProtectedError):
            refeicao.campus.delete()


class TestCategoriaEPrato:
    def test_remover_refeicao_remove_categorias_e_pratos(self):
        prato = criar_prato()
        prato.categoria.refeicao.delete()
        assert Categoria.objects.count() == 0
        assert Prato.objects.count() == 0

    def test_dieta_e_opcional(self):
        assert criar_prato().dieta is None

    def test_dieta_aceita_os_valores_do_dicionario(self):
        prato = criar_prato(dieta=Dieta.VEGETARIANO_ESTRITO)
        prato.refresh_from_db()
        assert prato.dieta == "vegetariano_estrito"


class TestMarcador:
    def test_nome_deve_ser_unico(self):
        criar_marcador(nome="soja")
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_marcador(nome="soja")


class TestPratoMarcador:
    def test_chave_primaria_e_composta(self):
        prato, marcador = criar_prato(), criar_marcador()
        associacao = PratoMarcador.objects.create(prato=prato, marcador=marcador)
        assert associacao.pk == (prato.pk, marcador.pk)

    def test_mesmo_marcador_nao_repete_no_mesmo_prato(self):
        prato, marcador = criar_prato(), criar_marcador()
        PratoMarcador.objects.create(prato=prato, marcador=marcador)
        with pytest.raises(IntegrityError), transaction.atomic():
            PratoMarcador.objects.create(prato=prato, marcador=marcador)

    def test_prato_aceita_varios_marcadores_e_marcador_varios_pratos(self):
        prato_a, prato_b = criar_prato(), criar_prato()
        soja, ovo = criar_marcador(), criar_marcador()
        PratoMarcador.objects.create(prato=prato_a, marcador=soja)
        PratoMarcador.objects.create(prato=prato_a, marcador=ovo)
        PratoMarcador.objects.create(prato=prato_b, marcador=soja)
        assert PratoMarcador.objects.count() == 3

    def test_remover_prato_remove_a_associacao_e_mantem_o_marcador(self):
        prato, marcador = criar_prato(), criar_marcador()
        PratoMarcador.objects.create(prato=prato, marcador=marcador)
        prato.delete()
        assert PratoMarcador.objects.count() == 0
        assert Marcador.objects.filter(pk=marcador.pk).exists()

    def test_marcador_com_prato_associado_nao_pode_ser_removido(self):
        prato, marcador = criar_prato(), criar_marcador()
        PratoMarcador.objects.create(prato=prato, marcador=marcador)
        with pytest.raises(ProtectedError):
            marcador.delete()

    def test_prato_e_marcador_se_enxergam_pela_relacao_many_to_many(self):
        prato, soja, ovo = criar_prato(), criar_marcador(), criar_marcador()
        PratoMarcador.objects.create(prato=prato, marcador=soja)
        PratoMarcador.objects.create(prato=prato, marcador=ovo)
        assert set(prato.marcadores.all()) == {soja, ovo}
        assert list(soja.pratos.all()) == [prato]

    def test_add_e_remove_pela_relacao_many_to_many(self):
        prato, marcador = criar_prato(), criar_marcador()
        prato.marcadores.add(marcador)
        assert PratoMarcador.objects.filter(prato=prato, marcador=marcador).exists()
        prato.marcadores.remove(marcador)
        assert PratoMarcador.objects.count() == 0
        assert Marcador.objects.filter(pk=marcador.pk).exists()

    def test_prefetch_traz_os_marcadores_sem_consulta_extra(
        self, django_assert_num_queries
    ):
        prato, soja = criar_prato(), criar_marcador()
        PratoMarcador.objects.create(prato=prato, marcador=soja)
        pratos = list(Prato.objects.prefetch_related("marcadores"))
        with django_assert_num_queries(0):
            assert list(pratos[0].marcadores.all()) == [soja]


class TestAlertaLeituraCardapio:
    def test_alerta_novo_nao_esta_resolvido(self):
        alerta = criar_alerta()
        assert alerta.ocorrido_em is not None
        assert alerta.resolvido is False
        assert alerta.resolvido_em is None

    def test_ocorrido_em_nao_muda_ao_salvar_de_novo(self, monkeypatch):
        alerta = criar_alerta()
        alerta.refresh_from_db()
        original = alerta.ocorrido_em
        monkeypatch.setattr(timezone, "now", lambda: original + timedelta(hours=1))
        alerta.resolvido = True
        alerta.save()
        alerta.refresh_from_db()
        assert alerta.ocorrido_em == original

    def test_refeicao_e_opcional(self):
        assert criar_alerta().refeicao is None

    def test_remover_a_refeicao_mantem_o_alerta_sem_refeicao(self):
        refeicao = criar_refeicao()
        alerta = criar_alerta(campus=refeicao.campus, refeicao=refeicao)
        refeicao.delete()
        alerta.refresh_from_db()
        assert alerta.refeicao is None

    def test_remover_o_campus_remove_os_alertas(self):
        alerta = criar_alerta()
        alerta.campus.delete()
        assert AlertaLeituraCardapio.objects.count() == 0


class TestContadorAlerta:
    def test_contador_novo_comeca_em_zero(self):
        contador = criar_contador()
        contador.refresh_from_db()
        assert contador.quantidade_enviada == 0
        assert contador.ultimo_envio_em is None

    def test_uma_contagem_por_campus_tipo_e_dia(self):
        campus = criar_campus()
        criar_contador(campus=campus)
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_contador(campus=campus)

    def test_tipo_ou_dia_diferentes_sao_contagens_separadas(self):
        campus = criar_campus()
        criar_contador(campus=campus)
        criar_contador(campus=campus, tipo=TipoAlerta.LEGENDA_INVALIDA)
        criar_contador(campus=campus, data=date(2026, 11, 10))
        assert ContadorAlerta.objects.filter(campus=campus).count() == 3

    def test_mesmo_tipo_e_dia_em_outro_campus_sao_contagens_separadas(self):
        # A falha de um campus não pode bloquear a contagem de outro.
        criar_contador(campus=criar_campus())
        criar_contador(campus=criar_campus())
        assert ContadorAlerta.objects.count() == 2

    @pytest.mark.parametrize("quantidade", [0, 1, 2, 3])
    def test_quantidade_de_0_a_3_e_aceita(self, quantidade):
        contador = criar_contador(quantidade_enviada=quantidade)
        assert contador.quantidade_enviada == quantidade

    @pytest.mark.parametrize("quantidade", [-1, 4])
    def test_quantidade_fora_de_0_a_3_e_rejeitada(self, quantidade):
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_contador(quantidade_enviada=quantidade)

    def test_quantidade_nula_e_rejeitada(self):
        # NULL passaria no CHECK (resultado "unknown" em SQL); o NOT NULL barra.
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_contador(quantidade_enviada=None)

    def test_remover_o_campus_remove_os_contadores(self):
        contador = criar_contador()
        contador.campus.delete()
        assert ContadorAlerta.objects.count() == 0
