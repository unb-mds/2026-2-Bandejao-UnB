"""Log de acesso do Gunicorn em produção (BE-10, #137).

Só é importado pelo Gunicorn (entrypoint.sh, --logger-class): em
desenvolvimento e nos jobs do CI sem o requirements-prod.txt, o gunicorn não
está instalado.
"""

from gunicorn.glogging import Logger

from config.logs import MascaraTokenDoPath


class LogDeAcessoSemToken(Logger):
    """Logger do Gunicorn com o token do path trocado por `***`.

    A página `/confirmar-email` do PWA chama `POST /api/confirmar-email/{token}/`.
    Uma chamada recusada (CSRF, limite de taxa, 5xx) deixa o token ainda válido
    na linha do log.
    """

    def setup(self, cfg):
        super().setup(cfg)
        self.access_log.addFilter(MascaraTokenDoPath())
