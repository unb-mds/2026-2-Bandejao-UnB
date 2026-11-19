#!/bin/sh
# Subida do backend em produção (BD-05).
set -e

# O depends_on do Compose só vale no "docker compose up". Depois de um reboot,
# o Docker sobe todos os containers ao mesmo tempo, e o MySQL ainda não aceita
# conexão. Espera até 60 s antes do migrate.
# O prazo é por relógio, e não por tentativas: cada check carrega o Django
# antes de tentar a conexão e leva alguns segundos.
limite=$(($(date +%s) + 60))
tentativas=0
until erro=$(python manage.py check --database default 2>&1); do
    tentativas=$((tentativas + 1))
    if [ "$(date +%s)" -ge "$limite" ]; then
        # O erro pode não ser do MySQL (variável faltando no .env, DB_ENGINE
        # errado): mostra a última saída, com o motivo real.
        echo "O backend não conseguiu falar com o banco em 60 s. Último erro:" >&2
        echo "$erro" | tail -n 5 >&2
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
