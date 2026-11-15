"""Acesso às contas no cadastro (Cadastro N4 4a).

Só o que a BE-05 usa. `buscar_por_identificador` (login, BE-07) e
`excluir_pendente_expirada` (job do RF02, BE-06) entram nas issues delas.
"""

from django.contrib.auth import get_user_model


class ContaRepository:
    def existe_matricula_ou_siape(self, identificador: str) -> bool:
        return get_user_model().objects.filter(matricula_siape=identificador).exists()

    def existe_email(self, email: str) -> bool:
        # O e-mail é gravado em minúsculas (Usuario.save).
        return (
            get_user_model()
            .objects.filter(email_institucional=email.strip().lower())
            .exists()
        )
