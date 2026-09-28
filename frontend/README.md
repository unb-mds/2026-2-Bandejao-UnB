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

Enquanto a API Django não expõe todos os endpoints, o app usa um **backend simulado**
(`src/services/mock/`) que responde às mesmas rotas e aplica as mesmas regras de negócio do
MVP. Os dados de demonstração (contas, avaliações) ficam no `localStorage` do navegador.

- Conta de demonstração: `231034567@aluno.unb.br` / `bandejao123`.
- Onde o sistema real enviaria um e-mail (confirmação de cadastro, redefinição de senha), a
  tela mostra um quadro "Modo demonstração" com o link, para seguir o fluxo inteiro.

Para usar a API real, crie `frontend/.env.local`:

```sh
VITE_USE_MOCK=false
VITE_API_URL=http://localhost:8000/api   # padrão: /api
```

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
├── stores/          Pinia: auth (em memória), preferencias (localStorage), cardapio, avaliacoes
├── utils/           datas e regras de exibição do cardápio (filtros, refeição padrão)
└── views/           uma view por tela
```

Segue o C4 nível 3/4 do frontend: nenhuma view chama a API diretamente, a sessão fica só em
memória e apenas campus e filtros são persistidos no aparelho.

## Contrato da API esperado

Formato que o backend simulado implementa e que a API Django deve seguir. Erros devolvem
`{ "detail": "mensagem para o usuário", "codigo"?: "..." }`.

| Método e rota | Corpo / parâmetros | Respostas |
|---|---|---|
| `GET /cardapio/{campus}/` | — | `200 { campus, semana: {inicio, fim}, publicado, dias: [{ data, refeicoes: [{ tipo, alergenosIndisponiveis, categorias: [{ rotulo, dieta, pratos: [{ nome, marcadores }] }] }] }] }` |
| `GET /avaliacoes/?campus&data&refeicao` | — | `200 { media, quantidade, avaliacoes: [{ id, apelido, nota, comentario, criadaEm }], minha }` |
| `GET /avaliacoes/resumo/?campus` | — | `200 { media, quantidade, dias: [{ data, media, quantidade }] }` |
| `POST /avaliacoes/` | `{ campus, data, refeicao, nota, comentario }` | `201` nova, `200` editada, `401`, `422 { codigo: fora_do_dia \| antes_do_inicio }` |
| `POST /cadastro/` | `{ tipo: estudante\|servidor, email, senha, apelido?, siape?, aceitouPrivacidade }` | `201 { email, pendente }`, `409 { codigo: apelido_manual }`, `422` |
| `POST /confirmar-email/` | `{ token }` | `200`, `410` |
| `POST /reenviar-confirmacao/` | `{ email }` | `200` (resposta sempre igual) |
| `POST /login/` | `{ email, senha }` | `200 { token, usuario: { apelido, tipo } }`, `401`, `403 { codigo: email_nao_confirmado }`, `429` |
| `POST /logout/` | — | `200` |
| `POST /recuperar-senha/` | `{ email }` | `200` (resposta sempre igual), `429` |
| `POST /redefinir-senha/` | `{ token, senha }` | `200`, `410`, `422` |

Valores usados: `campus` ∈ `darcy, ceilandia, gama, planaltina, fal`; `refeicao`/`tipo` ∈
`cafe, almoco, jantar`; `dieta` ∈ `todas, padrao, ovolacto, vegano`; marcadores ∈ `cogumelo,
leite, mel, pimenta, soja, trigo, amendoim, oleaginosa, ovo, suino`; datas em `AAAA-MM-DD`.
O token de sessão vai no cabeçalho `Authorization: Token <token>`.

Os links enviados por e-mail devem apontar para `/confirmar-email?token=...` e
`/redefinir-senha?token=...` no frontend.
