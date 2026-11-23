"""Teste de carga do cardápio e da previsão (BD-14, #184).

RNF01: 2.000 usuários, p95 ≤ 3 s em `GET /api/cardapio/` e
`GET /api/fila/previsao/`. A carga em si roda no workflow `carga.yml`, com o
Locust, o Gunicorn e o MySQL. Aqui ficam testadas as partes em Python do
pacote `carga/`:

- `dados`: popula um banco vazio com o volume do teste;
- `cenario`: os pedidos que cada usuário simulado faz;
- `avaliar`: lê o CSV do Locust e compara o p95 com a meta.
"""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cardapio.models import Campus, FonteCardapio, Prato, Refeicao
from apps.fila.models import Checkin
from carga import avaliar, cenario, dados
from config.parametros import ParametrosFilaConfig

CABECALHO = (
    "Type,Name,Request Count,Failure Count,Median Response Time,"
    "Average Response Time,Min Response Time,Max Response Time,"
    "Average Content Size,Requests/s,Failures/s,50%,66%,75%,80%,90%,95%,"
    "98%,99%,99.9%,99.99%,100%"
)


# --- dados ------------------------------------------------------------------


@pytest.fixture
def campi(db):
    call_command("loaddata", "campi", "marcadores", verbosity=0)
    return list(Campus.objects.order_by("pk"))


def test_popular_cria_a_semana_publicada_e_as_refeicoes(campi):
    hoje = timezone.localdate()

    resumo = dados.popular(hoje, checkins_por_refeicao=5)

    segunda = hoje - timedelta(days=hoje.weekday())
    assert FonteCardapio.objects.filter(semana_inicio=segunda).count() == len(campi)
    # 7 dias x 3 refeições por campus, todas com pratos.
    assert Refeicao.objects.count() == len(campi) * 7 * 3
    assert resumo.refeicoes == Refeicao.objects.count()
    assert resumo.pratos == Prato.objects.count() > 0


def test_popular_cria_os_checkins_das_semanas_da_previsao(campi):
    hoje = timezone.localdate()
    dias = 7 * ParametrosFilaConfig.janela_semanas

    resumo = dados.popular(hoje, checkins_por_refeicao=5)

    assert resumo.checkins == Checkin.objects.count() == len(campi) * 3 * dias * 5
    datas = set(Checkin.objects.values_list("data", flat=True))
    assert min(datas) == hoje - timedelta(days=dias)
    # Hoje não entra na previsão; o dia de hoje fica sem check-in.
    assert max(datas) == hoje - timedelta(days=1)
    # Sem conta, como depois da retenção: nenhum dado pessoal no teste.
    assert not Checkin.objects.filter(usuario__isnull=False).exists()


def test_faixas_dos_checkins_ficam_dentro_do_horario_da_refeicao(campi):
    dados.popular(timezone.localdate(), checkins_por_refeicao=5)

    for checkin in Checkin.objects.all()[:200]:
        inicio, fim = dados.HORARIOS[checkin.tipo_refeicao]
        assert inicio <= checkin.faixa_inicio < fim
        assert checkin.faixa_inicio.minute % 15 == 0


def test_popular_e_deterministico(campi):
    hoje = timezone.localdate()
    dados.popular(hoje, checkins_por_refeicao=5, semente=7)
    primeira = list(
        Checkin.objects.order_by("pk").values_list("faixa_inicio", "tempo_espera_min")
    )
    Checkin.objects.all().delete()
    Refeicao.objects.all().delete()
    FonteCardapio.objects.all().delete()

    dados.popular(hoje, checkins_por_refeicao=5, semente=7)
    segunda = list(
        Checkin.objects.order_by("pk").values_list("faixa_inicio", "tempo_espera_min")
    )

    assert primeira == segunda


def test_popular_recusa_banco_com_checkins(campi):
    """Proteção: nunca popular o banco de produção, que já tem check-ins."""
    dados.popular(timezone.localdate(), checkins_por_refeicao=1)

    with pytest.raises(dados.BancoNaoVazioError):
        dados.popular(timezone.localdate(), checkins_por_refeicao=1)


def test_popular_exige_os_campi_da_fixture(db):
    with pytest.raises(dados.SemCampiError):
        dados.popular(timezone.localdate(), checkins_por_refeicao=1)


def test_endpoints_respondem_com_dados_depois_de_popular(campi):
    """O teste de carga mede respostas de verdade: cardápio publicado e
    previsão disponível, e não as respostas vazias, que são mais leves."""
    dados.popular(timezone.localdate(), checkins_por_refeicao=5)
    cliente = APIClient()

    for campus in campi:
        cardapio = cliente.get("/api/cardapio/", {"campus": campus.pk}).json()
        assert cardapio["status"] == "publicado"
        assert cardapio["categorias"]
        for refeicao in ("cafe", "almoco", "jantar"):
            previsao = cliente.get(
                "/api/fila/previsao/", {"campus": campus.pk, "refeicao": refeicao}
            ).json()
            assert previsao["status"] == "disponivel", (campus.nome, refeicao)
            assert previsao["faixas"]


# --- cenario ----------------------------------------------------------------


def test_cenario_cobre_os_dois_endpoints_em_todos_os_campi():
    pedidos = cenario.pedidos([1, 2, 3, 4, 5])

    cardapio = [p for p in pedidos if p.nome == cenario.NOME_CARDAPIO]
    previsao = [p for p in pedidos if p.nome == cenario.NOME_PREVISAO]
    assert {p.url for p in cardapio} == {
        f"/api/cardapio/?campus={c}" for c in range(1, 6)
    }
    assert {p.url for p in previsao} == {
        f"/api/fila/previsao/?campus={c}&refeicao={r}"
        for c in range(1, 6)
        for r in ("cafe", "almoco", "jantar")
    }


def test_cenario_agrupa_as_estatisticas_por_endpoint():
    """Um nome por endpoint, para o Locust somar os campi numa linha só."""
    nomes = {p.nome for p in cenario.pedidos([1, 2])}

    assert nomes == {cenario.NOME_CARDAPIO, cenario.NOME_PREVISAO}


def test_cenario_pesa_mais_o_cardapio():
    """O cardápio é a tela de entrada do PWA; a previsão é aberta menos."""
    assert cenario.PESO_CARDAPIO > cenario.PESO_PREVISAO > 0


# --- avaliar ----------------------------------------------------------------


def csv_de_estatisticas(tmp_path, linhas):
    arquivo = tmp_path / "carga_stats.csv"
    corpo = [CABECALHO]
    for tipo, nome, total, falhas, p95 in linhas:
        corpo.append(
            f"{tipo},{nome},{total},{falhas},100,120,5,4000,800,50.0,0.0,"
            f"100,150,200,300,500,{p95},700,900,1500,2000,4000"
        )
    arquivo.write_text("\n".join(corpo) + "\n", encoding="utf-8")
    return arquivo


LINHAS_BOAS = [
    ("GET", cenario.NOME_CARDAPIO, 9000, 0, 800),
    ("GET", cenario.NOME_PREVISAO, 3000, 0, 1200),
    ("", "Aggregated", 12000, 0, 900),
]


def test_aprova_com_p95_dentro_da_meta(tmp_path):
    resultado = avaliar.avaliar(
        avaliar.ler_estatisticas(csv_de_estatisticas(tmp_path, LINHAS_BOAS))
    )

    assert resultado.aprovado
    assert resultado.motivos == []
    assert resultado.linhas[cenario.NOME_PREVISAO].p95_ms == 1200


def test_reprova_com_p95_acima_da_meta_em_um_endpoint(tmp_path):
    linhas = [*LINHAS_BOAS]
    linhas[1] = ("GET", cenario.NOME_PREVISAO, 3000, 0, 3100)

    resultado = avaliar.avaliar(
        avaliar.ler_estatisticas(csv_de_estatisticas(tmp_path, linhas))
    )

    assert not resultado.aprovado
    assert any(cenario.NOME_PREVISAO in motivo for motivo in resultado.motivos)


def test_p95_igual_a_meta_passa(tmp_path):
    linhas = [*LINHAS_BOAS]
    linhas[0] = ("GET", cenario.NOME_CARDAPIO, 9000, 0, 3000)

    assert avaliar.avaliar(
        avaliar.ler_estatisticas(csv_de_estatisticas(tmp_path, linhas))
    ).aprovado


def test_reprova_com_falhas_acima_de_1_por_cento(tmp_path):
    """Respostas com erro são rápidas e mascarariam um p95 ruim."""
    linhas = [*LINHAS_BOAS]
    linhas[0] = ("GET", cenario.NOME_CARDAPIO, 9000, 100, 800)

    resultado = avaliar.avaliar(
        avaliar.ler_estatisticas(csv_de_estatisticas(tmp_path, linhas))
    )

    assert not resultado.aprovado
    assert any("falha" in motivo for motivo in resultado.motivos)


def test_reprova_sem_um_dos_endpoints(tmp_path):
    linhas = [LINHAS_BOAS[0], LINHAS_BOAS[2]]

    resultado = avaliar.avaliar(
        avaliar.ler_estatisticas(csv_de_estatisticas(tmp_path, linhas))
    )

    assert not resultado.aprovado
    assert any(cenario.NOME_PREVISAO in motivo for motivo in resultado.motivos)


def test_le_n_a_como_sem_medida(tmp_path):
    arquivo = csv_de_estatisticas(tmp_path, LINHAS_BOAS)
    texto = arquivo.read_text(encoding="utf-8").replace(
        f"GET,{cenario.NOME_PREVISAO},3000,0", f"GET,{cenario.NOME_PREVISAO},0,0"
    )
    texto = texto.replace(",1200,", ",N/A,")
    arquivo.write_text(texto, encoding="utf-8")

    resultado = avaliar.avaliar(avaliar.ler_estatisticas(arquivo))

    assert resultado.linhas[cenario.NOME_PREVISAO].p95_ms is None
    assert not resultado.aprovado


def test_resumo_em_markdown_tem_a_tabela_e_o_veredito(tmp_path):
    resultado = avaliar.avaliar(
        avaliar.ler_estatisticas(csv_de_estatisticas(tmp_path, LINHAS_BOAS))
    )

    texto = avaliar.markdown(resultado)

    assert "| Endpoint |" in texto
    assert cenario.NOME_CARDAPIO in texto
    assert "800" in texto
    assert "3000" in texto
    assert "Aprovado" in texto


@pytest.mark.parametrize(("linhas", "codigo"), [(LINHAS_BOAS, 0), ([], 1)])
def test_main_devolve_o_codigo_de_saida(tmp_path, capsys, linhas, codigo):
    arquivo = csv_de_estatisticas(tmp_path, linhas)

    assert avaliar.main([str(arquivo)]) == codigo
    assert "| Endpoint |" in capsys.readouterr().out
