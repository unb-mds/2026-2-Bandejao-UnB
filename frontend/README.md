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
npm run lint       # oxlint + eslint
npm run build      # build de produção em dist/
```

### Backend simulado × API real

Enquanto a API Django não expõe todos os endpoints, o app usa, **só em desenvolvimento e nos
testes**, um **backend simulado** (`src/services/mock/`). Nas rotas de cadastro, confirmação,
reenvio e sessão ele segue o contrato OpenAPI v1 (`backend/openapi.yaml`, BE-03): mesmas
rotas, nomes de campos, status e `codigo`. O build de produção (`npm run build`) não inclui o
simulado e sempre fala com a API real. Os dados de demonstração (contas, avaliações) ficam no
`localStorage` do navegador.

- Conta de demonstração: matrícula `231034567` / senha `bandejao123`.
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
cookie HttpOnly do Django (ADR 0007, nada de token no JavaScript) e apenas campus e filtros
são persistidos no aparelho. O `apiClient` manda `X-CSRFToken` (lido do cookie `csrftoken`)
em POST, PUT, PATCH e DELETE, limpa o `authStore` quando recebe 401 e transforma erros em
`ApiError` com `status`, `codigo` e `mensagem`.

## Contrato da API

O contrato oficial é o **OpenAPI v1** em `backend/openapi.yaml` (BE-03). Erros vêm como
`{ "codigo": "snake_case", "mensagem": "texto para o usuário" }`. Rotas que o MVP já usa,
todas sob `/api`:

| Método e rota | Corpo | Respostas |
|---|---|---|
| `POST /cadastro/` | `{ tipoUsuario: estudante\|professor_servidor, emailInstitucional, senha, apelido?, matriculaSiape?, aceitePrivacidade }` | `201 { emailInstitucional, status: "pendente" }`, `409 { codigo: apelido_indisponivel, apelidoSugerido }`, `422 dados_invalidos` |
| `POST /confirmar-email/{token}/` | — | `200`, `410 token_invalido_ou_expirado` |
| `POST /reenviar-confirmacao/` | `{ matriculaSiape }` ou `{ token }` | `200` (resposta sempre igual), `422 dados_invalidos` |
| `POST /sessao/` (login) | `{ matriculaSiape, senha }` | `200 { apelido, tipo, avisoPrivacidadePendente }`, `401 credenciais_invalidas`, `403 conta_nao_confirmada`, `429 login_bloqueado` |
| `GET /sessao/` (quem sou) | — | `200 { apelido, tipo, avisoPrivacidadePendente }`, `401 nao_autenticado` |
| `DELETE /sessao/` (logout) | — | `204`, `401 nao_autenticado` |

Qualquer rota logada sem sessão responde `401 { codigo: "nao_autenticado" }`. Escrita com
sessão e sem `X-CSRFToken` responde `403` (não desloga).

Ainda no formato do MVP no simulado (entram no contrato nas tarefas FE-08, FE-09 e FE-E2):
`GET /cardapio/{campus}/`, `GET /avaliacoes/?campus&data&refeicao`,
`GET /avaliacoes/resumo/?campus`, `POST /avaliacoes/`, `POST /recuperar-senha/` e
`POST /redefinir-senha/`. Valores usados: `campus` ∈ `darcy, ceilandia, gama, planaltina,
fal`; `refeicao`/`tipo` ∈ `cafe, almoco, jantar`; datas em `AAAA-MM-DD`.

Os links enviados por e-mail devem apontar para `/confirmar-email?token=...` e
`/redefinir-senha?token=...` no frontend.
