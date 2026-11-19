# Imagem do backend em produção (BD-05, ADR 0012): Django servido pelo
# Gunicorn, atrás do Caddy. O entrypoint.sh aplica as migrations e o
# collectstatic a cada subida.

# Etapa 1: compila as dependências. O mysqlclient precisa do compilador e dos
# cabeçalhos do cliente MySQL, que não vão para a imagem final.
FROM python:3.14-slim AS construcao

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-prod.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements-prod.txt


# Etapa 2: imagem final, só com a biblioteca do cliente MySQL e os pacotes já
# compilados.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libmariadb3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=construcao /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# O Gunicorn não roda como root.
RUN useradd --create-home --uid 1000 app
WORKDIR /app
COPY --chown=app:app . .
# Pasta do collectstatic (STATIC_ROOT). Criada aqui para o volume nomeado do
# Compose herdar o dono "app"; senão o collectstatic não teria permissão.
RUN mkdir -p staticfiles && chown app:app staticfiles

USER app
EXPOSE 8000

ENTRYPOINT ["sh", "entrypoint.sh"]
