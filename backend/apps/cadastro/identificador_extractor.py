"""Extração do identificador por tipo de usuário (ADR 0002, Cadastro N4 4a).

Estudante: a matrícula vem do e-mail e o apelido é digitado.
Professor/Servidor: o SIAPE é digitado e o apelido vem do e-mail.
O extractor só separa os valores; quem valida é o `CadastroService`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from apps.cadastro.dados_cadastro import DadosCadastro
from apps.cadastro.models import TipoUsuario


@dataclass(frozen=True)
class IdentificadorExtraido:
    identificador: str
    # Nome do Nível 4. É o texto antes do "@", ainda sem limpeza: quem o
    # transforma no apelido é o `ApelidoResolver.resolver_extraido`. None para
    # Estudante, que digita o apelido.
    apelido_sugerido: str | None


def _antes_do_arroba(dados: DadosCadastro) -> str:
    return dados.email_institucional.strip().partition("@")[0]


class IdentificadorExtractor(ABC):
    @abstractmethod
    def extrair(self, dados: DadosCadastro) -> IdentificadorExtraido: ...


class EstudanteIdentificadorExtractor(IdentificadorExtractor):
    def extrair(self, dados: DadosCadastro) -> IdentificadorExtraido:
        # Uma matrícula digitada é ignorada: vale a do e-mail (ADR 0002).
        return IdentificadorExtraido(
            identificador=_antes_do_arroba(dados), apelido_sugerido=None
        )


class ProfessorServidorIdentificadorExtractor(IdentificadorExtractor):
    def extrair(self, dados: DadosCadastro) -> IdentificadorExtraido:
        return IdentificadorExtraido(
            identificador=dados.matricula_siape.strip(),
            apelido_sugerido=_antes_do_arroba(dados),
        )


ESTRATEGIAS = {
    TipoUsuario.ESTUDANTE: EstudanteIdentificadorExtractor,
    TipoUsuario.PROFESSOR_SERVIDOR: ProfessorServidorIdentificadorExtractor,
}


def extractor_para(tipo_usuario: TipoUsuario) -> IdentificadorExtractor:
    try:
        return ESTRATEGIAS[tipo_usuario]()
    except KeyError:
        raise ValueError(
            f"Tipo de usuário sem estratégia de extração: {tipo_usuario!r}"
        ) from None
