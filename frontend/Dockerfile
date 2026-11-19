# Imagem do Caddy com o build do PWA (BD-05, ADR 0012). O Caddy serve estes
# arquivos estáticos na raiz do domínio e encaminha /api/ e /admin/ ao
# backend. O Caddyfile fica na raiz do repositório e é montado pelo Compose.

# Etapa 1: build do PWA.
FROM node:24-slim AS construcao

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

# O build de produção sempre usa a API real: o apiClient só liga o backend
# simulado no servidor de desenvolvimento (import.meta.env.DEV).
RUN npm run build


# Etapa 2: só o Caddy e a pasta dist.
FROM caddy:2.11-alpine

COPY --from=construcao /app/dist /srv/pwa
