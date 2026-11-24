# Bandejão — Frontend (PWA)

Frontend do Bandejão em **Vue 3 + Vite** (HTML, CSS e JavaScript, sem framework de CSS),
cobrindo a **Release 1 (MVP)** do Documento de Requisitos e reproduzindo as telas e a
navegação do protótipo do Figma (`protótipo/Bandejão PWA Prototype.zip`).

## Como rodar

Requer Node `^22.18.0` ou `>=24.12.0`.

```sh
npm install
npm run dev        # servidor de desenvolvimento
npm run test:unit  # testes (Vitest)
npm run lint       # oxlint + eslint, corrigindo o que der
npm run build      # build de produção em dist/

# Os mesmos comandos do CI (frontend-ci.yml), para conferir antes do PR:
npm run lint:ci    # oxlint + eslint sem corrigir nada; aviso também reprova
npm run test:ci    # testes com cobertura (relatório em coverage/index.html)
npm audit --audit-level=high

# Mutação (StrykerJS, FE-17). Demorado: a base inteira leva dezenas de minutos.
npm run mutacao                                      # todos os arquivos críticos
npm run mutacao -- --mutate src/stores/fila.js       # um arquivo só
# Relatório em reports/mutation/mutation.html
```

### Backend simulado × API real

Enquanto a API Django não expõe todos os endpoints, o app usa, **só em desenvolvimento e nos
testes**, um **backend simulado** (`src/services/mock/`). Nas rotas de cadastro, confirmação,
reenvio e sessão ele segue o contrato OpenAPI v1 (`backend/openapi.yaml`, BE-03): mesmas
rotas, nomes de campos, status e `codigo`. O build de produção (`npm run build`) não inclui o
simulado e sempre fala com a API real. Os dados de demonstração (contas, avaliações) ficam no
`localStorage` do navegador.

- Conta de demonstração: e-mail `231034567@aluno.unb.br` / senha `bandejao123`.
- Onde o sistema real enviaria um e-mail (confirmação de cadastro, redefinição de senha), a
  tela mostra um quadro "Modo demonstração" com o link, para seguir o fluxo inteiro.

Para usar a API real em desenvolvimento, suba o Django em `localhost:8000` e crie
`frontend/.env.local`:

```sh
VITE_USE_MOCK=false
```

O Vite encaminha `/api` para `http://localhost:8000`, então PWA e API ficam na mesma origem
e o cookie de sessão funciona sem CORS (ADR 0007). Não mude `VITE_API_URL` para outra origem:
o `apiClient` usa `credentials: 'same-origin'`.

### Testes de ponta a ponta (Playwright, FE-18)

Os fluxos do usuário rodam num navegador de verdade, contra o PWA de produção, a API e o MySQL
no Docker (`e2e/docker-compose.yml`), no celular (360×800) e no desktop (1366×768). Precisa do
Docker e do Chromium do Playwright:

```sh
npx playwright install --with-deps chromium   # uma vez (com as bibliotecas do sistema)
npm run e2e:subir                 # builda e sobe PWA, API, MySQL e Mailpit (localhost:8080)
npm run e2e                       # limpa o banco, carrega as fixtures e roda os testes
npm run e2e -- --project celular  # só um projeto
npm run e2e:descer                # derruba tudo e apaga os volumes
```

O relógio do backend do e2e começa na segunda-feira, 23/11/2026, ao meio-dia (horário de
Brasília), a cada subida do container, e anda dali em diante, para o check-in e a avaliação
valerem a qualquer hora. O `npm run e2e` recria o backend antes de rodar, então o relógio volta
ao meio-dia a cada rodada; com a pilha no ar há mais de 2h30, o healthcheck do backend acusa
que o relógio saiu do almoço. Os e-mails ficam no Mailpit
(http://localhost:8025). As fixtures e como foram geradas estão em `e2e/dados/README.md`; o
funcionamento completo, no Plano de Testes (3.5 e 5.3).

### CI do front

O `.github/workflows/frontend-ci.yml` roda em todo PR, com cinco portas (Plano de Testes 5.2):

| Job | O que reprova |
|---|---|
| `lint (front)` | Qualquer erro ou aviso do Oxlint ou do ESLint, incluindo teste sem `expect` (`vitest/expect-expect`) e `v-html` |
| `testes (front)` | Teste falhando, ou menos de 70% de linhas em algum arquivo crítico (`coverage.thresholds` no `vitest.config.js`, montado a partir do `ARQUIVOS_CRITICOS` do `scripts/mutacao.mjs`). A tabela por módulo sai no resumo do run, e o relatório HTML no artefato `cobertura-front` |
| `build (front)` | Erro no `vite build`, ou o servidor simulado dentro do `dist/` |
| `seguranca (front)` | Dependência com vulnerabilidade alta ou crítica (`npm audit`) e achado de severidade ERROR no Semgrep |
| `mutacao (front)` | Escore de mutação abaixo de 50% nos arquivos críticos alterados no PR. O job roda em todo PR, mas só chama o Stryker quando o PR mexe em algum arquivo crítico, num teste que chegue a um deles ou na configuração da mutação |

Arquivo crítico novo (por exemplo, uma store de um extra) entra no `MODULOS` do
`scripts/mutacao.mjs` no mesmo PR que o cria: a mutação e o `coverage.thresholds` do
`vitest.config.js` usam essa lista. A base inteira passa pela mutação toda semana
(`frontend-mutacao-semanal.yml`).

Se o Stryker quebrar no dry run de um componente `.vue` com "`defineProps()` ... cannot reference
locally declared variables", envolva o `defineProps` com `// Stryker disable all` e
`// Stryker restore all`, como no `CheckinBotao.vue`: o Stryker envolve os valores em chamadas
declaradas no próprio script, e o `defineProps`, içado para fora do `setup()`, não pode usá-las.

## O que está implementado (MVP)

| Requisito | Onde |
|---|---|
| RF01 Cadastro em duas etapas (Aluno / Professor / Servidor), aviso de privacidade | `CadastroView` |
| RF02 Confirmação de e-mail, reenvio do link | `ConfirmarEmailView`, `LoginView` |
| RF03 Login (por e-mail institucional, como no protótipo), mensagens genéricas, bloqueio | `LoginView` |
| RF04 Recuperação e redefinição de senha | `RecuperarSenhaView`, `RedefinirSenhaView` |
| RF05 Navegação sem login; convite ao login nas ações restritas | router, `ConviteLogin` |
| RF06/RF07 Cardápio por campus, dia e refeição; "não publicado"; alérgenos indisponíveis | `CardapioView` |
| RF08 Filtro de marcadores (sem filtro: alerta "Contém: …"; com filtro: prato oculto) | `FiltroCardapio` |
| RF09 Filtro de dieta com "mostrar todas" | `FiltroCardapio`, `CardapioView` |
| RF15 Avaliação por estrelas + comentário, edição, média e lista pública | `AvaliacoesView`, `AvaliacaoWidget` |
| RF17 Paleta e tipografia únicas | `src/assets/base.css` |
| RNF05 PWA instalável (manifest + service worker) | `public/`, `src/pwa.js` |

A **Fila** (RF11–RF13) é da Release 2: a tela existe, para manter a navegação do protótipo,
mas mostra "Em breve".

## Navegação

```
/ ──(1ª visita)──► /boas-vindas ──► /login ──► /cadastro ──► /confirmar-email
  └(campus salvo)► /cardapio            └────► /campus ──► /inicio
                                                              ├─► /cardapio
                                                              ├─► /fila       (Em breve)
                                                              └─► /avaliacoes
```

A barra inferior (Início, Cardápio, Fila, Avaliações, Perfil) aparece em Cardápio, Fila e
Avaliações, como no protótipo. O menu do avatar, na Início, permite trocar de campus e
entrar/sair. `/cardapio/:campusId` é um link compartilhável que também define o campus.

## Estrutura

```
src/
├── assets/          base.css (tokens de design) e main.css (padrões compartilhados)
├── components/      AppLogo, IconeSvg, EstrelasNota, CampoTexto, CampoSenha, BotaoVoltar,
│                    CabecalhoFormulario, NavegacaoInferior, FiltroCardapio,
│                    AvaliacaoWidget, ConviteLogin, LinkSimulado
├── constants/       campi, refeições (horários do Anexo A), marcadores, dietas
├── router/          rotas nomeadas e lazy-loaded
├── services/
│   ├── apiClient.js único ponto de contato com a API (C4 nível 3b)
│   └── mock/        backend simulado (servidor, dados, validações do RF01)
├── stores/          Pinia: auth (sem token), preferencias (localStorage), cardapio, avaliacoes
├── utils/           datas e regras de exibição do cardápio (filtros, refeição padrão)
└── views/           uma view por tela
```

Segue o C4 nível 3/4 do frontend: nenhuma view chama a API diretamente, a sessão fica no
cookie HttpOnly do Django (ADR 0007, nada de token no JavaScript; ao abrir o app, o
guarda `carregarSessaoAoAbrir` do roteador chama `GET /api/sessao/` uma vez) e apenas campus e filtros
são persistidos no aparelho. O `apiClient` manda `X-CSRFToken` (lido do cookie `csrftoken`,
buscado em `GET /api/csrf/` se ainda não existe) em POST, PUT, PATCH e DELETE, limpa o `authStore` quando recebe 401
(menos no `GET /api/sessao/` da abertura do app e no login, que pedem `avisarSessaoPerdida: false`) e transforma erros em
`ApiError` com `status`, `codigo` e `mensagem`. Se o `GET /api/sessao/` demora mais de 3 s, o app abre como visitante.

## Contrato da API

O contrato oficial é o **OpenAPI v1** em `backend/openapi.yaml` (BE-03). Erros vêm como
`{ "codigo": "snake_case", "mensagem": "texto para o usuário" }`. Rotas que o MVP já usa,
todas sob `/api`:

| Método e rota | Corpo | Respostas |
|---|---|---|
| `GET /csrf/` | — | `204`, grava o cookie `csrftoken` (o `apiClient` chama sozinho antes da primeira escrita) |
| `POST /cadastro/` | `{ tipoUsuario: estudante\|professor_servidor, emailInstitucional, senha, apelido?, matriculaSiape?, aceitePrivacidade }` | `201 { emailInstitucional, status: "pendente" }`, `409 { codigo: apelido_indisponivel, apelidoSugerido }`, `422 dados_invalidos`, `429 limite_excedido` (40/h por IP) |
| `POST /confirmar-email/{token}/` | — | `200`, `410 token_invalido_ou_expirado` |
| `POST /reenviar-confirmacao/` | `{ emailInstitucional }` ou `{ token }` (com os dois, vale o e-mail; sem conta, o token) | `200` sem corpo (sempre igual; acima de 3 links/h por conta, não manda outro), `422 dados_invalidos`, `429 limite_excedido` (10/h por IP) |
| `POST /sessao/` (login) | `{ emailInstitucional, senha }` (`@aluno.unb.br` ou `@unb.br`, #201) | `200 { apelido, tipo, avisoPrivacidadePendente }`, `401 credenciais_invalidas`, `403 conta_nao_confirmada`, `422 dados_invalidos`, `429 login_bloqueado` (conta) ou `limite_excedido` (60/h por IP) |
| `GET /sessao/` (quem sou) | — | `200 { apelido, tipo, avisoPrivacidadePendente }`, `401 nao_autenticado` |
| `DELETE /sessao/` (logout) | — | `204`, `401 nao_autenticado` |

Qualquer rota logada sem sessão responde `401 { codigo: "nao_autenticado" }`. Toda escrita,
com ou sem sessão, sem o `X-CSRFToken` certo responde `403 { codigo: "csrf_invalido" }` (não
desloga). Erro sem `mensagem` (ex.: o `detail` em inglês do DRF) aparece com uma mensagem em
português pelo status; as telas mostram erros com `mensagemDeErro(falha)`.

Ainda no formato do MVP no simulado (entram no contrato nas tarefas FE-08, FE-09 e FE-E2):
`GET /avaliacoes/?campus&data&refeicao`,
`GET /avaliacoes/resumo/?campus`, `POST /avaliacoes/`, `POST /recuperar-senha/` e
`POST /redefinir-senha/`. Valores usados: `campus` ∈ `darcy, ceilandia, gama, planaltina,
fal`; `refeicao`/`tipo` ∈ `cafe, almoco, jantar`; datas em `AAAA-MM-DD`.

Os links enviados por e-mail devem apontar para `/confirmar-email?token=...` e
`/redefinir-senha?token=...` no frontend.
