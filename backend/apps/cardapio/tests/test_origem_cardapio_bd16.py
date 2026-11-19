"""BD-16: origem do cardápio de cada campus (ADR 0014).

- `CAMPUS.rotulo_pagina_ru` e `CAMPUS.prefixo_arquivo_pdf`: NOT NULL e
  UNIQUE, com os valores do Anexo A na fixture dos 5 campi;
- tabela `FONTE_CARDAPIO`: uma linha por campus e semana, com UNIQUE
  (`campus_id`, `semana_inicio`) e `ON DELETE CASCADE` no campus;
- data migration que preenche as colunas novas nos campi que já existem.

Fonte: docs/arquitetura/banco-de-dados/C4-nivel-4-banco-de-dados-bandejao.md
(`CAMPUS` e `FONTE_CARDAPIO`) e Documento de Requisitos, Anexo A.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from apps.cardapio.models import Campus, FonteCardapio

# Rótulo na página do RU e prefixo do arquivo, por campus (Anexo A, ADR 0014).
ORIGEM_ESPERADA = {
    1: ("Darcy Ribeiro", "Darcy-Ribeiro"),
    2: ("Ceilândia", "Ceilandia"),
    3: ("Gama", "Gama"),
    4: ("Planaltina", "Planaltina"),
    5: ("Fazenda Água Limpa", "Fazenda"),
}

SHA256_EXEMPLO = "a" * 64
URL_EXEMPLO = (
    "https://ru.unb.br/wp-content/uploads/2026/11/Gama-Semana-04-09-11-a-15-11.pdf"
)


def criar_campus(nome, rotulo, prefixo):
    return Campus.objects.create(
        nome=nome,
        ru_latitude=Decimal("-15.989493"),
        ru_longitude=Decimal("-48.044024"),
        raio_confirmacao_metros=150,
        centro_latitude=Decimal("-15.989493"),
        centro_longitude=Decimal("-48.044024"),
        raio_deteccao_metros=150,
        rotulo_pagina_ru=rotulo,
        prefixo_arquivo_pdf=prefixo,
    )


def criar_fonte(campus, semana_inicio=date(2026, 11, 9), **campos):
    agora = timezone.now()
    valores = {
        "url": URL_EXEMPLO,
        "sha256": SHA256_EXEMPLO,
        "verificado_em": agora,
        "processado_em": agora,
        **campos,
    }
    return FonteCardapio.objects.create(
        campus=campus, semana_inicio=semana_inicio, **valores
    )


@pytest.mark.django_db
def test_fixture_campi_traz_rotulo_e_prefixo_do_anexo_a():
    call_command("loaddata", "campi", verbosity=0)

    origem = {
        campus.pk: (campus.rotulo_pagina_ru, campus.prefixo_arquivo_pdf)
        for campus in Campus.objects.all()
    }

    assert origem == ORIGEM_ESPERADA
    for campus in Campus.objects.all():
        campus.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize("campo", ["rotulo_pagina_ru", "prefixo_arquivo_pdf"])
def test_dois_campi_nao_disputam_o_mesmo_rotulo_ou_prefixo(campo):
    """UNIQUE nas duas colunas: dois campi não podem pegar o mesmo bloco da
    página nem o mesmo arquivo (Nível 4 do banco, regra do ADR 0014)."""
    criar_campus("Gama", "Gama", "Gama")
    valores = {"rotulo": "Outro", "prefixo": "Outro"}
    valores["rotulo" if campo == "rotulo_pagina_ru" else "prefixo"] = "Gama"

    with pytest.raises(IntegrityError), transaction.atomic():
        criar_campus("Outro campus", valores["rotulo"], valores["prefixo"])


@pytest.mark.parametrize("campo", ["rotulo_pagina_ru", "prefixo_arquivo_pdf"])
def test_colunas_de_origem_sao_obrigatorias_e_tem_50_caracteres(campo):
    coluna = Campus._meta.get_field(campo)

    assert coluna.null is False
    assert coluna.unique is True
    assert coluna.max_length == 50


@pytest.mark.django_db
def test_fonte_cardapio_guarda_a_ultima_leitura_com_sucesso():
    campus = criar_campus("Gama", "Gama", "Gama")

    fonte = criar_fonte(campus)
    fonte.refresh_from_db()

    assert fonte.campus == campus
    assert fonte.semana_inicio == date(2026, 11, 9)
    assert fonte.url == URL_EXEMPLO
    assert fonte.sha256 == SHA256_EXEMPLO
    assert fonte.verificado_em is not None
    assert fonte.processado_em is not None


@pytest.mark.django_db
def test_uma_origem_por_campus_e_semana():
    campus = criar_campus("Gama", "Gama", "Gama")
    criar_fonte(campus)

    with pytest.raises(IntegrityError), transaction.atomic():
        criar_fonte(campus, sha256="b" * 64)


@pytest.mark.django_db
def test_semana_seguinte_e_outro_campus_tem_linhas_proprias():
    """A semana vigente e a seguinte (RF18) podem estar publicadas juntas."""
    gama = criar_campus("Gama", "Gama", "Gama")
    darcy = criar_campus("Darcy Ribeiro", "Darcy Ribeiro", "Darcy-Ribeiro")

    criar_fonte(gama)
    criar_fonte(gama, semana_inicio=date(2026, 11, 9) + timedelta(weeks=1))
    criar_fonte(darcy)

    assert FonteCardapio.objects.filter(campus=gama).count() == 2
    assert FonteCardapio.objects.count() == 3


@pytest.mark.django_db
def test_excluir_o_campus_apaga_a_origem():
    campus = criar_campus("Gama", "Gama", "Gama")
    criar_fonte(campus)

    campus.delete()

    assert not FonteCardapio.objects.exists()


def test_tamanho_das_colunas_de_fonte_cardapio():
    """`url` com o mesmo tamanho de `REFEICAO.fonte_pdf_url` e `sha256` com
    os 64 caracteres hexadecimais do SHA-256 (Nível 4 do banco)."""
    assert FonteCardapio._meta.get_field("url").max_length == 500
    assert FonteCardapio._meta.get_field("sha256").max_length == 64
    for campo in ("semana_inicio", "url", "sha256", "verificado_em", "processado_em"):
        assert FonteCardapio._meta.get_field(campo).null is False


# --- Data migration -------------------------------------------------------

MIGRACAO_ANTERIOR = ("cardapio", "0003_campus_constraints_bd03")
MIGRACAO_BD16 = ("cardapio", "0004_origem_cardapio_bd16")


def migrar_para(destino):
    executor = MigrationExecutor(connection)
    executor.migrate([destino])
    return executor.loader.project_state([destino]).apps


@pytest.fixture
def estado_anterior(transactional_db):
    destinos_finais = MigrationExecutor(connection).loader.graph.leaf_nodes()
    try:
        yield migrar_para(MIGRACAO_ANTERIOR)
    finally:
        MigrationExecutor(connection).migrate(destinos_finais)


def criar_campus_historico(apps, pk, nome):
    return (
        apps.get_model("cardapio", "Campus")
        .objects.using(connection.alias)
        .create(
            pk=pk,
            nome=nome,
            ru_latitude=Decimal("-15.764203"),
            ru_longitude=Decimal("-47.870251"),
            raio_confirmacao_metros=150,
            confirmacao_ativa=True,
            centro_latitude=Decimal("-15.764203"),
            centro_longitude=Decimal("-47.870251"),
            raio_deteccao_metros=150,
        )
    )


def test_migration_preenche_rotulo_e_prefixo_dos_campi_existentes(estado_anterior):
    """Em produção os 5 campi já existem (BD-03) quando as colunas entram."""
    for pk, nome in (
        (1, "Darcy Ribeiro"),
        (2, "Ceilândia"),
        (3, "Gama"),
        (4, "Planaltina"),
        (5, "Fazenda Água Limpa"),
    ):
        criar_campus_historico(estado_anterior, pk, nome)

    estado_novo = migrar_para(MIGRACAO_BD16)
    campus = estado_novo.get_model("cardapio", "Campus")

    origem = {
        pk: (rotulo, prefixo)
        for pk, rotulo, prefixo in campus.objects.values_list(
            "pk", "rotulo_pagina_ru", "prefixo_arquivo_pdf"
        )
    }
    assert origem == ORIGEM_ESPERADA


def test_migration_usa_o_nome_para_campus_fora_do_anexo_a(estado_anterior):
    """Um campus que não está no Anexo A recebe o próprio nome nas duas
    colunas, que é único, para a migration não falhar. O valor certo vem
    depois pela fixture."""
    criar_campus_historico(estado_anterior, 9, "Campus de Teste")
    criar_campus_historico(estado_anterior, 3, "Gama")

    estado_novo = migrar_para(MIGRACAO_BD16)
    campus = estado_novo.get_model("cardapio", "Campus")

    teste = campus.objects.get(pk=9)
    assert teste.rotulo_pagina_ru == "Campus de Teste"
    assert teste.prefixo_arquivo_pdf == "Campus de Teste"
    gama = campus.objects.get(pk=3)
    assert (gama.rotulo_pagina_ru, gama.prefixo_arquivo_pdf) == ("Gama", "Gama")
