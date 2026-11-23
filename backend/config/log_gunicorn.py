"""Logs do Gunicorn em produção (BE-10, #137).

O Gunicorn carrega este módulo pelo `--logger-class` do entrypoint.sh, e o
tests/test_deploy_be10.py também. Nada que rode em desenvolvimento pode
importá-lo (o settings.py, por exemplo): o gunicorn só existe na imagem e no
job testes-mysql do CI.
"""

from gunicorn.glogging import Logger

from config.logs import MascaraTokenDoPath


class LogDeAcessoSemToken(Logger):
    """Logger do Gunicorn com o token de `/api/confirmar-email/` trocado por `***`.

    A página `/confirmar-email` do PWA chama `POST /api/confirmar-email/{token}/`.
    Uma chamada recusada (CSRF, limite de taxa, 5xx) deixaria o token, ainda
    válido, na linha do log de acesso. O log de erros também grava o path
    ("Error handling request <método> <uri>") quando uma exceção escapa do
    WSGI.
    """

    def setup(self, cfg):
        super().setup(cfg)
        # O reload (SIGHUP) roda o setup() de novo nos mesmos loggers: um
        # filtro só por logger.
        for logger in (self.access_log, self.error_log):
            if not any(isinstance(f, MascaraTokenDoPath) for f in logger.filters):
                logger.addFilter(MascaraTokenDoPath())
