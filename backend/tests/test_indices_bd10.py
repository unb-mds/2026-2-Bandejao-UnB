"""BD-10 (#150): as consultas da previsão e do ranking usam os índices do Nível 4.

Os índices conferidos são os do dicionário de dados
(docs/arquitetura/banco-de-dados/C4-nivel-4-banco-de-dados-bandejao.md):

- `CHECKIN` (`campus_id`, `tipo_refeicao`, `data`): previsão de pico (RF13) e
  espera estimada (RN08), Fila N4 4c;
- `PONTOS_SEMESTRE_CAMPUS` (`campus_id`, `semestre_referencia`, `pontos` desc,
  `atualizado_em`): ranking e desempate (RF27.2), Gamificação N4 4c.

O `PrevisaoService` (BE-15) e o `RankingService` (BE-17) ainda não existem.
As consultas abaixo têm a forma que o Nível 4 descreve para o
`CheckinRepository.contarPorFaixa`, o `CheckinRepository.temposDeEspera` e o
`PontuacaoRepository.elegiveis`: quem implementar esses métodos deve manter os
filtros de igualdade nas colunas do começo do índice e, no ranking, a ordem
`-pontos, atualizado_em`, ou o plano muda (ver docs/arquitetura/banco-de-dados/
indices-bd10.md).

Os dados de teste têm volume suficiente para o otimizador ter escolha: os
índices de uma coluna das FKs (`campus_id`, `usuario_id`) e o de `data` também
servem às consultas, e o teste falha se algum deles for escolhido no lugar do
índice composto.

O `EXPLAIN` roda nos dois bancos do CI: `EXPLAIN QUERY PLAN` no SQLite e
`EXPLAIN` no MySQL 8.4 (o que vale para produção, RNF01). O plano é impresso
para ficar no log do CI (passo "EXPLAIN dos índices (BD-10)" do job
`testes-mysql`).
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Count
from django.utils import timezone

from apps.cadastro.models import StatusUsuario
from apps.cardapio.models import Campus, TipoRefeicao
from apps.fila.models import Checkin
from apps.gamificacao.models import PontosSemestreCampus, PontuacaoUsuario

INDICE_CHECKIN = "checkin_campus_tipo_data_idx"
INDICE_RANKING = "pontos_semestre_ranking_idx"

# Volume dos dados de teste: 5 campi, 3 refeições, 12 semanas de segunda a
# sexta e 4 faixas por refeição dão 3.600 check-ins; 120 contas em 5 campi e
# 2 semestres dão 1.200 linhas de pontos.
QTD_CONTAS = 120
SEMANAS = 12
FAIXAS = (time(11, 0), time(11, 15), time(11, 30), time(11, 45))
SEMESTRES = ("2026.1", "2026.2")

# Dia da previsão (uma quarta-feira) e a janela de 4 semanas no mesmo dia da
# semana (RF13, ParametrosFilaConfig.janelaSemanas).
DIA_PREVISAO = date(2026, 11, 18)
JANELA = [DIA_PREVISAO - timedelta(weeks=n) for n in range(1, 5)]


def _criar_campi():
    return [
        Campus.objects.create(
            nome=f"Campus {n}",
            ru_latitude=Decimal("-15.764203"),
            ru_longitude=Decimal("-47.870251"),
            raio_confirmacao_metros=150,
            confirmacao_ativa=True,
            centro_latitude=Decimal("-15.764203"),
            centro_longitude=Decimal("-47.870251"),
            raio_deteccao_metros=150,
        )
        for n in range(1, 6)
    ]


def _criar_contas():
    """Contas por `bulk_create`: o `create_user` (hash de senha e
    `full_clean`) deixaria o teste lento à toa. Por isso o apelido normalizado
    e a senha inutilizável vão preenchidos aqui."""
    agora = timezone.now()
    contas = get_user_model().objects.bulk_create(
        get_user_model()(
            tipo_usuario="estudante",
            matricula_siape=f"2026{n:05d}",
            apelido=f"conta{n}",
            apelido_normalizado=f"conta{n}",
            email_institucional=f"2026{n:05d}@aluno.unb.br",
            password="!",
            # Uma conta em cada 10 está suspensa e sai do ranking.
            status=StatusUsuario.SUSPENSO if n % 10 == 0 else StatusUsuario.ATIVO,
            aceite_privacidade_em=agora,
            versao_aviso_aceita="teste",
        )
        for n in range(QTD_CONTAS)
    )
    PontuacaoUsuario.objects.bulk_create(
        # Metade das contas aderiu ao ranking (RN12).
        PontuacaoUsuario(usuario=conta, participa_ranking=n % 2 == 0)
        for n, conta in enumerate(contas)
    )
    return contas


def _criar_checkins(campi, contas):
    """Check-ins de segunda a sexta nas 12 semanas antes do dia da previsão,
    nas três refeições. Uma parte já perdeu o vínculo (retenção, RNF07.3)."""
    inicio = DIA_PREVISAO - timedelta(weeks=SEMANAS)
    dias = [
        inicio + timedelta(days=d)
        for d in range(SEMANAS * 7)
        if (inicio + timedelta(days=d)).weekday() < 5
    ]
    checkins = []
    n = 0
    for campus in campi:
        for tipo in TipoRefeicao.values:
            for dia in dias:
                for faixa in FAIXAS:
                    conta = contas[n % len(contas)]
                    n += 1
                    checkins.append(
                        Checkin(
                            usuario=conta if n % 3 else None,
                            campus=campus,
                            tipo_refeicao=tipo,
                            data=dia,
                            registrado_em=timezone.make_aware(
                                datetime.combine(dia, faixa)
                            ),
                            faixa_inicio=faixa,
                            tempo_espera_min=(Decimal(n % 20) if n % 4 == 0 else None),
                        )
                    )
    Checkin.objects.bulk_create(checkins, batch_size=500)


def _criar_pontos(campi, contas):
    PontosSemestreCampus.objects.bulk_create(
        (
            PontosSemestreCampus(
                usuario=conta,
                campus=campus,
                semestre_referencia=semestre,
                # Algumas contas ficam com zero ponto e saem do ranking.
                pontos=(n * 7 + campus.id) % 50,
            )
            for semestre in SEMESTRES
            for campus in campi
            for n, conta in enumerate(contas)
        ),
        batch_size=500,
    )


@pytest.fixture
def dados_de_teste(transactional_db):
    """Monta os dados e atualiza as estatísticas do banco.

    `transactional_db` porque o `ANALYZE TABLE` do MySQL faz commit implícito,
    o que quebraria o rollback do teste comum; a limpeza fica com o `flush` do
    pytest-django.
    """
    campi = _criar_campi()
    contas = _criar_contas()
    _criar_checkins(campi, contas)
    _criar_pontos(campi, contas)

    tabelas = (Checkin._meta.db_table, PontosSemestreCampus._meta.db_table)
    with connection.cursor() as cursor:
        if connection.vendor == "mysql":
            cursor.execute(f"ANALYZE TABLE {', '.join(tabelas)}")
            cursor.fetchall()
        else:
            cursor.execute("ANALYZE")
    return campi


def consulta_contagem_por_faixa(campus):
    """Forma do `CheckinRepository.contarPorFaixa` (previsão de pico, RF13):
    check-ins por dia e faixa na janela de 4 semanas."""
    return (
        Checkin.objects.filter(
            campus=campus, tipo_refeicao=TipoRefeicao.ALMOCO, data__in=JANELA
        )
        .values("data", "faixa_inicio")
        .annotate(quantidade=Count("id"))
        .order_by()
    )


def consulta_tempos_de_espera(campus):
    """Forma do `CheckinRepository.temposDeEspera` (espera estimada, RN08)."""
    return Checkin.objects.filter(
        campus=campus,
        tipo_refeicao=TipoRefeicao.ALMOCO,
        data__in=JANELA,
        tempo_espera_min__isnull=False,
    ).values("data", "faixa_inicio", "tempo_espera_min")


def consulta_ranking(campus):
    """Forma do `PontuacaoRepository.elegiveis` + tamanho do ranking (RF27.2,
    RN12): só quem aderiu, conta ativa e ao menos 1 ponto no semestre, pelos
    pontos e desempate por `atualizado_em`, até 10 linhas."""
    return (
        PontosSemestreCampus.objects.filter(
            campus=campus,
            semestre_referencia="2026.2",
            pontos__gte=1,
            usuario__status=StatusUsuario.ATIVO,
            usuario__pontuacao__participa_ranking=True,
        )
        .select_related("usuario")
        .order_by("-pontos", "atualizado_em")[:10]
    )


def plano(queryset):
    """Linhas do `EXPLAIN` da consulta, como dicionários."""
    sql, parametros = queryset.query.sql_with_params()
    prefixo = "EXPLAIN" if connection.vendor == "mysql" else "EXPLAIN QUERY PLAN"
    with connection.cursor() as cursor:
        cursor.execute(f"{prefixo} {sql}", parametros)
        colunas = [coluna[0] for coluna in cursor.description]
        linhas = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
    # `str()` mostra o valor das choices ("almoco"), não o nome do enum.
    valores = tuple(repr(str(p) if isinstance(p, str) else p) for p in parametros)
    print(f"\n[{connection.vendor}] {sql % valores}")
    for linha in linhas:
        print(f"  {linha}")
    return linhas


def linha_da_tabela(linhas, tabela):
    """No MySQL, a linha do `EXPLAIN` da tabela; no SQLite, o passo do plano
    que lê a tabela."""
    if connection.vendor == "mysql":
        encontradas = [linha for linha in linhas if linha["table"] == tabela]
    else:
        encontradas = [
            linha
            for linha in linhas
            if linha["detail"].split(" ")[0] in ("SEARCH", "SCAN")
            and linha["detail"].split(" ")[1] == tabela
        ]
    assert len(encontradas) == 1, f"{tabela} não aparece uma vez no plano: {linhas}"
    return encontradas[0]


def indice_usado(linha):
    if connection.vendor == "mysql":
        return linha["key"]
    # Ex.: "SEARCH fila_checkin USING INDEX checkin_campus_tipo_data_idx (...)".
    partes = linha["detail"].split(" ")
    if "INDEX" not in partes:
        return None
    return partes[partes.index("INDEX") + 1]


def ordena_sem_arquivo_temporario(linhas):
    """Sem "Using filesort" (MySQL) nem "TEMP B-TREE FOR ORDER BY" (SQLite):
    a ordem do ranking sai do próprio índice."""
    if connection.vendor == "mysql":
        return not any("filesort" in (linha["Extra"] or "") for linha in linhas)
    return not any("FOR ORDER BY" in linha["detail"] for linha in linhas)


@pytest.mark.parametrize(
    "consulta", [consulta_contagem_por_faixa, consulta_tempos_de_espera]
)
def test_previsao_usa_indice_de_campus_tipo_e_data(dados_de_teste, consulta):
    campus = dados_de_teste[2]

    linhas = plano(consulta(campus))

    assert indice_usado(linha_da_tabela(linhas, Checkin._meta.db_table)) == (
        INDICE_CHECKIN
    )


def test_previsao_conta_os_mesmos_checkins_que_a_janela(dados_de_teste):
    """Confere que a consulta do plano é a da previsão, e não uma vazia: 4 dias
    da janela x 4 faixas, um check-in em cada."""
    campus = dados_de_teste[2]

    contagens = list(consulta_contagem_por_faixa(campus))

    assert len(contagens) == len(JANELA) * len(FAIXAS)
    assert {contagem["quantidade"] for contagem in contagens} == {1}


def test_ranking_usa_indice_e_nao_ordena_em_arquivo_temporario(dados_de_teste):
    campus = dados_de_teste[2]

    linhas = plano(consulta_ranking(campus))

    linha = linha_da_tabela(linhas, PontosSemestreCampus._meta.db_table)
    assert indice_usado(linha) == INDICE_RANKING
    assert ordena_sem_arquivo_temporario(linhas), linhas


def test_ranking_respeita_ordem_e_elegibilidade(dados_de_teste):
    """Confere que a consulta do plano devolve o ranking esperado."""
    campus = dados_de_teste[2]

    linhas = list(consulta_ranking(campus))

    assert len(linhas) == 10
    chaves = [(-linha.pontos, linha.atualizado_em) for linha in linhas]
    assert chaves == sorted(chaves)
    assert all(linha.pontos >= 1 for linha in linhas)
    assert all(linha.usuario.status == StatusUsuario.ATIVO for linha in linhas)
    assert all(linha.usuario.pontuacao.participa_ranking for linha in linhas)
