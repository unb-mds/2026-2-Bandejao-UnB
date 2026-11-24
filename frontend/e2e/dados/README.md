# Dados dos testes de ponta a ponta (FE-18)

Carregados pelo `npm run e2e:dados` (e pelo `globalSetup` do Playwright), depois das fixtures
da BD-03 (`campi` e `marcadores`). Datas e horários combinam com o relógio do backend no
`e2e/docker-compose.yml`: segunda-feira, 23/11/2026, 12h em Brasília.

| Arquivo | O que tem | Para quê |
|---|---|---|
| `cardapio.json` | A semana de 23/11 do Gama (campus 3), com refeições de segunda a sexta (23/11 a 27/11): `FonteCardapio`, refeições, categorias, pratos e marcadores | M3 (cardápio e filtros) e a refeição avaliada no M3 |
| `contas.json` | Oito contas confirmadas (`e2e_*`, matrículas `260000101` a `260000108`, senha `senha-e2e-2026`), uma por teste e por projeto (celular e desktop) nos fluxos M2 (no RU e longe dele), M3 e M4; pontos das contas do M4; check-in de hoje das contas do M3 | M2, M3 e M4 entram sem passar pelo e-mail; o M1 cria a própria conta pela tela |
| `historico-fila.json` | 162 check-ins sem usuário no almoço do Gama em 02/11, 09/11 e 16/11, com pico às 12h e tempos de espera | Previsão de pico do M4 (RF13: 3 dias distintos nas 4 semanas anteriores) |

## Como foram gerados

Com o próprio Django, num SQLite descartável (`DB_ENGINE=sqlite`), para as senhas saírem com o
hash certo e os campos derivados (`apelido_normalizado`, e-mail em minúsculas) preenchidos:

- **Cardápio:** o `CardapioPDFParser` leu o PDF de teste
  `backend/apps/cardapio/tests/fixtures/cardapios/Gama-Semana-02-23-11-a-29-11.pdf`, e o
  `CardapioRepository` gravou as refeições do Gama; depois, uma `FonteCardapio` da semana
  (sem ela, a semana aparece como "não publicada", RF07.3) e o `dumpdata` desses modelos.
- **Contas:** `Usuario` com `set_password`, `PontuacaoUsuario` e `PontosSemestreCampus` (160
  pontos no semestre `2026.2`) para as contas do M4, e o check-in das 11h40 de 23/11 para as
  contas do M3.
- **Histórico da fila:** `Checkin` sem usuário (como ficam depois da retenção, RNF07.3) em cada
  faixa de 15 minutos do almoço.

Para mudar a data, troque o `FAKETIME` do `docker-compose.yml`, o `AGORA` de
`e2e/apoio/teste.js` e as datas destes arquivos juntos.
