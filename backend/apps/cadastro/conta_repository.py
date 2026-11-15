"""Acesso às contas no cadastro (Cadastro N4 4a e 4b).

Só o que a BE-05 e a BE-06 usam. `salvar` e o uso de `buscar_por_identificador`
no login (BE-07) e `excluir` (exclusão de conta, BD-12) entram nas issues delas.
"""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Max, Q
from django.db.models.functions import Coalesce

from apps.cadastro.models import (
    StatusUsuario,
    TipoToken,
    normalizar_apelido,
    normalizar_email,
)


class ContaRepository:
    def existe_matricula_ou_siape(self, identificador: str) -> bool:
        return get_user_model().objects.filter(matricula_siape=identificador).exists()

    def existe_email(self, email: str) -> bool:
        return (
            get_user_model()
            .objects.filter(email_institucional=normalizar_email(email))
            .exists()
        )

    def existe_apelido(self, apelido: str) -> bool:
        """Mesma regra do UNIQUE: sem distinguir maiúsculas nem acentos."""
        return (
            get_user_model()
            .objects.filter(apelido_normalizado=normalizar_apelido(apelido))
            .exists()
        )

    def apelidos_com_prefixo(self, prefixo: str) -> set[str]:
        """Apelidos normalizados que começam com `prefixo` (uma consulta só)."""
        return set(
            get_user_model()
            .objects.filter(apelido_normalizado__startswith=normalizar_apelido(prefixo))
            .values_list("apelido_normalizado", flat=True)
        )

    def buscar_por_identificador(self, identificador: str):
        """A conta da matrícula/SIAPE, ou None se não houver."""
        return get_user_model().objects.filter(matricula_siape=identificador).first()

    def pendentes_expiradas(self, limite: datetime):
        """Contas pendentes cujo último link de confirmação saiu antes de `limite`.

        O prazo conta do link mais recente (o reenvio renova, RF02.2), e não da
        criação da conta. Conta pendente sem nenhum link (o envio falhou antes
        de criar o token) usa o `criado_em` da própria conta.
        """
        return (
            get_user_model()
            .objects.filter(status=StatusUsuario.PENDENTE, email_confirmado=False)
            .annotate(
                ultimo_link=Coalesce(
                    Max(
                        "tokens__criado_em",
                        filter=Q(tokens__tipo=TipoToken.CONFIRMACAO_EMAIL),
                    ),
                    "criado_em",
                )
            )
            .filter(ultimo_link__lt=limite)
        )

    def excluir_pendente_expirada(self, conta, limite: datetime) -> bool:
        """Apaga a conta se ela ainda for pendente e expirada. Diz se apagou.

        Entre a listagem do job e aqui, a pessoa pode ter confirmado ou pedido
        um link novo. Por isso a conta é travada (`select_for_update`) antes de
        o prazo ser conferido de novo: no MySQL, um reenvio ou uma confirmação
        concorrentes esperam o fim desta transação. Se um deles fez commit
        antes, a conferência já vê o link novo (ou a conta ativa) e não apaga.
        No SQLite dos testes, a trava não tem efeito (ele trava o banco inteiro
        na escrita), então lá só a conferência protege.

        Apaga pelo ORM (e nunca por DELETE direto) para os tokens e a pontuação
        irem junto (`on_delete=CASCADE`).
        """
        modelo = get_user_model()
        with transaction.atomic():
            travada = modelo.objects.select_for_update().filter(pk=conta.pk).first()
            if travada is None:
                return False
            ainda_expirada = self.pendentes_expiradas(limite).filter(pk=conta.pk)
            if not ainda_expirada.exists():
                return False
            # Pelo id: o QuerySet com agregação (Max) não aceita delete().
            modelo.objects.filter(pk=conta.pk).delete()
            return True
