# Checklist de qualidade do front (FE-16, QA-07)

Confere os requisitos de usabilidade e compatibilidade do front antes do teste com usuários: funcional a partir de 360 px e no desktop (RNF03, FE-20), guia de estilo (RF17), até 3 interações até o cardápio na primeira visita (RNF03) e as duas versões mais recentes de Chrome, Firefox, Edge e Safari (RNF05).

Legenda: ✅ atende · ❌ não atende (bug aberto) · ⚠️ atende com ressalva · ⬜ a conferir no aparelho.

## Como foi conferido

- **Versão do front:** `develop` de 24/11/2026, com a FE-19 (#280).
- **Celular:** 360×800, com toque. **Desktop:** 1366×768. As telas também foram abertas em 768×1024 (tablet, FE-20).
- **Navegador da conferência automática:** Chromium 157 (Playwright), o motor do Chrome e do Edge. Firefox e Safari não rodam no ambiente da conferência e ficam na seção 4, para conferir no aparelho.
- **Dados:** servidor simulado do front (`npm run dev`), com a conta de demonstração para as telas com login. A pilha real (PWA, API e MySQL) é conferida pelos testes de ponta a ponta `frontend/e2e/qualidade.spec.js` no job `ponta-a-ponta`, nos dois projetos (celular e desktop).
- **"Rola para o lado":** a página é mais larga que a janela (`scrollWidth` maior que `clientWidth`). Faixas com rolagem própria, como as abas dos dias, não contam.

## 1. Funcional a partir de 360 px e no desktop (RNF03, FE-20)

Nenhuma tela rola para o lado, e o conteúdo aparece inteiro, sem sobreposição. As telas com login foram abertas com uma sessão ativa.

| Tela | Rota | Celular (360 px) | Desktop (1366 px) |
|---|---|---|---|
| Boas-vindas | `/boas-vindas` | ✅ | ✅ |
| Seletor de campus | `/campus` | ✅ | ✅ |
| Tela do campus (cardápio, avaliações e fila) | `/campus/:id` | ⚠️ (observação 1) | ✅ |
| Início | `/inicio` | ✅ | ✅ |
| Avaliações | `/avaliacoes` | ✅ | ✅ |
| Ranking | `/ranking/:id` | ✅ | ✅ |
| Meu progresso, sem login e com login | `/progresso` | ✅ | ✅ |
| Entrar | `/login` | ✅ | ✅ |
| Criar conta | `/cadastro` | ✅ | ✅ |
| Confirmar e-mail | `/confirmar-email` | ✅ | ✅ |
| Recuperar senha | `/recuperar-senha` | ✅ | ✅ |
| Redefinir senha | `/redefinir-senha` | ✅ | ✅ |
| Página não encontrada | qualquer outra | ✅ | ✅ |

**Observação 1:** a 360 px, o rótulo "Café da manhã" do seletor de refeição fica a 4 px da borda do cartão do cardápio. Não corta nem rola, mas fica apertado. A 320 px, abaixo do mínimo do RNF03, encosta na borda.

## 2. Até 3 interações até o cardápio (RNF03)

Primeira visita, sem conta, contando os toques no aviso de localização (RF19) e o pedido do navegador, como manda o RNF03 da Release 2.

| Caminho | Interações | Celular | Desktop |
|---|---|---|---|
| "Agora não" → "Continuar sem login" → campus | 3 | ✅ no limite de 3; ⚠️ a Release 2 prevê 2 | ✅ no limite de 3; ⚠️ a Release 2 prevê 2 |
| "Permitir localização" → pedido do navegador → "Continuar sem login" → campus | 4 | ❌ (bug 1) | ❌ (bug 1) |
| Visita seguinte (campus lembrado, RN04) | 0 | ✅ | ✅ |

A detecção do campus pela localização (RF20.1, FE-E3) é EXTRA 3 e não foi feita. Por isso, permitir a localização na boas-vindas não leva ao campus, e o caminho com permissão fica com uma interação a mais que o caminho sem ela. A conta de 2 interações da Release 2 depende desse extra.

## 3. Guia de estilo (RF17)

O guia são os tokens de `frontend/src/assets/base.css` (paleta, tipografia, raios e larguras), que o próprio arquivo manda usar em todas as telas, sem cor solta.

| Item | Celular | Desktop |
|---|---|---|
| Paleta: as cores da marca, do texto e do feedback vêm dos tokens | ⚠️ (bug 2) | ⚠️ (bug 2) |
| Tipografia: títulos em `--fonte-titulo` (Nunito) e texto em `--fonte-texto` (Inter), sem `font-family` solta | ✅ | ✅ |
| Raios: `--raio-sm` a `--raio-xl` e o formato de pílula (`999px`) | ⚠️ (bug 2) | ⚠️ (bug 2) |
| Larguras: conteúdo até `--largura-conteudo` (1200 px) e formulários até `--largura-formulario` (480 px) | não se aplica | ✅ |
| Navegação: `NavegacaoInferior` no celular e `NavegacaoTopo` a partir de 768 px, com os mesmos destinos | ✅ | ✅ |
| Foco visível (`:focus-visible`), dourado sobre o verde | ✅ | ✅ |
| Mesma distribuição de informação entre as telas: cabeçalho verde, cartões em `--cartao` sobre o bege | ✅ | ✅ |

**Bug 2 (baixa prioridade):** cores e um raio fora dos tokens. O branco (`#fff`) aparece escrito direto em 18 arquivos, as sombras e os fundos escurecidos dos diálogos usam 9 `rgba(...)` soltos, em 7 arquivos (`AvisoLocalizacao`, `FiltroCardapio`, `BoasVindasView`, `HomeView`, `PontosAviso`, `ProgressoView` e `assets/main.css`), e o campo da `CadastroView` usa raio de 6 px, que não existe nos tokens. Visualmente as telas são coerentes; o que falta é o token. As cores do desenho do `AppLogo` são da ilustração e ficam de fora.

## 4. Navegadores (RNF05)

As duas versões mais recentes de cada navegador, no celular e no desktop. Em cada um: abrir o app, chegar ao cardápio pela primeira visita, trocar de dia e de refeição, aplicar um filtro, entrar com uma conta e abrir Meu progresso e o Ranking. A instalação do PWA é conferida na FE-14.

| Navegador | Versão | Celular | Desktop |
|---|---|---|---|
| Chrome (motor Chromium 157, conferência automática) | — | ✅ | ✅ |
| Chrome | última | ⬜ | ⬜ |
| Chrome | penúltima | ⬜ | ⬜ |
| Edge | última | ⬜ | ⬜ |
| Edge | penúltima | ⬜ | ⬜ |
| Firefox | última | ⬜ | ⬜ |
| Firefox | penúltima | ⬜ | ⬜ |
| Safari (iOS no celular, macOS no desktop) | última | ⬜ | ⬜ |
| Safari (iOS no celular, macOS no desktop) | penúltima | ⬜ | ⬜ |

Preencher com o número da versão, quem conferiu e a data. Problema encontrado vira issue, com o link na célula.

## 5. Bugs abertos

| Bug | Requisito | Issue |
|---|---|---|
| 1. Com a localização permitida, a primeira visita leva 4 interações até o cardápio | RNF03 | #___ |
| 2. Cores e raio fora dos tokens do guia de estilo | RF17 | #___ |
