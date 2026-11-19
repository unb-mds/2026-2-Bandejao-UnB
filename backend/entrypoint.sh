#!/bin/sh
# Subida do backend em produção (BD-05).
set -e

# Sem DB_ENGINE=mysql no .env, o settings.py cai no SQLite sem erro: o site
# parece normal, mas os dados ficam num arquivo dentro do container e somem
# no próximo build. Mesma checagem do CI ("Validar backend MySQL"). Não abre
# conexão, então também mostra na hora um erro de configuração (variável
# obrigatória faltando no .env), em vez de esperar o prazo abaixo.
python manage.py shell -c "from django.db import connection; assert connection.vendor == 'mysql', f'Em produção o banco precisa ser o MySQL (DB_ENGINE=mysql no .env), e não {connection.vendor}.'"

# O depends_on do Compose só vale no "docker compose up". Depois de um reboot,
# o Docker sobe todos os containers ao mesmo tempo, e o MySQL ainda não aceita
# conexão. Espera cerca de 60 s antes do migrate.
# O prazo é por relógio, e não por tentativas: cada check carrega o Django
# antes de tentar a conexão. O timeout limita cada tentativa, porque um host
# que não resolve chega a prender o check por uns 45 s.
limite=$(($(date +%s) + 60))
tentativas=0
until erro=$(timeout 10 python manage.py check --database default 2>&1); do
    tentativas=$((tentativas + 1))
    if [ -z "$erro" ]; then
        # Um DB_HOST que não resolve também cai aqui: a busca no DNS demora
        # mais que o timeout.
        erro="A tentativa passou de 10 s sem resposta do banco (confira o DB_HOST e se o db está no ar)."
    fi
    if [ "$(date +%s)" -ge "$limite" ]; then
        printf '%s\n' "O backend não conseguiu falar com o banco em 60 s. Último erro:" >&2
        printf '%s\n' "$erro" | tail -n 5 >&2
        exit 1
    fi
    # A última linha do erro já mostra se é o banco subindo (Can't connect)
    # ou configuração (Access denied, host errado).
    printf '%s\n' "Esperando o banco ($tentativas): $(printf '%s\n' "$erro" | tail -n 1)"
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
