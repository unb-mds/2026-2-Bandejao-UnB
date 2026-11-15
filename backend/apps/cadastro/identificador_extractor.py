"""Extração do identificador por tipo de usuário (ADR 0002, Cadastro N4 4a).

Estudante: a matrícula vem do e-mail e o apelido é digitado.
Professor/Servidor: o SIAPE é digitado e o apelido vem do e-mail.
Cada regra fica numa estratégia, em vez de `if tipo == ...` no serviço.
O extractor só separa os valores; quem valida é o `CadastroService`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from apps.cadastro.models import TipoUsuario


@dataclass(frozen=True)
class IdentificadorExtraido:
    identificador: str
    # Texto antes do "@", ainda sem limpeza (o ApelidoResolver limpa).
    # None para Estudante, que digita o apelido.
    apelido_sugerido: str | None


def _antes_do_arroba(dados: dict) -> str:
    return dados.get("emailInstitucional", "").strip().partition("@")[0]


class IdentificadorExtractor(ABC):
    @abstractmethod
    def extrair(self, dados: dict) -> IdentificadorExtraido: ...


class EstudanteIdentificadorExtractor(IdentificadorExtractor):
    def extrair(self, dados: dict) -> IdentificadorExtraido:
        # Uma matrícula digitada é ignorada: vale a do e-mail (ADR 0002).
        return IdentificadorExtraido(
            identificador=_antes_do_arroba(dados), apelido_sugerido=None
        )


class ProfessorServidorIdentificadorExtractor(IdentificadorExtractor):
    def extrair(self, dados: dict) -> IdentificadorExtraido:
        return IdentificadorExtraido(
            identificador=dados.get("matriculaSiape", "").strip(),
            apelido_sugerido=_antes_do_arroba(dados),
        )


ESTRATEGIAS = {
    TipoUsuario.ESTUDANTE: EstudanteIdentificadorExtractor,
    TipoUsuario.PROFESSOR_SERVIDOR: ProfessorServidorIdentificadorExtractor,
}


def extractor_para(tipo_usuario: TipoUsuario) -> IdentificadorExtractor:
    return ESTRATEGIAS[tipo_usuario]()
