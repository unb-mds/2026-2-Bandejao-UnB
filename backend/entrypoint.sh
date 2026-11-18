#!/bin/sh
# Subida do backend em produção (BD-05).
set -e

# O depends_on do Compose só vale no "docker compose up". Depois de um reboot,
# o Docker sobe todos os containers ao mesmo tempo, e o MySQL ainda não aceita
# conexão. Espera até 60 s antes do migrate.
tentativas=0
until python manage.py check --database default >/dev/null 2>&1; do
    tentativas=$((tentativas + 1))
    if [ "$tentativas" -ge 30 ]; then
        echo "MySQL não respondeu em 60 s" >&2
        exit 1
    fi
    echo "Esperando o MySQL ($tentativas)..."
    sleep 2
done

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# 3 workers: a regra do Gunicorn é 2 x CPUs + 1, e a VM (B2as_v2) tem 2 vCPUs,
# mas parte da CPU fica com o MySQL e o Caddy. O timeout de 30 s fica acima
# do timeout de 10 s do SMTP (settings.py).
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 30 \
    --access-logfile -
