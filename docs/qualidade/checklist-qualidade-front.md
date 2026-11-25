# Checklist de qualidade do front (FE-16, QA-07)

Confere os requisitos de usabilidade e compatibilidade do front antes do teste com usuários: funcional a partir de 360 px e no desktop (RNF03 e FE-20, [#169](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/169)), guia de estilo (RF17), até 3 interações até o cardápio na primeira visita (RNF03) e as duas versões mais recentes de Chrome, Firefox, Edge e Safari (RNF05).

Legenda: ✅ atende · ❌ não atende (bug aberto) · ⚠️ atende com ressalva · ⏸ pendência de um EXTRA · ⬜ a conferir no aparelho.

## Como foi conferido

- **Versão do front:** `develop` de 24/11/2026, com a FE-19 (#280).
- **Larguras:** celular 360×800, com toque; tablet 768×1024; desktop 1366×768 (FE-20).
- **Navegador:** Chromium 157, pelo Playwright. É o motor do Chrome e do Edge, mas não substitui as versões de marca deles; Firefox e Safari não rodam no ambiente da conferência. Os quatro ficam na seção 4, para conferir no aparelho.
- **"Passa da largura":** algum elemento da tela vai além da borda direita da janela. A largura do documento não serve de medida, porque o app corta o que passa e rola o conteúdo dentro da própria tela, sem que a página fique mais larga. As abas dos dias, que rolam para o lado de propósito, ficam de fora (`data-rolagem-horizontal`).
- **Onde cada item foi conferido:**
  - **Servidor simulado do front** (`npm run dev`): todas as telas da seção 1, nas três larguras, sem login e com a conta de demonstração, e a contagem da seção 2.
  - **Testes de ponta a ponta** `frontend/e2e/qualidade.spec.js`, na pilha real (PWA, API e MySQL), no job `ponta-a-ponta`, nos projetos celular e desktop: a seção 2 e a seção 1 sem login (todas as telas da tabela) e com login (tela do campus, Início, Avaliações, Ranking e Meu progresso). Cada tela só é medida depois de o conteúdo aparecer, e um teste de controle confere que o detector acusa um elemento largo de propósito.
  - **Só no servidor simulado:** a coluna do tablet (o Playwright do projeto não tem projeto tablet) e as telas Seletor de campus, Entrar, Criar conta, Confirmar e-mail, Recuperar senha, Redefinir senha e Página não encontrada com login.

## 1. Funcional a partir de 360 px e no desktop (RNF03, FE-20)

Nenhum elemento passa da largura da janela, e o conteúdo aparece inteiro, sem sobreposição. As telas com login foram abertas com uma sessão ativa.

| Tela | Rota | Celular (360 px) | Tablet (768 px) | Desktop (1366 px) |
|---|---|---|---|---|
| Boas-vindas | `/boas-vindas` | ✅ | ✅ | ✅ |
| Seletor de campus | `/campus` | ✅ | ✅ | ✅ |
| Tela do campus (cardápio, avaliações e fila) | `/campus/:campusId` | ⚠️ (observação 1) | ✅ | ✅ |
| Início | `/inicio` | ✅ | ✅ | ✅ |
| Avaliações | `/avaliacoes` | ✅ | ✅ | ✅ |
| Ranking | `/ranking/:campusId` | ✅ | ✅ | ✅ |
| Meu progresso, sem login e com login | `/progresso` | ✅ | ✅ | ✅ |
| Entrar | `/login` | ✅ | ✅ | ✅ |
| Criar conta | `/cadastro` | ✅ | ✅ | ✅ |
| Confirmar e-mail | `/confirmar-email` | ✅ | ✅ | ✅ |
| Recuperar senha | `/recuperar-senha` | ✅ | ✅ | ✅ |
| Redefinir senha | `/redefinir-senha` | ✅ | ✅ | ✅ |
| Página não encontrada | qualquer outra | ✅ | ✅ | ✅ |

**Observação 1:** a 360 px, o rótulo "Café da manhã" do seletor de refeição fica a 4 px da borda do cartão do cardápio. Não corta nem passa da largura, mas fica apertado. A 320 px, abaixo do mínimo do RNF03, encosta na borda.

## 2. Até 3 interações até o cardápio (RNF03)

Primeira visita, sem conta, contando os toques no aviso de localização (RF19) e o pedido do navegador, como manda o RNF03 da Release 2: *com permissão, são 2 interações até o cardápio do campus detectado; sem permissão, "Agora não" e a escolha do campus também somam 2*.

| Caminho | Interações | Celular | Desktop |
|---|---|---|---|
| Sem permissão: "Agora não" → campus | 2 | ✅ | ✅ |
| Com permissão: "Permitir localização" → pedido do navegador → campus | 3 (a Release 2 prevê 2) | ⏸ (pendência 1) | ⏸ (pendência 1) |
| Visita seguinte (campus lembrado, RN04) | 0 | ✅ | ✅ |

As duas causas são diferentes:

- **Sem permissão (bug 1, corrigido na #285):** a interação a mais era o "Continuar sem login" da boas-vindas, entre o "Agora não" e a escolha do campus. A boas-vindas passou a ter a escolha do campus no lugar dele, e o caminho fica em 2 interações, como pede a Release 2.
- **Com permissão (pendência 1):** a detecção do campus pela localização (RF20.1, FE-E3) é EXTRA 3 e não foi feita. Por isso, permitir a localização não leva ao campus em que a pessoa está, e o caminho segue o mesmo do sem permissão, com o pedido do navegador a mais. Só a FE-E3 leva esse caminho às 2 interações.

Só o caso com permissão está marcado no `qualidade.spec.js` com `test.fail()`: quando a FE-E3 entrar, o teste acusa, para este checklist ser atualizado. O caso sem permissão é um teste comum.

## 3. Guia de estilo (RF17)

O guia são os tokens de `frontend/src/assets/base.css` (paleta, tipografia, raios e larguras), que o próprio arquivo manda usar em todas as telas, sem cor solta.

| Item | Celular | Desktop |
|---|---|---|
| Paleta: as cores da marca, do texto e do feedback vêm dos tokens | ✅ (validação automatizada; PR #290) | ✅ (validação automatizada; PR #290) |
| Tipografia: títulos em `--fonte-titulo` (Nunito) e texto em `--fonte-texto` (Inter), sem `font-family` solta | ✅ | ✅ |
| Raios: escala semântica (`--raio-2xs` a `--raio-xl`), tokens numéricos, círculo (`50%`) e pílula (`999px`) | ✅ (validação automatizada; PR #290) | ✅ (validação automatizada; PR #290) |
| Larguras: no desktop, a lateral de 246 px (`--largura-lateral`) e o conteúdo na largura que sobra; formulários de conta com 470 px (tablet: cartão até `--largura-formulario`, 480 px) | não se aplica | ✅ |
| Navegação: `NavegacaoInferior` no celular, `NavegacaoTopo` de 768 a 1023 px e `BarraLateral` a partir de 1024 px (FE-23). Perfil leva a Meu progresso no celular e no tablet (#297); no desktop, o atalho de conta leva a Meu progresso para usuários autenticados e ao login para visitantes, sem duplicar o Perfil no menu principal | ✅ | ✅ |
| Foco visível (`:focus-visible`), dourado sobre o verde | ✅ | ✅ |
| Mesma distribuição de informação entre as telas: cabeçalho verde nas telas internas (no desktop, a Início tem a barra do topo clara) e cartões em `--cartao` sobre o bege (no desktop, o creme) | ✅ | ✅ |

**Bug 2 (baixa prioridade):** correção implementada no [PR #290](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/290), com validação automatizada local aprovada (13/13 testes do guia de estilo, 1.131/1.131 testes da suíte completa em 44 arquivos, lint e build). As cores e raios identificados foram substituídos por tokens; o teste-guarda verifica as formas de declaração documentadas no próprio teste. O AppLogo também é verificado pelo teste-guarda. A guarda detecta usos incorretos de tokens de sombra completa e tokens duplicados no base.css.

## 4. Navegadores (RNF05)

As duas versões mais recentes de cada navegador, no celular e no desktop. Em cada um: abrir o app, chegar ao cardápio pela primeira visita, trocar de dia e de refeição, aplicar um filtro, entrar com uma conta e abrir Meu progresso e o Ranking. A instalação do PWA é conferida na FE-14.

| Navegador | Versão | Celular | Desktop |
|---|---|---|---|
| Chromium 157 (Playwright, conferência automática) | — | ✅ | ✅ |
| Chrome | última | ⬜ | ⬜ |
| Chrome | penúltima | ⬜ | ⬜ |
| Edge | última | ⬜ | ⬜ |
| Edge | penúltima | ⬜ | ⬜ |
| Firefox | última | ⬜ | ⬜ |
| Firefox | penúltima | ⬜ | ⬜ |
| Safari (iOS no celular, macOS no desktop) | última | ⬜ | ⬜ |
| Safari (iOS no celular, macOS no desktop) | penúltima | ⬜ | ⬜ |

Preencher com o número da versão, quem conferiu e a data. Problema encontrado vira issue, com o link na célula.

## 5. Bugs e pendências

| Achado | Requisito | Situação |
|---|---|---|
| Bug 1. Sem permitir a localização, a primeira visita levava 3 interações até o cardápio, e a Release 2 prevê 2 ("Continuar sem login" a mais) | RNF03 | #285, corrigido no PR #289 |
| Bug 2. Cores e raios fora dos tokens do guia de estilo | RF17 | #286 — correção no PR #290, validação automatizada aprovada |
| Pendência 1. Com a localização permitida, 3 interações até o cardápio, porque a detecção do campus não foi feita | RNF03, RF20.1 | EXTRA 3 (FE-E3), sem issue nesta release |
