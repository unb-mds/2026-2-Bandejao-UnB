# ADR 0004 — Acesso direto da equipe ao banco de dados para moderação


**Status:** Aceita
**Data:** 2026-09-27
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

O Bandejão não valida a matrícula ou o SIAPE contra nenhum sistema da
universidade: só confere o formato (RF01, L01). Por isso, a principal defesa
contra uso indevido (matrícula alheia ou inventada, contas múltiplas, avaliações
abusivas) é a **rastreabilidade posterior** (RNF08): a equipe precisa
identificar o autor de uma avaliação problemática, moderar o conteúdo e tratar
matrículas contestadas.

Os requisitos já estabelecem que:

- a moderação (ocultar avaliações, suspender contas, tratar matrículas
  contestadas) é feita **diretamente pela equipe**, por consulta
  administrativa manual, e **não há tela administrativa no escopo** (RNF08);
- a matrícula/SIAPE é guardada de forma **recuperável** a partir do apelido,
  com acesso restrito à equipe (RNF07);
- a exclusão de conta é feita por **solicitação à equipe** (RNF07);
- o site divulga um canal de contato para reclamações (RNF08).

O escopo do projeto é um MVP a ser entregue em um semestre por uma equipe
inexperiente. Construir uma interface ou uma API de administração, com controle
de acesso e de auditoria, competiria com as funcionalidades principais.

## Decisão

A Equipe de Desenvolvimento opera e modera o sistema por **acesso direto ao
banco de dados**, por fora da API REST. É um caminho paralelo ao fluxo normal
(PWA → Backend → Banco), representado nos diagramas C4 por uma seta tracejada
da Equipe ao Banco de Dados.

Esse acesso é usado para:

- rastrear o autor de uma avaliação a partir do apelido, recuperando a
  matrícula/SIAPE (RNF07, RNF08);
- ocultar avaliações e suspender contas;
- tratar matrículas contestadas (L01);
- atender solicitações de exclusão de conta.

A equipe já sinalizou a intenção de **automatizar a moderação de rotina no
futuro**, reservando o acesso direto a casos extremos de rastreamento por
matrícula/SIAPE. Esta ADR reflete o estado atual, em que o acesso direto é o
caminho principal.

## Consequências

- Nenhuma tela ou endpoint administrativo precisa ser construído no MVP, o que
  libera tempo para as funcionalidades principais.
- O acesso ao banco dá visibilidade a dados pessoais, incluindo a matrícula ou
  o SIAPE de todos os usuários. Ele deve ficar restrito a membros nomeados da
  equipe (RNF07), e as credenciais de acesso não podem ser compartilhadas
  informalmente. A forma de conexão dependerá da hospedagem, ainda não
  definida (4.4 do Documento de Visão).
- Operações manuais **contornam as validações da API** (formato, unicidade,
  regras de negócio) e podem deixar dados inconsistentes. A equipe deve
  combinar quais operações são permitidas e como executá-las.
- Como não há tela administrativa, também não há registro automático de quem
  fez cada alteração de moderação, e a equipe decidiu não manter um registro
  manual dessas ações. Consequência aceita: não será possível reconstruir
  depois quem suspendeu uma conta ou ocultou uma avaliação, nem por quê; se
  uma ação de moderação for contestada, não haverá histórico para consultar.
  Se isso virar um problema na prática, esta decisão deve ser revista, e a
  automação da moderação é a oportunidade natural de introduzir um registro.
- Para que a moderação por banco tenha efeito, a API precisa **respeitar o
  estado alterado**: por exemplo, uma avaliação oculta não pode ser devolvida
  pelo endpoint público, e uma conta suspensa não pode autenticar. Os models
  precisam de campos que representem esses estados, e a equipe deve defini-los
  ao implementar os apps de avaliação e de cadastro.
- SQLite em desenvolvimento e MySQL em produção (ADR 0001) significam que os
  procedimentos manuais precisam ser testados no banco de produção, não só no
  local.
- Quando a moderação de rotina for automatizada, esta ADR deve ser revisada e
  substituída, mantendo o acesso direto apenas como recurso de exceção.

## Alternativa considerada

**Tela administrativa ou API de administração.** Daria mais segurança
operacional (controle de acesso por perfil, registro de ações, validações),
mas foi deixada fora do escopo (RNF08) pelo custo de desenvolvimento em um
projeto de um semestre. Continua sendo o caminho natural para a automação
futura da moderação de rotina.

## Relacionadas

- Requisitos: RNF07, RNF08, L01, L02.
- `docs/adr/0001-escolha-stack-backend.md` (bancos de dados usados em
  desenvolvimento e produção).
- `docs/adr/0002-matricula-apelido-extraidos-do-email.md` (origem da matrícula
  e do apelido rastreados).
