"""Models do app `cardapio`: CAMPUS, REFEICAO, CATEGORIA, PRATO, MARCADOR,
PRATO_MARCADOR, ALERTA_LEITURA_CARDAPIO e CONTADOR_ALERTA.

Fonte: docs/arquitetura/banco-de-dados/C4-nivel-4-banco-de-dados-bandejao.md
(dicionário de dados e estratégia de migração SQLite -> MySQL).
"""

from django.db import models


class TipoRefeicao(models.TextChoices):
    CAFE = "cafe", "Café da manhã"
    ALMOCO = "almoco", "Almoço"
    JANTAR = "jantar", "Jantar"


class StatusLeitura(models.TextChoices):
    OK = "ok", "Lida com sucesso"
    ALERGENOS_INDISPONIVEIS = "alergenos_indisponiveis", "Alérgenos indisponíveis"
    LEITURA_FALHOU = "leitura_falhou", "Leitura falhou"


class Dieta(models.TextChoices):
    PADRAO = "padrao", "Padrão"
    OVOLACTO = "ovolacto", "Ovolacto"
    VEGETARIANO_ESTRITO = "vegetariano_estrito", "Vegetariano estrito"


class TipoAlerta(models.TextChoices):
    LEGENDA_INVALIDA = "legenda_invalida", "Legenda inválida"
    ASSOCIACAO_FALHOU = "associacao_falhou", "Associação falhou"
    FALHA_LEITURA_PDF = "falha_leitura_pdf", "Falha na leitura do PDF"


class Campus(models.Model):
    """Um dos 5 campi com RU. Povoado por fixture (BD-03), nunca pelo usuário."""

    nome = models.CharField(max_length=50, unique=True)
    # O Nível 4 não fixa a precisão das coordenadas: 9 dígitos com 6 casas
    # decimais dão cerca de 0,1 m, mais que o suficiente para o raio do GPS.
    ru_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    ru_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    raio_confirmacao_metros = models.IntegerField()
    centro_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    centro_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    raio_deteccao_metros = models.IntegerField()

    def __str__(self):
        return self.nome


class Refeicao(models.Model):
    """Refeição de um tipo, em um campus e um dia, lida do PDF (RF06, RF07)."""

    campus = models.ForeignKey(
        Campus, on_delete=models.PROTECT, related_name="refeicoes"
    )
    data = models.DateField()
    tipo = models.CharField(max_length=10, choices=TipoRefeicao.choices)
    # Copiados do Anexo A no momento da leitura do PDF.
    horario_inicio = models.TimeField()
    horario_fim = models.TimeField()
    status_leitura = models.CharField(
        max_length=30,
        choices=StatusLeitura.choices,
        default=StatusLeitura.OK,
    )
    # O N4 não fixa o tamanho. O MySQL em modo estrito recusa URL maior que o
    # varchar, e o Leitor grava sem `full_clean`; por isso 500 e não os 200
    # padrão do URLField.
    fonte_pdf_url = models.URLField(max_length=500)
    # Atualizada a cada gravação. Quem implementar o Leitor não deve chamar
    # `save()` na refeição antiga ao manter o último cardápio válido, senão
    # `lida_em` deixa de indicar quando a última leitura deu certo.
    lida_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("campus", "data", "tipo"),
                name="refeicao_unica_por_campus_data_tipo",
            ),
        )

    @property
    def alergenos_indisponivel(self):
        """Derivada de `status_leitura`; não é coluna (Níveis 4 do Leitor e da
        Exposição do Cardápio)."""
        return self.status_leitura == StatusLeitura.ALERGENOS_INDISPONIVEIS

    def __str__(self):
        return f"{self.tipo} de {self.data} ({self.campus_id})"


class Categoria(models.Model):
    """Grupo de pratos de uma refeição, na ordem do PDF (RF07)."""

    refeicao = models.ForeignKey(
        Refeicao, on_delete=models.CASCADE, related_name="categorias"
    )
    nome = models.CharField(max_length=100)
    ordem = models.IntegerField()

    def __str__(self):
        return self.nome


class Prato(models.Model):
    """Opção de uma categoria, para exibição e filtros (RF08, RF09)."""

    categoria = models.ForeignKey(
        Categoria, on_delete=models.CASCADE, related_name="pratos"
    )
    nome = models.CharField(max_length=200)
    # Segue o dicionário de dados do N4 do banco: a dieta fica no prato, e
    # não na categoria. `NULL` nas categorias comuns a todas as dietas (RF09).
    dieta = models.CharField(
        max_length=20, choices=Dieta.choices, null=True, blank=True
    )
    ordem = models.IntegerField()
    # Atalho sobre PratoMarcador: permite `prefetch_related("marcadores")`,
    # `prato.marcadores.add(...)` e `remove(...)`. Não cria coluna nem tabela.
    marcadores = models.ManyToManyField(
        "Marcador", through="PratoMarcador", related_name="pratos"
    )

    def __str__(self):
        return self.nome


class Marcador(models.Model):
    """Um dos 10 marcadores fixos do cardápio (RF06). Povoado por fixture."""

    nome = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.nome


class PratoMarcador(models.Model):
    """Associação muitos-para-muitos entre prato e marcador.

    A chave primária composta (`CompositePrimaryKey`, Django 5.2+) dispensa o
    `id` e já impede o mesmo marcador duas vezes no mesmo prato.
    """

    pk = models.CompositePrimaryKey("prato_id", "marcador_id")
    prato = models.ForeignKey(
        Prato, on_delete=models.CASCADE, related_name="prato_marcadores"
    )
    # Marcadores não são removidos enquanto houver prato associado.
    marcador = models.ForeignKey(
        Marcador, on_delete=models.PROTECT, related_name="prato_marcadores"
    )


class AlertaLeituraCardapio(models.Model):
    """Alerta da leitura do PDF, tratado pela equipe (RF06, ADR 0003)."""

    campus = models.ForeignKey(
        Campus, on_delete=models.CASCADE, related_name="alertas_leitura"
    )
    # Nulo quando o alerta é sobre a leitura do PDF como um todo.
    refeicao = models.ForeignKey(
        Refeicao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alertas_leitura",
    )
    tipo = models.CharField(max_length=30, choices=TipoAlerta.choices)
    mensagem = models.TextField()
    ocorrido_em = models.DateTimeField(auto_now_add=True)
    # Marcado manualmente pela equipe; sem tela administrativa no escopo
    # (RNF08). Hoje, por acesso direto ao banco (ADR 0004).
    resolvido = models.BooleanField(default=False)
    resolvido_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.tipo} em {self.campus_id}"


class ContadorAlerta(models.Model):
    """Limite de avisos por e-mail do Leitor: uma linha por campus, tipo e dia
    (ADR 0006)."""

    campus = models.ForeignKey(
        Campus, on_delete=models.CASCADE, related_name="contadores_alerta"
    )
    tipo = models.CharField(max_length=30, choices=TipoAlerta.choices)
    # Dia da contagem no horário de Brasília (ADR 0006). Quem grava o campo é
    # quem calcula o dia: com TIME_ZONE em UTC nas settings, `localdate()` vira
    # o dia às 21h de Brasília. Ajustar o TIME_ZONE é pendência do BD-04.
    data = models.DateField()
    quantidade_enviada = models.SmallIntegerField(default=0)
    ultimo_envio_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("campus", "tipo", "data"),
                name="contador_alerta_unico_por_campus_tipo_data",
            ),
            models.CheckConstraint(
                condition=models.Q(quantidade_enviada__range=(0, 3)),
                name="contador_alerta_quantidade_entre_0_e_3",
            ),
        )

    def __str__(self):
        return f"{self.tipo} em {self.campus_id} ({self.data})"
