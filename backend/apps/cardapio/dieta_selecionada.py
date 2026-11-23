"""DietaSelecionada: a dieta escolhida no filtro do cardápio (RF09, Exposição N4 4a).

Não confundir com o enum `Dieta` do model (`padrao`, `ovolacto`,
`vegetariano_estrito`): aquele é a dieta do **prato**, lida do PDF; este é o
que o usuário escolheu, com os valores do parâmetro `dieta` do contrato.
"""

from django.db import models


class DietaSelecionada(models.TextChoices):
    SEM_FILTRO = "sem_filtro", "Sem filtro"
    OVOLACTOVEGETARIANO = "ovolactovegetariano", "Ovolactovegetariano"
    VEGETARIANO_ESTRITO = "vegetariano_estrito", "Vegetariano estrito"
