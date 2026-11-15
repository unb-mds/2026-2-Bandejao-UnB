"""Acesso às contas no cadastro (Cadastro N4 4a).

Só o que a BE-05 usa. `buscar_por_identificador` (login, BE-07),
`excluir_pendente_expirada` (job do RF02, BE-06) e `excluir` (exclusão de
conta, BD-12) entram nas issues delas.
"""

from django.contrib.auth import get_user_model

from apps.cadastro.models import normalizar_apelido, normalizar_email


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
