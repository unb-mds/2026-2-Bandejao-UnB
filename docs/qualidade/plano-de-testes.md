# Plano de Testes — Bandejão (Release 2)

> **Vale para:** backend (Django/DRF) e frontend (Vue 3 + Pinia), sem exceção. Cada tipo de teste abaixo tem a sua forma no back e no front.
> **Requisito:** RNF06 (Documento de Requisitos). **Decisão:** ADR 0013. **Fonte das metas:** plano de ensino de MDS 2026/2, seção "No lugar da métrica de cobertura".
> **Método:** TDD (vermelho → verde → refatorar) para os testes e para o pipeline de CI.

---

## 1. Metas (portas de qualidade)

O plano de ensino trata a cobertura como **piso, não como prova de qualidade**. Por isso a qualidade da suíte é medida por quatro metas, que valem para o back e para o front. Todas são conferidas no CI, e um PR que não as cumpre não entra na `develop`.

| Métrica | Meta | Onde | Como se confere |
|---|---|---|---|
| Cobertura de linhas | **≥ 70%** | Módulos críticos (seção 2), cada um | `coverage.py` (back) e `@vitest/coverage-v8` (front), com o CI falhando abaixo da meta. No back, o CI mede linhas e ramos juntos (`--cov-branch`), com duas casas decimais, sem arredondar a meta para cima |
| Escore de mutação | **≥ 50%** | Módulos críticos | `mutmut` (back) e StrykerJS (front) |
| Teste de sabotagem | **100%** dos módulos críticos | Módulos críticos | Defeito proposital em cada módulo; a suíte tem que quebrar. Registro na seção 6 |
| Achados críticos/altos em SAST | **0 em aberto** | Todo o código e as dependências | `bandit`, Semgrep, `pip-audit` e `npm audit` |

A cobertura de ramos (branches) também sai no relatório, para orientar a revisão. No back, ela entra no percentual que bloqueia o PR: com `--cov-branch`, o `coverage.py` soma linhas e ramos num número só, que costuma ficar abaixo do de linhas. Se um módulo ficar entre os dois (linhas ≥ 70% e o combinado abaixo), o relatório registra os dois.

**Porta de qualidade da entrega:** a nota da Release 2 só é lançada com o software implantado e acessível, o **CI verde no commit da entrega** e **nenhuma vulnerabilidade crítica ou alta** em aberto (plano de ensino, Condições de Aprovação).

---

## 2. Módulos críticos

São os do RNF06, no que entrou na R2. São eles que precisam cumprir as metas de cobertura, mutação e sabotagem. O resto do código também é testado, mas sem meta numérica.

| Módulo | Backend (app ou pacote) | Frontend |
|---|---|---|
| Cadastro e autenticação | `apps/cadastro` | `stores/auth.js`, validações do cadastro, guardas do `router` |
| Leitura do cardápio (com os ícones) | `apps/cardapio/leitor` | — |
| Exposição do cardápio e filtros | `apps/cardapio` sem o leitor (serviços de consulta e filtros, e também views, serializers, models e comandos: a cobertura e a mutação medem o app inteiro menos o `leitor/`) | `stores/cardapio.js`, `utils/cardapio.js` |
| Avaliação | `apps/avaliacao` | `stores/avaliacoes.js` |
| Fila (check-in, previsão) | `apps/fila` | `filaStore`, `services/leituraPosicao.js`, `CheckinBotao`, `FilaPrevisao` |
| Gamificação (pontos, patente, ranking) | `apps/gamificacao` | `gamificacaoStore`, `PontosAviso` |
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
| Ferramenta | `pytest-django` com SQLite e **MySQL 8.4** em todos os PRs para `develop` e `main` (BD-02) | `vitest` |
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
| RNF01 — 3 s no p95 com 2.000 usuários | Teste de carga do cardápio e da previsão ([resultado](teste-de-carga-bd14.md)) | BD-14 |
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
| Avaliar → aviso "+N pontos" (`PontosAviso`); editar → sem aviso | M3 |
| Previsão de pico, progresso e ranking | M4 |

- **Ferramenta:** Playwright (`@playwright/test`, só o Chromium), com dois projetos: celular (360×800, toque) e desktop (1366×768), conforme a FE-20. A pasta `frontend/e2e/` fica fora do Vitest.
- **Quando:** todo PR (job `ponta-a-ponta`, seção 5.3) e todo push na `develop` e na `main`. Os testes manuais em produção (BD-08, QA-04, QA-09) continuam e não substituem estes.
- **Onde rodam:** `frontend/e2e/docker-compose.yml` sobe o PWA de produção no Caddy, a API no Gunicorn e o MySQL 8.4, com as imagens de produção, mais o Mailpit (SMTP de teste). Diferenças para produção: HTTP em `localhost:8080`, cookies sem o flag `Secure`, e-mail no Mailpit e o relógio do backend começando na segunda-feira, 23/11/2026, às 12h de Brasília (libfaketime), a cada subida do container, e andando dali em diante. É o que deixa o check-in e a avaliação dentro do horário do almoço a qualquer hora do dia; o `globalSetup` recria o backend antes de cada rodada, para o relógio voltar ao meio-dia, e o healthcheck do backend confere que ele está no almoço de 23/11 (o que também prova que a libfaketime carregou). O navegador usa o mesmo instante (`page.clock`) e o fuso de Brasília.
- **Dados:** as fixtures da BD-03 (campi e marcadores) e as de `frontend/e2e/dados/`: o cardápio da semana de 23/11 do Gama, gerado pelo leitor de PDF de verdade a partir do PDF de teste do backend; oito contas confirmadas, uma por teste e por projeto (celular e desktop) nos fluxos M2 a M4; e o histórico do almoço do Gama nas três segundas anteriores, para a previsão de pico. Antes de cada rodada, o `globalSetup` limpa o banco e o cache e carrega tudo de novo. O cache guarda os contadores do limite de taxa: com `ATRAS_DE_PROXY_HTTPS=False`, todo pedido conta como o IP do Caddy, e o limite de login estouraria em poucas rodadas seguidas.
- **Contas:** o M1 cria a conta pela tela e lê o link de confirmação na API do Mailpit. Os outros fluxos entram com as contas da fixture, para não depender do e-mail: o M2 com uma conta que aceitou uma versão antiga do aviso de privacidade (o aviso aparece antes do GPS) e outra para o check-in recusado longe do RU, o M3 com uma conta que já fez check-in no almoço (a avaliação só pontua assim, RN09) e o M4 com uma conta de 160 pontos que ainda não participa do ranking.
- **Localização:** a do RU do Gama, pelas permissões e pela geolocalização do contexto do Playwright. Nos fluxos sem GPS, o aviso de localização (RF19) é respondido com "Agora não", como a pessoa faria.

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
| `leitor` | Associar o link do PDF pela posição do bloco na página, e não pelo título do campus | Página do RU com os blocos em outra ordem (BE-12, ADR 0014) |
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
| O PDF do cardápio muda sem aviso (L15) | **Teste de caracterização** com os PDFs reais guardados como fixture: a saída do leitor é comparada com uma saída conferida à mão. Se o formato mudar, o teste mostra o quê | Back (`leitor`) |
| A página de cardápios do RU muda: ordem dos blocos, título ou nome do arquivo (L15) | **Teste de caracterização** com o HTML real da página guardado como fixture (ADR 0014): os blocos em outra ordem dão o mesmo resultado; sufixo `-1`/`-2` no nome do arquivo é aceito; bloco com a semana vigente e a seguinte gera as duas semanas; título ausente ou repetido, arquivo de outro campus, dois links para a mesma semana e dia do PDF fora do intervalo do link mantêm o último cardápio válido e alertam; o Gama com 6 dias num link de 7 é aceito; nome do arquivo com acento ou em minúsculas é aceito; a semana seguinte lida com sucesso não zera o contador de alertas da semana vigente com falha, nem a semana vigente ausente da página zera o contador do "não publicado"; link da semana vigente presente com o PDF falhando gera só o alerta da falha, e não o de "não publicado"; mesma URL e mesmo SHA-256 não leem o PDF de novo | Back (`leitor`) |
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

### 5.1 `backend-ci.yml` (BE-02, BD-02, BE-19, BE-18)

| Job | Comandos | Bloqueia o merge |
|---|---|---|
| `lint` | `ruff check .` e `ruff format --check .` | Sim |
| `testes` | `pytest --cov=apps --cov-branch --cov-fail-under=70` com SQLite; depois `coverage report --include=<módulo> --fail-under=70` para **cada** módulo crítico da seção 2 (o `cardapio` sem o leitor, com `--omit`), com a tabela de cada um no resumo do run (BE-18). O passo mede os seis e só depois falha; ele roda se o `pytest` passou | Sim |
| `testes-mysql` | Mesma suíte com MySQL 8.4 `utf8mb4`, collation `utf8mb4_0900_ai_ci` e isolamento explícito READ COMMITTED (BD-02). Executado em todos os PRs para `develop` e `main`, inclusive os que não alteram migrations | Sim, obrigatório na `develop` |
| `contrato` | `manage.py spectacular --validate` e comparação com o contrato do repositório | Sim |
| `seguranca` | `bandit -r apps config -lll` (falha em severidade alta), Semgrep, `pip-audit` | Sim |
| `mutacao` | `mutmut run` nos arquivos críticos alterados; falha abaixo de 50% | Sim, quando roda |

**Como o job `mutacao` funciona (BE-19):**

- **Configuração:** seção `[mutmut]` do `backend/setup.cfg` (`mutmut` 3.8.1). Mutam os seis módulos críticos da seção 2 (`apps/cadastro`, `apps/cardapio`, com o leitor, `apps/avaliacao`, `apps/fila` e `apps/gamificacao`); ficam fora os testes, as migrations, `admin.py`, `apps.py` e `urls.py`, que não têm regra de negócio a matar. Toda exclusão nova precisa de motivo escrito no `setup.cfg`.
- **Testes usados:** só os de `apps/`. O `mutmut` roda a suíte numa cópia do código (`backend/mutants/`), e os testes de `backend/tests/` acham a raiz do repositório com `Path(__file__).resolve().parents[2]`, que aponta para o lugar errado dentro da cópia. O `mutmut` exige a suíte verde antes de mutar e abortaria. Esses testes são de configuração e deploy e não matam mutantes dos módulos críticos; continuam rodando nos jobs `testes` e `testes-mysql`.
- **Quando roda:** nos PRs. Só o PR de release (da `develop` para a `main`) pula o job, que conta como verde para o check obrigatório: o diff dele é o da release inteira, e a rodada semanal já mede a base. Um hotfix para a `main`, vindo de outra branch, roda normalmente. Um push novo no PR cancela a rodada anterior.
- **Arquivos escolhidos:** o `backend/scripts/mutacao_incremental.py` lista os arquivos alterados no PR (`git diff --name-only origin/<base>...HEAD`) e converte cada arquivo de código dos módulos críticos no curinga do nome dos mutantes (`apps/fila/checkin_service.py` → `apps.fila.checkin_service.*`). Arquivo de código apagado no PR, documentação (`.md`) e arquivo fora da mutação não geram curinga.
  - Um **arquivo de dados** de um app crítico (fixture JSON, PDF, HTML) também conta, porque muda o comportamento dos testes sem tocar em código: os de `apps/cardapio/tests/fixtures/` (os PDFs e as páginas do RU) apontam para o leitor, e o resto, para o app inteiro.
  - Um **teste alterado, ou apagado,** também conta, porque muda o escore do código que ele cobre: `tests/test_<nome>.py` aponta para `<nome>.py` do app (ou de um subpacote dele, como o leitor). No cardápio, o que tem `leitor` no nome (`test_leitor_*.py`, `apoio_leitor.py`) aponta para o leitor inteiro, e o resto (testes de endpoint, apoio, `conftest.py`) para o cardápio sem o leitor, que tem quase metade dos mutantes da base. Nos outros apps, o resto aponta para o app inteiro.
  - Uma **mudança na configuração da mutação** (`setup.cfg`, `conftest.py`, `pytest.ini`, `manage.py`, `config/`, `requirements-dev.txt`, `requirements.txt`, `apps/__init__.py`, `apps/conftest.py`, o script ou o `backend-ci.yml`) roda a mutação num alvo fixo, o `apps/gamificacao/patente_resolver.py` (39 mutantes), para a configuração nova ser exercitada antes do merge. Esse alvo sempre gera mutantes e serve de canário: se a configuração nova o tirar da mutação, o job falha em vez de dar "nada a testar".
- **Nada a testar:** sem nenhum desses arquivos alterado, o job termina verde sem rodar o `mutmut` (não há filtro `paths:` no workflow, para o check obrigatório não ficar pendente). Se nenhum curinga casa com mutante (um arquivo em que o `mutmut` não acha o que mutar, como o `pontuacao_policy.py`), também é verde, mas só depois de conferir, na lista de todos os mutantes gerados, que os nomes ainda têm o formato `apps.*`: se o formato mudou (upgrade do `mutmut`, `source_paths`), o job falha, e também falha se o alvo fixo da configuração não gerou mutantes. Cada curinga que não casou com nenhum mutante vira um aviso na página do run.
- **Escore:** `(killed + timeout) / (killed + timeout + survived + no_tests + suspicious + segfault)`, a partir do `mutants/mutmut-cicd-stats.json`, com duas casas truncadas. O `timeout` conta como morto; `no_tests` (nenhum teste passa pela linha) conta contra; `skipped` e os mutantes que não rodaram ficam fora. O `total` do JSON não é usado, porque conta todos os mutantes gerados, inclusive os que ficaram de fora do modo incremental. No PR, o mínimo vale para o conjunto dos mutantes dos arquivos alterados.
- **Quando o job falha sem medir:** JSON ausente, ilegível ou sem algum dos campos que o `mutmut` 3.8.1 grava (`killed`, `survived`, `total`, `no_tests`, `skipped`, `suspicious`, `timeout`, `check_was_interrupted_by_user`, `segfault`); nenhum mutante avaliado (o "nada a testar" é decidido antes, então zero avaliados no passo de escore é defeito); e rodada parcial. Rodada parcial é a interrompida por tempo esgotado ou cancelamento (o `mutmut` imprime `Stopping...` e sai com 0) ou aquela em que algum mutante dos curingas ficou `not checked` depois de uma saída 0 (o JSON não tem esse campo, e o resultado seria de uma amostra). O script sai com 2 nesses casos, e com 1 só quando o escore fica abaixo do mínimo.
- **Relatório:** o resumo sai na página do run, e o log completo, o JSON e a lista dos sobreviventes e dos sem teste ficam no artefato `mutacao`.
- **Na máquina:** `cd backend`, `mutmut run "apps.gamificacao.patente_resolver.*"` (um arquivo) ou `mutmut run` (a base inteira, demorado), depois `mutmut results` e `mutmut show <mutante>`.

**Garantias do job MySQL (BD-02):**

- O job `testes-mysql` executa em todos os PRs para `develop` e `main`, sem filtro por arquivos de migration. Na `develop`, o check é obrigatório.
- Após instalar as dependências e antes de executar migrations, o job verifica se o backend carregado pelo Django é realmente `mysql`. Se carregar SQLite, a execução falha, inclusive quando `DB_ENGINE` estiver ausente ou incorreto.
- O job confere migrations pendentes com `makemigrations --check --dry-run`, aplica as migrations do zero e executa a suíte completa com a meta de cobertura.
- O teste de configuração usa a fixture `carregar_settings`, isolada do `.env` local, para conferir os valores explícitos de charset, isolamento e collation do banco de testes.
- O teste com conexão real verifica MySQL 8.4, os charsets do banco e da conexão, a collation do banco e o isolamento da sessão.
- Os motivos de testes ignorados aparecem no relatório com `pytest -rs`.
- A auditoria de `requirements-ci-mysql.txt`, incluindo o driver MySQL, acontece antes das migrations e dos testes.
- A evidência de aceite inclui um PR de prova com migration executando os jobs SQLite e MySQL. Esse PR de prova é fechado sem merge.

**Models e migrations sincronizados (#110):** o banco de teste é criado pelas migrations, não pelos models, então uma constraint alterada só no `models.py` passaria pela suíte sem chegar ao banco. O teste `tests/test_estrutura.py::test_models_e_migrations_estao_sincronizados` roda `makemigrations --check --dry-run` dentro da suíte e falha listando a migration que falta. Por estar no `pytest`, vale nos jobs `testes` (SQLite) e `testes-mysql` e também no teste local, antes do push. No `testes-mysql` a conferência fica duplicada de propósito: o passo "Conferir migrations pendentes" do workflow falha mais cedo, antes do `migrate`, e não deve ser removido por parecer redundante.

**Índices da previsão e do ranking (BD-10, RNF01):** `tests/test_indices_bd10.py` monta dados de teste em volume (3.600 check-ins e 1.200 linhas de pontos), atualiza as estatísticas (`ANALYZE`) e roda `EXPLAIN` nas consultas da previsão de pico, da espera estimada e do ranking. Falha se o otimizador não usar `checkin_campus_tipo_data_idx` e `pontos_semestre_ranking_idx`, ou se o ranking ordenar em arquivo temporário. Roda nos dois bancos; o passo "EXPLAIN dos índices (BD-10)" do `testes-mysql` repete esses testes com `-s` (mesmo quando o passo anterior falha) só para o plano do MySQL ficar no log. No MySQL, o ranking só usa o índice com a elegibilidade num `EXISTS` dentro de um `CASE`, sem join nem `select_related`. Quem implementar a BE-15 e a BE-17 deve manter a forma das consultas descrita em `docs/arquitetura/banco-de-dados/indices-bd10.md`.

**Decisão sobre collation (BD-02):** o banco de testes MySQL mantém `utf8mb4_0900_ai_ci`, que ignora diferenças de acentos e maiúsculas/minúsculas nas comparações. Assim, `"Açúcar"` e `"acucar"` são considerados iguais: inserir ambos em `Marcador.nome`, que possui restrição de unicidade, provoca `IntegrityError` no MySQL. No SQLite, com a comparação padrão desse campo, os dois valores podem coexistir. Essa diferença entre os bancos é conhecida e fica documentada; a collation do MySQL é mantida.

### 5.2 `frontend-ci.yml` (FE-02, FE-17, FE-19)

| Job | Comandos | Bloqueia o merge |
|---|---|---|
| `lint` | ESLint e Oxlint **sem `--fix`** (novo script `lint:ci`; o `lint` atual corrige sozinho e esconderia o erro no CI) | Sim |
| `testes` | `vitest run --coverage`, com `coverage.thresholds` de 70% de linhas em **cada** arquivo crítico (a mesma lista da mutação); depois `node scripts/cobertura.mjs resumo`, com a tabela por módulo no resumo do run (FE-19) | Sim |
| `build` | `vite build` | Sim |
| `seguranca` | Semgrep e `npm audit --audit-level=high` | Sim |
| `mutacao` | StrykerJS incremental nos arquivos críticos alterados; falha abaixo de 50% | Sim, quando roda |

**Como o job `mutacao (front)` funciona (FE-17):**

- **Configuração:** `frontend/stryker.config.mjs` (StrykerJS 10 com `@stryker-mutator/vitest-runner`, cobertura por teste). Os arquivos mutados são os módulos críticos da seção 2, listados no `MODULOS` do `frontend/scripts/mutacao.mjs`: `auth` (`stores/auth.js`, guardas do `router`), `cardapio` (`stores/cardapio.js`, `utils/cardapio.js`), `avaliacao` (`stores/avaliacoes.js`), `fila` (`stores/fila.js`, `services/leituraPosicao.js`, `CheckinBotao`, `FilaPrevisao`), `gamificacao` (`stores/gamificacao.js`, `PontosAviso`) e `api` (`services/apiClient.js`). Há teste que confere os dois sentidos: todo arquivo com meta de cobertura no `vitest.config.js` também é mutado, e todo arquivo mutado também tem meta de 70% de linhas (FE-19). O `vitest.config.js` monta as metas a partir da mesma lista (`ARQUIVOS_CRITICOS`), então as duas portas não divergem. As validações do cadastro ficam na `CadastroView` e são cobertas pelos testes do fluxo da conta, não pela mutação da view inteira.
- **Arquivos escolhidos:** `node scripts/mutacao.mjs alvos origin/<base>` lista os arquivos do `git diff --name-only origin/<base>...HEAD` e devolve os críticos alterados, que vão para o `--mutate` do Stryker. Um **teste alterado** conta para o arquivo crítico de mesmo nome, cortando o nome no primeiro ponto (`x.test.js` e `x.propriedades.test.js` apontam para `x.js` ou `x.vue`). **Sem correspondência por nome**, o teste conta para os arquivos críticos que ele importa, direta ou indiretamente, seguindo também o `import()` dinâmico das rotas: um teste de tela, que monta o `App` com o roteador, chega à base inteira (como o app inteiro no backend). Uma **mudança na configuração da mutação** (`stryker.config.mjs`, `vitest.config.js`, `vite.config.js`, `package.json`, `package-lock.json`, o script, o `frontend-ci.yml` ou o servidor simulado em `src/services/mock/`, que os testes de todas as stores críticas usam, como os fixtures no backend; um `setupFiles` do Vitest, se for criado, entra nessa lista) sem nenhum arquivo crítico alterado muta um alvo fixo, o `utils/cardapio.js`; com outro alvo no PR, o alvo fixo não entra, para não diluir o escore do que mudou. Arquivo crítico apagado no PR não vira alvo.
- **Nada a testar:** sem nenhum desses arquivos alterado, o job roda e termina verde sem chamar o Stryker (sem filtro `paths:`, para o check obrigatório não ficar pendente). O PR de release (`develop` → `main`) pula o job, como no backend.
- **Escore:** `(Killed + Timeout) / (Killed + Timeout + Survived + NoCoverage)`, como o Stryker calcula. `CompileError`, `RuntimeError`, `Ignored` e `Pending` ficam fora da conta. No PR, a meta vale para o conjunto dos mutantes rodados: o `thresholds.break: 50` do `stryker.config.mjs` compara o valor exato, e o `scripts/mutacao.mjs escore` repete a conta no resumo do run, mostrando duas casas truncadas (o veredito é o mesmo).
- **Quando o job falha sem medir:** o step de escore roda sempre que o Stryker rodou, mesmo sem relatório. Relatório ausente ou ilegível, nenhum mutante avaliado, `--minimo` inválido ou (na rodada semanal) módulo crítico fora do relatório saem com 2 e reprovam o job, em vez de ficar verde sem ter medido.
- **Componentes `.vue`:** o Stryker envolve os valores em chamadas `stryMutAct_*`/`stryCov_*`, declaradas no próprio script, e o `defineProps`, içado para fora do `setup()`, não pode referenciar variáveis locais. Por isso o argumento do `defineProps` fica entre `// Stryker disable all` e `// Stryker restore all`.
- **Relatório:** o resumo sai na página do run, e o HTML e o JSON do Stryker ficam no artefato `mutacao-front`.
- **Na máquina:** `cd frontend`, `npm run mutacao -- --mutate src/stores/fila.js` (um arquivo) ou `npm run mutacao` (a base inteira, dezenas de minutos), e o relatório em `reports/mutation/mutation.html`.

**Como o passo de cobertura funciona (FE-19):**

- **Meta:** 70% de linhas em cada arquivo crítico da seção 2, não na média do front: um arquivo fraco não se esconde atrás dos outros. Antes da FE-19, o `CheckinBotao` e o `FilaPrevisao` eram mutados mas não tinham meta de cobertura; agora têm, porque a lista de metas vem do `ARQUIVOS_CRITICOS` do `scripts/mutacao.mjs`.
- **Relatório:** `scripts/cobertura.mjs resumo coverage/coverage-summary.json --minimo 70` lê o `coverage-summary.json` e escreve, no resumo do run, a tabela de cada arquivo crítico (módulo, linhas cobertas e porcentagem com duas casas truncadas) e a linha do conjunto. O HTML completo fica no artefato `cobertura-front`. O Vitest já reprova abaixo da meta, e o script repete a conta sobre o mesmo relatório para o veredito e a tabela saírem do mesmo número.
- **Quando o passo falha sem medir:** relatório ausente ou ilegível, arquivo crítico fora do relatório ou sem nenhuma linha (0 de 0 não prova nada) e `--minimo` inválido saem com 2, e o passo reprova em vez de ficar verde sem ter medido. Abaixo da meta, sai com 1 e nomeia o arquivo.
- **SAST:** sem mudança de ferramenta. O job `seguranca (front)` (`npm audit --audit-level=high` e Semgrep com severidade ERROR) é o relatório da meta de 0 achados críticos ou altos; o resultado de cada rodada fica no log do job.
- **Na máquina:** `cd frontend`, `npm run test:ci` e depois `node scripts/cobertura.mjs resumo coverage/coverage-summary.json`.

### 5.3 `e2e.yml` (FE-18)

| Job | Comandos | Bloqueia o merge |
|---|---|---|
| `ponta-a-ponta` | Sobe PWA, API e banco com o `frontend/e2e/docker-compose.yml`, carrega as fixtures (BD-03 e as do e2e) e roda o Playwright no celular e no desktop | Sim, a partir do M2 |

**Como o job `ponta-a-ponta` funciona (FE-18):** `.github/workflows/e2e.yml`, em todo PR (sem filtro `paths:`) e no push na `develop` e na `main`. Builda as imagens de produção do backend e do PWA, espera os healthchecks do MySQL, do Gunicorn e do Caddy (`docker compose up --wait`) e roda `npx playwright test`. Em falha, o log da pilha sai no próprio job e o relatório do Playwright, com o trace do teste que falhou, fica no artefato `e2e-relatorio`. Não há segunda tentativa: o banco só é limpo uma vez por rodada, e uma tentativa nova do M2, do M3 ou do M4 falharia pelo que a primeira gravou (check-in feito, avaliação enviada, adesão ligada), escondendo a causa real.

### 5.4 Rodadas agendadas

- **Toda semana** (e antes de 22/11): mutação na base inteira, back e front, para pegar o escore de quem não mexeu em módulo crítico recentemente.
  - **Back:** `.github/workflows/backend-mutacao-semanal.yml`, aos domingos às 06:00 UTC (03:00 em Brasília), na `develop`; à mão, pelo `workflow_dispatch`, na branch escolhida. Um job por módulo crítico (`cadastro`, `cardapio/leitor`, `cardapio` sem o leitor, `avaliacao`, `fila`, `gamificacao`), com até 5 horas cada, para a base inteira (cerca de 5.240 mutantes, quase metade no leitor) não passar do limite de 6 horas de um job do GitHub. Um último job junta os seis resultados e falha se **algum** módulo ficar abaixo de 50%, se faltar o resultado de algum ou se algum job de módulo não terminou bem (quebrou, passou do tempo ou foi cancelado), porque um resultado parcial não vale. Mesma fórmula do escore do job `mutacao`.
  - **Front:** `.github/workflows/frontend-mutacao-semanal.yml`, aos domingos às 07:00 UTC (04:00 em Brasília), na `develop`; à mão, pelo `workflow_dispatch`, na branch escolhida. Um job só com todos os arquivos críticos (perto de 2 mil mutantes, dezenas de minutos), e o `scripts/mutacao.mjs escore --por-modulo` reprova a rodada se **algum** módulo crítico ficar abaixo de 50%, mesmo com o geral acima, ou se algum módulo faltar no relatório.
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
