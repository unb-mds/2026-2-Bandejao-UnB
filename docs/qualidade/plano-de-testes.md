# Plano de Testes — Bandejão (Release 2)

> **Vale para:** backend (Django/DRF) e frontend (Vue 3 + Pinia), sem exceção. Cada tipo de teste abaixo tem a sua forma no back e no front.
> **Requisito:** RNF06 (Documento de Requisitos). **Decisão:** ADR 0013. **Fonte das metas:** plano de ensino de MDS 2026/2, seção "No lugar da métrica de cobertura".
> **Método:** TDD (vermelho → verde → refatorar) para os testes e para o pipeline de CI.

---

## 1. Metas (portas de qualidade)

O plano de ensino trata a cobertura como **piso, não como prova de qualidade**. Por isso a qualidade da suíte é medida por quatro metas, que valem para o back e para o front. Todas são conferidas no CI, e um PR que não as cumpre não entra na `develop`.

| Métrica | Meta | Onde | Como se confere |
|---|---|---|---|
| Cobertura de linhas | **≥ 70%** | Módulos críticos (seção 2) | `coverage.py` (back) e `@vitest/coverage-v8` (front), com o CI falhando abaixo da meta |
| Escore de mutação | **≥ 50%** | Módulos críticos | `mutmut` (back) e StrykerJS (front) |
| Teste de sabotagem | **100%** dos módulos críticos | Módulos críticos | Defeito proposital em cada módulo; a suíte tem que quebrar. Registro na seção 6 |
| Achados críticos/altos em SAST | **0 em aberto** | Todo o código e as dependências | `bandit`, Semgrep, `pip-audit` e `npm audit` |

A cobertura de ramos (branches) também sai no relatório, para orientar a revisão, mas não bloqueia o PR.

**Porta de qualidade da entrega:** a nota da Release 2 só é lançada com o software implantado e acessível, o **CI verde no commit da entrega** e **nenhuma vulnerabilidade crítica ou alta** em aberto (plano de ensino, Condições de Aprovação).

---

## 2. Módulos críticos

São os do RNF06, no que entrou na R2. São eles que precisam cumprir as metas de cobertura, mutação e sabotagem. O resto do código também é testado, mas sem meta numérica.

| Módulo | Backend (app ou pacote) | Frontend |
|---|---|---|
| Cadastro e autenticação | `apps/cadastro` | `stores/auth.js`, validações do cadastro, guardas do `router` |
| Leitura do cardápio (com os ícones) | `apps/cardapio/leitor` | — |
| Exposição do cardápio e filtros | `apps/cardapio` (serviços de consulta e filtros) | `stores/cardapio.js`, `utils/cardapio.js` |
| Avaliação | `apps/avaliacao` | `stores/avaliacoes.js` |
| Fila (check-in, previsão) | `apps/fila` | `filaStore`, `CheckinBotao`, `FilaPrevisao` |
| Gamificação (pontos, patente, ranking) | `apps/gamificacao` | `gamificacaoStore` |
| Comunicação com a API | — | `services/apiClient.js` |

Se um extra entrar (EXTRA 1, 3 ou 7), o módulo dele entra nesta tabela no mesmo PR.

---

## 3. Tipos de teste

Cada tipo diz **o que** testa, **como** é feito no back e no front, e **quando** roda.

### 3.1 Unitário

Uma regra isolada, sem banco, sem rede e sem tela.

| | Backend | Frontend |
|---|---|---|
| Alvo | Validators, policies, resolvers e serviços (`MatriculaValidator`, `PontuacaoPolicy`, `DistanciaGeografica`, `HorarioRefeicaoResolver`, `CardapioEstruturador.separarPratos`…) | Funções de `utils/`, getters e actions das stores com a API simulada |
| Ferramenta | `pytest` | `vitest` |
| Quando | Todo PR | Todo PR |

### 3.2 Integração

Várias partes juntas, com banco ou com a API simulada.

| | Backend | Frontend |
|---|---|---|
| Alvo | View + serializer + serviço + model + banco, pelo `APIClient` do DRF. Transações, constraints (`UNIQUE`, `CHECK`) e `select_for_update` | Store + `apiClient` + servidor simulado (`services/mock/`). Roteador + guardas + `authStore` |
| Ferramenta | `pytest-django` com SQLite em todo PR e **MySQL 8** quando há migration (BD-02) | `vitest` |
| Quando | Todo PR | Todo PR |

### 3.3 Interface

No back, "interface" é a **interface de programação** (o contrato da API). No front, é a **interface gráfica** (o que o usuário vê e toca).

| | Backend — contrato da API | Frontend — interface gráfica |
|---|---|---|
| Alvo | Cada resposta segue o contrato OpenAPI (BE-03): campos, tipos, formato de erro com `codigo`, nenhum campo além do previsto | Componentes montados com `@vue/test-utils`: o texto, o botão e a mensagem que aparecem em cada estado (carregando, vazio, erro, sucesso). O teste procura pelo texto ou pelo papel do elemento, não por classes CSS |
| Ferramenta | `drf-spectacular --validate` e um teste que gera o contrato e compara com o arquivo do repositório (contrato desatualizado = CI vermelho) | `vitest` + `@vue/test-utils` |
| Quando | Todo PR | Todo PR |

### 3.4 Sistema

O sistema inteiro implantado, conferido contra os requisitos **não funcionais**.

| Requisito | Teste | Item do backlog |
|---|---|---|
| RNF01 — 3 s no p95 com 2.000 usuários | Teste de carga do cardápio e da previsão | BD-14 |
| RNF02 — 95% de disponibilidade | Monitor das 7h às 19h30 | BD-09 |
| RNF03 — 3 interações, 360 px | Checklist em celular real | FE-16, QA-07 |
| RNF05 — navegadores e PWA instalável | Chrome, Firefox, Edge e Safari; Lighthouse | FE-14, QA-07 |
| RNF07 — retenção de 4 semanas | Teste com registros de 5 semanas | BD-11 |

### 3.5 Ponta a ponta (End-to-End)

Um navegador de verdade fazendo os fluxos do usuário, com PWA, API e banco rodando juntos (`docker compose`).

| Fluxo | Começa em |
|---|---|
| Cadastro → confirmação do e-mail → login → logout | M1 |
| Login → aviso de privacidade → check-in no RU (com a localização simulada pelo Playwright) | M2 |
| Tela do campus → cardápio → filtro de dieta e de marcador | M3 |
| Avaliar e editar a avaliação → "+N pontos" | M3 |
| Previsão de pico, progresso e ranking | M4 |

- **Ferramenta:** Playwright (a pasta `frontend/e2e/` já está excluída do vitest).
- **Quando:** todo PR para a `develop` que mexe no back ou no front, e de novo na `main`. Os testes manuais em produção (BD-08, QA-04, QA-09) continuam e não substituem estes.

### 3.6 Segurança

| | Backend | Frontend |
|---|---|---|
| SAST | `bandit` e Semgrep (regras de Python e Django) | Semgrep (regras de JavaScript e Vue) e a regra `vue/no-v-html` do ESLint |
| Dependências | `pip-audit` | `npm audit --audit-level=high` |
| Testes automatizados | Teste da ADR 0008 (nenhuma matrícula, SIAPE ou e-mail em resposta pública ou log); cookie `HttpOnly`, `Secure`, `SameSite=Lax`; escrita sem CSRF recusada (403); bloqueio após 5 tentativas de login; comentário com `<script>` gravado como texto; nenhuma coordenada gravada ou logada (RI09); rotas sensíveis sem o corpo no log | `apiClient` manda `X-CSRFToken` em toda escrita; 401 limpa o `authStore`; nenhum token, coordenada ou campo de formulário no `localStorage`; comentário com HTML aparece como texto |
| Quando | Todo PR | Todo PR |

A **dependência inventada** (slopsquatting: um agente sugere um pacote que não existe ou tem nome parecido com um real) é conferida na revisão: toda dependência nova no `requirements.txt` ou no `package.json` precisa ter o link do pacote oficial na descrição do PR.

### 3.7 Mutação

A ferramenta altera o código de propósito (troca `<=` por `<`, `True` por `False`, apaga uma linha) e roda a suíte. Cada alteração é um **mutante**. Se algum teste falha, o mutante foi **morto**. O **escore de mutação** é a porcentagem de mutantes mortos.

| | Backend | Frontend |
|---|---|---|
| Ferramenta | `mutmut` (usa o `pytest`) | StrykerJS com `@stryker-mutator/vitest-runner` |
| Alvo | Módulos críticos (seção 2) | Módulos críticos (seção 2) |
| Meta | ≥ 50% | ≥ 50% |
| Quando | Nos PRs que mexem em módulo crítico, só nos arquivos alterados (modo incremental), e toda semana na base inteira | Igual ao back |

Um mutante que sobrevive é um teste que falta, ou um teste sem asserção real. O relatório mostra a linha e a troca feita.

### 3.8 Sabotagem

É a mutação feita à mão, com um defeito que **faz sentido no domínio**. Para cada módulo crítico, alguém que **não escreveu** os testes dele coloca um defeito realista numa branch descartável e roda a suíte. A suíte tem que quebrar. Exemplos:

| Módulo | Sabotagem | Teste que tem que quebrar |
|---|---|---|
| `fila` | Aceitar o check-in a 1 m além do raio do RU | Distância na borda (BE-09) |
| `gamificacao` | Dar os 10 pontos duas vezes no mesmo check-in | Pontos uma vez só (BE-14) |
| `avaliacao` | Mostrar a avaliação com `oculta = True` | Avaliação oculta (BE-13) |
| `cadastro` | Devolver o e-mail no `GET /api/sessao/` | Teste da ADR 0008 |
| `leitor` | Ignorar o ícone de um marcador | `MarcadorIconMatcher` com o PDF real (BE-12) |
| `filaStore` | Guardar as coordenadas na store | Store sem coordenadas (FE-05) |
| `apiClient` | Não mandar o `X-CSRFToken` no `DELETE` | CSRF nas escritas (FE-01) |

O resultado vai para o registro da seção 6. Se a suíte **não** quebrar, o teste que falta é escrito e a sabotagem é repetida.

### 3.9 Propriedades

Em vez de um exemplo fixo, o teste descreve uma regra que vale para **qualquer** entrada, e a ferramenta gera centenas de casos (e encolhe o caso que falhou até o menor exemplo).

| | Backend | Frontend |
|---|---|---|
| Ferramenta | `hypothesis` | `fast-check` |
| Propriedades | A distância de A a B é igual à de B a A e nunca negativa; um ponto no centro do RU sempre é aceito; os pontos totais nunca ficam negativos; registrar a mesma contribuição duas vezes dá o mesmo total (idempotência); a patente nunca regride quando os pontos sobem; na previsão, mais chegadas numa faixa nunca baixam o nível dela; o apelido normalizado não tem acento nem maiúscula, e normalizar duas vezes dá o mesmo resultado | Os filtros nunca devolvem um prato que tem o marcador selecionado; aplicar o mesmo filtro duas vezes dá o mesmo resultado; a distância do front dá o mesmo resultado que a do back nos mesmos pontos (EXTRA 3) |
| Quando | Todo PR | Todo PR |

### 3.10 Testes gerados por IA e falsa confiança

A equipe usa agentes para escrever testes. Um teste gerado pode passar e dar boa cobertura sem testar nada. Cada PR com testes gerados por IA passa pelo checklist abaixo na revisão (QA-03), e o uso fica registrado no `AI-USAGE.md`.

**Checklist do revisor:**

- [ ] Todo teste tem pelo menos uma asserção sobre o **resultado** (valor, status, campo, mensagem), e não só "não deu exceção".
- [ ] A asserção não é tautológica (`assert x == x`, `expect(true).toBe(true)`, comparar o mock com ele mesmo).
- [ ] O teste não simula (mock) a própria unidade que está testando.
- [ ] O valor esperado vem do requisito (Anexo A, RN, critério Dado/Quando/Então), e não de rodar o código e copiar a saída.
- [ ] O teste falha se a linha principal da regra for apagada (sabotagem rápida feita pelo revisor em pelo menos um teste do PR).
- [ ] Nenhuma dependência nova sem link do pacote oficial (slopsquatting).
- [ ] Nenhuma decisão de arquitetura escondida no teste (nome de classe, endpoint ou campo que não está no C4 ou no contrato).

**Apoio automático:** a regra `vitest/expect-expect` do `@vitest/eslint-plugin` (que o front já usa) aponta teste sem `expect`. No back, a mutação (3.7) pega o teste sem asserção, porque ele não mata nenhum mutante.

### 3.11 Testes específicos do tema

O Bandejão tem riscos próprios, que pedem testes próprios:

| Risco do tema | Teste | Back / Front |
|---|---|---|
| O PDF do cardápio muda sem aviso (L05) | **Teste de caracterização** com os PDFs reais guardados como fixture: a saída do leitor é comparada com uma saída conferida à mão. Se o formato mudar, o teste mostra o quê | Back (`leitor`) |
| A associação dos ícones falha (L03) | PDF com a legenda alterada ou sem ícones: publica em texto e marca "sem marcadores" | Back (`leitor`) |
| Regras que dependem de horário e data | Relógio simulado: RN05 (refeição padrão, domingo, refeição encerrada), avaliação até 23h59, faixas de 15 min no fuso `America/Sao_Paulo`, semestre sem data de término | Back (`time-machine`) e front (`vi.useFakeTimers`) |
| Duas requisições ao mesmo tempo | Dois check-ins simultâneos: só um é gravado e só um pontua. Roda no job do MySQL, que tem o bloqueio de verdade | Back |
| Localização (RN03, RI09) | Leitura com precisão ruim ou antiga é recusada antes do envio; coordenadas descartadas em todos os desfechos; RU de outro campus recusado | Back e front |
| Previsão com poucos dados | Abaixo e no mínimo de dias, empate (todas as faixas são pico), faixa zerada, outro dia da semana não conta | Back e front |
| Privacidade (LGPD, RNF07) | Retenção de 4 semanas; conta removida aparece como "usuário removido" e some do ranking; apelido e patente públicos, pontos nunca | Back e front |
| Gamificação incentiva fraude (L13) | Check-in rejeitado não pontua; avaliação sem check-in não pontua; campus errado não pontua | Back |
| PWA usado no celular | Instalável (Lighthouse), funciona a partir de 360 px, sessão sobrevive à reabertura do app | Front (sistema e ponta a ponta) |

---

## 4. TDD

### 4.1 Nos testes

Todo item do backlog segue o ciclo **vermelho → verde → refatorar**:

1. **Vermelho:** escrever o teste a partir do critério de aceite (Dado/Quando/Então) ou da regra de negócio, e ver ele **falhar** pelo motivo certo (não por erro de import).
2. **Verde:** escrever o mínimo de código para o teste passar.
3. **Refatorar:** limpar o código com a suíte verde.

**No histórico do Git**, o ciclo fica visível: o teste entra num commit antes do código (`test(fila): distância na borda do raio`, depois `feat(fila): ConfirmacaoLocalizacaoService`). O revisor confere isso, e isso conta na arguição individual (o plano de ensino diz que o histórico "será lido na sua arguição").

**BDD:** os cenários Dado/Quando/Então do Documento de Requisitos viram testes de API (back) e de ponta a ponta (front). O nome do teste cita o requisito (`test_rf15_editar_avaliacao_nao_da_pontos_em_dobro`).

### 4.2 No pipeline de CI

O pipeline também é feito em TDD. Cada porta de qualidade só é considerada pronta depois de ser vista **barrando** um PR ruim:

| Porta | Vermelho (PR de prova, não é mesclado) | Verde |
|---|---|---|
| Testes | Um teste que falha de propósito | O teste corrigido |
| Lint | Código com import sem uso | Código limpo |
| Cobertura | Um módulo crítico com código sem teste, abaixo de 70% | Teste que cobre o código |
| SAST | Uma senha fixa no código ou um `eval` | Linha retirada |
| Dependências | Uma versão antiga com vulnerabilidade conhecida | Versão atualizada |
| Contrato | Um campo novo na resposta sem atualizar o OpenAPI | Contrato atualizado |
| Mutação | Um teste sem asserção num módulo crítico | Asserção real |

O link do PR de prova vermelho fica na descrição do PR que cria cada porta (BE-02, FE-02, BE-19, FE-17). Depois, o workflow é refatorado (cache de dependências, jobs em paralelo) com tudo verde.

---

## 5. Pipeline de CI (GitHub Actions)

Dois workflows, um por frente, e um de ponta a ponta. Todos rodam em todo PR para a `develop` e para a `main`. A proteção da branch exige todos os jobs verdes para mesclar.

### 5.1 `backend-ci.yml` (BE-02, BD-02, BE-19)

| Job | Comandos | Bloqueia o merge |
|---|---|---|
| `lint` | `ruff check .` e `ruff format --check .` | Sim |
| `testes` | `pytest --cov --cov-branch` com SQLite; depois `coverage report --include=<módulos críticos> --fail-under=70` | Sim |
| `testes-mysql` | Mesma suíte com MySQL 8 `utf8mb4` e READ COMMITTED (BD-02). Obrigatório quando há migration | Sim, quando roda |
| `contrato` | `manage.py spectacular --validate` e comparação com o contrato do repositório | Sim |
| `seguranca` | `bandit -r apps -lll` (falha em severidade alta), Semgrep, `pip-audit` | Sim |
| `mutacao` | `mutmut run` nos arquivos críticos alterados; falha abaixo de 50% | Sim, quando roda |

### 5.2 `frontend-ci.yml` (FE-02, FE-17)

| Job | Comandos | Bloqueia o merge |
|---|---|---|
| `lint` | ESLint e Oxlint **sem `--fix`** (novo script `lint:ci`; o `lint` atual corrige sozinho e esconderia o erro no CI) | Sim |
| `testes` | `vitest run --coverage`, com `coverage.thresholds` de 70% de linhas nos arquivos críticos | Sim |
| `build` | `vite build` | Sim |
| `seguranca` | Semgrep e `npm audit --audit-level=high` | Sim |
| `mutacao` | StrykerJS incremental nos arquivos críticos alterados; falha abaixo de 50% | Sim, quando roda |

### 5.3 `e2e.yml` (FE-18)

| Job | Comandos | Bloqueia o merge |
|---|---|---|
| `ponta-a-ponta` | Sobe PWA, API e banco com `docker compose`, carrega as fixtures (BD-03) e roda o Playwright | Sim, a partir do M2 |

### 5.4 Rodadas agendadas

- **Toda semana** (e antes de 22/11): mutação na base inteira, back e front, para pegar o escore de quem não mexeu em módulo crítico recentemente.
- **Antes da entrega:** o commit da entrega precisa ter todos os workflows verdes (porta da Release 2).

---

## 6. Registro de sabotagem

Preenchido no QA-10. Uma linha por módulo crítico, no back e no front. A meta é 100% das linhas com "Sim" na coluna "Suíte quebrou".

| Módulo | Frente | Sabotagem feita | Suíte quebrou? | Teste que pegou | Quem | Data |
|---|---|---|---|---|---|---|
| `cadastro` | Back | | | | | |
| `cardapio/leitor` | Back | | | | | |
| `cardapio` (filtros) | Back | | | | | |
| `avaliacao` | Back | | | | | |
| `fila` | Back | | | | | |
| `gamificacao` | Back | | | | | |
| `authStore` e guardas | Front | | | | | |
| `cardapioStore` e `utils/cardapio` | Front | | | | | |
| `avaliacoesStore` | Front | | | | | |
| `filaStore`, `CheckinBotao`, `FilaPrevisao` | Front | | | | | |
| `gamificacaoStore` | Front | | | | | |
| `apiClient` | Front | | | | | |

---

## 7. Ferramentas

| Função | Backend | Frontend |
|---|---|---|
| Executor de testes | `pytest`, `pytest-django` | `vitest` |
| Cobertura | `pytest-cov` (`coverage.py`) | `@vitest/coverage-v8` |
| Interface | `drf-spectacular` | `@vue/test-utils` |
| Propriedades | `hypothesis` | `fast-check` |
| Mutação | `mutmut` | `@stryker-mutator/core`, `@stryker-mutator/vitest-runner` |
| Relógio simulado | `time-machine` | `vi.useFakeTimers` |
| Ponta a ponta | — | `@playwright/test` |
| Lint | `ruff` | ESLint, Oxlint |
| SAST | `bandit`, Semgrep | Semgrep |
| Dependências | `pip-audit` | `npm audit` |

As ferramentas de teste do back ficam num `requirements-dev.txt`, separado do `requirements.txt` de produção.
