"""AvisoPrivacidadeService: ciência do aviso de privacidade (RF11, RNF07.1, Cadastro N4 4d).

Quem tinha conta antes da versão atual do aviso vê o aviso de novo (o
`GET /api/sessao/` diz `avisoPrivacidadePendente`) e registra a ciência por
`POST /api/privacidade/aceite/`, antes do primeiro check-in.
"""

from datetime import datetime

from apps.cadastro.conta_repository import ContaRepository
from apps.cadastro.models import Usuario
from config.parametros import AvisoPrivacidadeConfig


class AvisoPrivacidadeService:
    def __init__(self):
        self.conta_repository = ContaRepository()

    def registrar_ciencia(self, conta: Usuario, agora: datetime) -> None:
        """Grava a versão atual do aviso e a hora do servidor.

        Se a conta já aceitou a versão atual, nada muda: a hora do primeiro
        aceite é a prova do consentimento (RNF07.1). Quem confere é o banco,
        e não a conta em memória, que pode estar velha (duplo clique).
        """
        versao = AvisoPrivacidadeConfig.versao_atual
        if self.conta_repository.registrar_aceite_se_pendente(conta, versao, agora):
            # Mantém a conta em memória igual ao banco.
            conta.versao_aviso_aceita = versao
            conta.aceite_privacidade_em = agora
