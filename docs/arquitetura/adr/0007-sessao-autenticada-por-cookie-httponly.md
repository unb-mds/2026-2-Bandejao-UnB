# ADR 0007 — Sessão autenticada por cookie HttpOnly

**Status:** Aceita
**Data:** 2026-09-28
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

O Usuário se autentica com matrícula/SIAPE e senha (RF03) para avaliar refeições (RF15) e fazer check-in (RF11). O C4 do frontend (Nível 3b) propunha guardar o token de sessão **só em memória**, no `authStore`. Com isso, a sessão se perde a cada recarga de página e cada vez que o PWA instalado é reaberto, o que vai contra:

- o caráter PWA e mobile-first do produto (RNF05): o app instalado é fechado e reaberto o tempo todo pelo sistema operacional do celular;
- a usabilidade para quem tem pouco tempo (RNF03, Visão 3.4): pedir login toda vez que alguém abre o app para avaliar a refeição reduz o número de avaliações.

A alternativa óbvia, guardar um token em `localStorage`, deixa o token legível por qualquer script da página. Um único XSS (por exemplo, num comentário de avaliação mal escapado) permitiria roubar sessões (RNF04).

O backend é Django REST Framework (ADR 0001), que já traz autenticação por sessão pronta (`SessionAuthentication`), sessões guardadas no banco e proteção CSRF.

## Decisão

A autenticação da API usa a **sessão do Django em cookie**, e não token.

- O cookie de sessão é `HttpOnly` (inacessível a JavaScript), `Secure` (só HTTPS) e `SameSite=Lax`.
- A sessão fica guardada no banco (`django_session`), o que permite encerrá-la pelo servidor.
- **Duração:** 14 dias, renovada a cada uso (`SESSION_COOKIE_AGE`, `SESSION_SAVE_EVERY_REQUEST`). O valor passa a ser parâmetro configurável do Anexo A.
- **CSRF:** requisições que alteram estado (POST, PUT, PATCH, DELETE) enviam o token CSRF do Django num cabeçalho. O `apiClient` do frontend é o único ponto que faz isso.
- **Rotas de sessão:** `POST /api/sessao/` (login), `DELETE /api/sessao/` (logout) e `GET /api/sessao/` (quem sou eu: devolve só apelido e tipo de usuário, nunca matrícula/SIAPE ou e-mail, RI10). Os nomes finais ficam no contrato OpenAPI.
- **`authStore`** não guarda token. Ao abrir o app, ele chama `GET /api/sessao/` para saber se há sessão e guarda só o apelido e o tipo de usuário.
- **Redefinição de senha encerra todas as sessões** da conta (RF04). O Django já faz isso ao trocar a senha, porque cada sessão guarda um hash derivado da senha e deixa de valer quando ela muda.
- **Conta suspensa ou removida** (ADR 0004) é mapeada para `is_active = False`. Com isso, o login é recusado e as sessões já abertas deixam de autenticar na próxima requisição.
- **PWA e API no mesmo domínio** (por exemplo, `bandejao.exemplo/` e `bandejao.exemplo/api/`), para o cookie `SameSite` funcionar sem CORS com credenciais. É requisito para a escolha de hospedagem (SP-02).

## Consequências

- A sessão sobrevive a recargas e à reabertura do PWA, sem expor credencial a JavaScript.
- Não é preciso implementar emissão, renovação nem revogação de token: o Django já cobre isso, o que é importante para uma equipe iniciante com prazo curto.
- Surge a necessidade de tratar CSRF no frontend, concentrada no `apiClient`.
- A hospedagem precisa servir o PWA e a API sob o mesmo domínio. Se não der, será preciso configurar CORS com `credentials` e `SameSite=None`, o que é mais frágil, e esta ADR deve ser revista.
- Sessões ficam no banco e aumentam uma tabela. É preciso rodar `clearsessions` periodicamente, no mesmo agendador do leitor de cardápio (ADR 0003).
- O C4 do frontend (nota sobre `authStore` e tabela de stores) e o Nível 4 de Cadastro/Autenticação (`Sessao`, `LoginService`) precisam ser atualizados.
- Fica criada a história de **logout** (US-03.3), que os requisitos não previam.

## Alternativas consideradas

- **Token só em memória** (proposta anterior do C4 do frontend): seguro contra XSS persistente, mas perde a sessão a cada recarga. Descartada pela usabilidade.
- **Token (DRF `TokenAuthentication` ou JWT) em `localStorage`:** sobrevive a recargas, mas fica exposto a XSS e não tem revogação simples (JWT). Descartada por segurança (RNF04).
- **JWT em cookie HttpOnly:** tão seguro quanto a decisão adotada, mas exige biblioteca extra, lógica de renovação e lista de revogação para cumprir o RF04. Descartada por complexidade sem ganho para o projeto.

## Relacionadas

- Requisitos: RF03, RF04, RF05, RNF03, RNF04, RNF05, RI10.
- `docs/adr/0001-escolha-stack-backend.md` (DRF, autenticação integrada).
- `docs/adr/0004-acesso-direto-da-equipe-ao-banco.md` (conta suspensa ou removida).
- `c4-niveis-3-4-frontend-bandejao.md` (`authStore`, `apiClient`).
- `c4-nivel-4-cadastro-autenticacao.md` (`LoginService`, `Sessao`).
