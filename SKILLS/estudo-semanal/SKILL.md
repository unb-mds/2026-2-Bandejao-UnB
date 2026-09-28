---
name: estudo-semanal
description: >
  Cria o relatório markdown padronizado de estudo semanal do grupo do RU-UnB
  (fila, cardápio, previsão de pico), para ser commitado no GitHub em
  estudos/semana-XX/. Use sempre que o usuário disser que estudou um assunto
  durante a semana (por exemplo "estudei Docker no fim de semana", "terminei
  de estudar sobre filas", "preciso fazer o commit do meu estudo da semana") e
  quiser gerar o documento antes de commitar, ou quando pedir explicitamente
  para "padronizar o commit do estudo", "gerar relatório de estudo semanal" ou
  "criar o arquivo md do assunto que estudei". Também use para revisar ou
  corrigir a formatação de um relatório de estudo já escrito antes do commit.
---

# Estudo Semanal — RU UnB

Gera o relatório padronizado (arquivo `.md`) que cada integrante do grupo produz
depois de estudar, individualmente, um assunto relevante para o projeto do site
de fila / cardápio / previsão de pico dos RUs da UnB. O objetivo do documento é
que qualquer colega do grupo consiga entender o essencial do assunto e como ele
se aplica ao projeto sem precisar estudar tudo de novo — só lendo esse arquivo.

## Convenção do repositório

- **Pasta:** cada semana tem sua própria pasta: `estudos/semana-XX/` (XX com dois
  dígitos, ex: `semana-01`, `semana-03`).
- **Nome do arquivo:** `semanaXX-assunto.md`, com o assunto em minúsculas e
  separado por hífen. Ex: `semana03-docker.md`, `semana07-previsao-de-demanda.md`.
- **Caminho completo de exemplo:** `estudos/semana-03/semana03-docker.md`.

## Fluxo de trabalho: entrevista guiada

Não peça tudo de uma vez. O documento é construído em rodadas de conversa: você
pergunta uma coisa, o integrante responde com o que lembra do que estudou, você
já aproveita a resposta para ir preenchendo o rascunho, e passa pra próxima
pergunta. É um bate-papo que vai destilando o estudo da pessoa em documento —
não um formulário.

**Abertura.** Se o usuário só disse algo solto tipo "estudei Docker essa
semana", comece confirmando o básico em uma pergunta curta (pode ser mais de um
dado nessa primeira, já que são triviais): nome do integrante, número da semana
e assunto. Não precisa de ferramenta de múltipla escolha aqui — é só perguntar
em linguagem natural.

**Rodadas pelo conteúdo.** Depois disso, percorra as seções do
`assets/template.md` **uma de cada vez**, nesta ordem:

1. Resumo (do que se trata o assunto)
2. Aplicação no projeto (onde isso entra no site do RU)
3. Principais conceitos / como usar
4. Fontes e materiais usados
5. Observações / próximos passos (só pergunte se fizer sentido; é opcional)

Para cada seção:
- Faça **uma pergunta objetiva e específica** sobre aquele pedaço do estudo —
  evite perguntas genéricas tipo "me conta sobre X"; ajude a pessoa a lembrar
  do que estudou. Ex: em vez de "qual a aplicação no projeto?", pergunte "esse
  assunto entra em qual parte do site — fila, cardápio, previsão de pico,
  infraestrutura? o que ele resolve especificamente?".
- Depois da resposta, **reescreva o que a pessoa disse** de forma clara e
  organizada (não é copiar e colar a resposta crua) e mostre esse trechinho já
  pronto antes de seguir pra próxima pergunta — assim o integrante vê o
  documento tomando forma e pode corrigir na hora se algo ficou errado.
- Se a resposta já veio completa e detalhada, não insista com pergunta
  repetida — só confirme e siga para a próxima seção.
- Se a resposta vier rasa (ex: "é uma ferramenta de container"), faça **uma**
  pergunta de acompanhamento pontual antes de seguir, para garantir que a seção
  tenha profundidade suficiente para ajudar um colega que não estudou o tema.

**Fechamento.** Depois da última seção respondida, monte o documento completo,
mostre pra pessoa revisar, e só gere o arquivo final depois da confirmação (ou
direto, se o usuário pedir explicitamente pra já finalizar sem revisão).

## Depois da entrevista

1. **Montar o documento final** usando `assets/template.md` como base,
   preenchido com o que foi destilado em cada rodada da entrevista (não com as
   respostas cruas — com a versão já reescrita e organizada que foi mostrada a
   cada etapa). Substitua todos os placeholders `{{...}}`; não deixe nenhum
   `{{...}}` no arquivo final. Remova a seção "Observações / próximos passos"
   inteira se não houve nada pra colocar ali (não deixe seção vazia com só o
   comentário). Remova também os comentários `<!-- ... -->` do template — eles
   são só instrução de preenchimento, não aparecem no documento entregue.

2. **Criar o arquivo** em `estudos/semana-XX/semanaXX-assunto.md` dentro do
   repositório do projeto (se o usuário tiver um clone local do repo em algum
   caminho, criar lá; caso contrário, criar em `/home/claude` e depois copiar
   para `/mnt/user-data/outputs` para o usuário baixar e colocar na pasta certa).

3. **Sugerir a mensagem de commit padronizada**, no formato:
   ```
   estudo(semanaXX): assunto - nome-do-integrante
   ```
   Exemplo: `estudo(semana03): docker - joao`

   Se o usuário pedir, também pode fornecer os comandos git prontos:
   ```bash
   git add estudos/semana-03/semana03-docker.md
   git commit -m "estudo(semana03): docker - joao"
   git push
   ```
   (Não execute comandos git automaticamente — o grupo decidiu que cada um faz
   o commit manualmente.)

4. **Entregar o arquivo ao usuário** (present_files) e mostrar a mensagem de
   commit sugerida logo em seguida, de forma breve.

## Dicas de qualidade

- Relatórios muito curtos (2-3 linhas por seção) não cumprem o objetivo do
  grupo — a ideia é que o documento *substitua* precisar estudar o assunto do
  zero. Incentive o usuário a dar detalhe suficiente nos "Principais conceitos".
- Se o usuário colar um texto grande (anotações, resumo de curso) de uma vez
  em vez de topar a entrevista, tudo bem — não force as perguntas por
  perguntar. Extraia o que já dá pra extrair desse texto, mapeie para as
  seções do template, e faça perguntas só sobre o que realmente ficou faltando
  (normalmente aplicação no projeto e fontes, que anotações de estudo tendem a
  não deixar claras).
- Nunca invente conteúdo técnico sobre o que a pessoa estudou. Se uma resposta
  não veio ou ficou vaga, pergunte de novo — não preencha a lacuna com
  suposições só pra fechar o documento mais rápido.
