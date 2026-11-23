# ADR 0004 — Acesso direto da equipe ao banco de dados para moderação


**Status:** Aceita
**Data:** 2026-09-27 (revisada em 2026-11-14: a exclusão de conta passa a apagar a conta, para atender à LGPD; e em 2026-11-15: retenção dos backups e ponderação do legítimo interesse)
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
- atender solicitações de exclusão de conta, que apagam a conta (ver a
  revisão de 2026-11-14, abaixo).

A equipe já sinalizou a intenção de **automatizar a moderação de rotina no
futuro**, reservando o acesso direto a casos extremos de rastreamento por
matrícula/SIAPE. Esta ADR reflete o estado atual, em que o acesso direto é o
caminho principal.

## Consequências

- Nenhuma tela ou endpoint administrativo precisa ser construído no produto (Release 2), o que
  libera tempo para as funcionalidades principais.
- O acesso ao banco dá visibilidade a dados pessoais, incluindo a matrícula ou
  o SIAPE de todos os usuários. Ele deve ficar restrito a membros nomeados da
  equipe (RNF07), e as credenciais de acesso não podem ser compartilhadas
  informalmente. A conexão é feita por túnel SSH até a máquina virtual da
  Azure (ADR 0012), com chave SSH individual por membro; a porta do banco não é
  exposta à internet.
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
  pelo endpoint público, e uma conta suspensa não pode autenticar. Os campos
  que representam esses estados estão no Nível 4 do banco de dados:
  `AVALIACAO.oculta` (avaliação oculta não aparece nos comentários nem entra
  na nota média e na quantidade; ver o Nível 4 da Avaliação) e
  `USUARIO.status` (`suspenso` não autentica; ver a ADR 0007).
- SQLite em desenvolvimento e MySQL em produção (ADR 0001) significam que os
  procedimentos manuais precisam ser testados no banco de produção, não só no
  local.
- Quando a moderação de rotina for automatizada, esta ADR deve ser revisada e
  substituída, mantendo o acesso direto apenas como recurso de exceção.

## Revisão de 2026-11-14: a exclusão de conta apaga a conta

**Contexto.** Até aqui, a exclusão de conta só marcava a conta como
`removido` e guardava a matrícula/SIAPE, o e-mail, o apelido e o hash da
senha sem prazo, para manter o vínculo das avaliações com o autor (RNF08).
Pela LGPD, o titular pode pedir a eliminação dos dados tratados com o seu
consentimento (art. 18, VI), e o cadastro usa o consentimento como base
legal (aceite do aviso de privacidade). Guardar os dados depois do pedido
só é permitido nos casos do art. 16 (obrigação legal, pesquisa,
transferência a terceiro ou uso exclusivo do controlador com os dados
anonimizados), e nenhum deles cobre a moderação, que precisa identificar o
autor. Manter os dados sem prazo também contraria o princípio da
necessidade (art. 6º, III).

Foram consideradas duas saídas:
- **(A)** guardar só a matrícula/SIAPE ligada às avaliações por um prazo
  definido, com base no legítimo interesse (art. 7º, IX), e apagar tudo
  depois do prazo;
- **(B)** apagar a conta na exclusão e manter as avaliações anônimas.

**Decisão: (B).** O `RemoverContaCommand` apaga os contadores, retira o
vínculo dos registros de fila, encerra as sessões e **apaga a linha de
`USUARIO`**. As avaliações continuam publicadas como "usuário removido",
sem vínculo com a pessoa (`AVALIACAO.usuario_id` vira nulo por
`ON DELETE SET NULL`). Se a pessoa pedir, a equipe também apaga as
avaliações dela antes de apagar a conta, porque um comentário pode conter
algo que a identifique. O status `removido` e a coluna `removido_em` deixam
de existir (migration da BD-12).

**Consequências.**
- Nenhum dado pessoal sobra depois da exclusão: a avaliação anônima deixa
  de ser dado pessoal (art. 12), e mantê-la não precisa de base legal.
- A moderação continua possível: a equipe ainda oculta uma avaliação
  abusiva de conta excluída. O que se perde é identificar o autor. Como a
  conta dele já não existe, não haveria a quem suspender.
- A pessoa pode voltar a se cadastrar com a mesma matrícula/SIAPE e o mesmo
  e-mail. Uma matrícula contestada (L01) também se resolve apagando a conta
  de quem a usou indevidamente.
- O banco já estava preparado: as avaliações e os registros de fila ficam
  sem dono (`ON DELETE SET NULL`) e os contadores são apagados junto
  (`ON DELETE CASCADE`). Como esse comportamento é do ORM do Django, a
  exclusão é feita pelo `RemoverContaCommand`, nunca por DELETE direto no
  banco.
- A opção (A) foi descartada por exigir um prazo novo no Anexo A, um job de
  limpeza e a demonstração formal do legítimo interesse, sem ganho real para
  a moderação.
- Os dados da conta excluída também saem das cópias de segurança, que são
  guardadas por 7 dias (Anexo A, ADR 0012).

**Ponderação do legítimo interesse (LGPD, art. 10).** O aviso de privacidade
usa o legítimo interesse (art. 7º, IX) para três tratamentos que não dependem
do consentimento. Para cada um, a ponderação entre o interesse da equipe e os
direitos do titular é a seguinte:

| Tratamento | Interesse da equipe | Dado tratado (só o necessário, art. 10, §1º) | Por que não prevalecem os direitos do titular |
|---|---|---|---|
| Dados de segurança da conta (tentativas de login erradas e bloqueio) | Impedir que alguém descubra a senha de outra pessoa por tentativa e erro (RF03.2) | Um contador, o horário da primeira falha da janela e o horário de fim do bloqueio, ligados à conta | Protege o próprio titular; o dado é zerado a cada login certo ou nova janela de 10 minutos e some com a conta |
| Cookies necessários (sessão e CSRF) | Manter a pessoa logada e impedir pedidos falsificados por outros sites (ADR 0007, #112) | Identificador de sessão e token aleatório, sem dado pessoal no cookie | Sem eles o aplicativo não funciona; não há publicidade nem rastreamento entre sites; a sessão dura 14 dias e termina no "Sair" |
| Registros técnicos do servidor | Diagnosticar falhas e se defender de ataques | Data, hora, página e, se o servidor registrar, endereço IP; nunca o corpo de cadastro e login nem o token da confirmação de e-mail | Acesso só da equipe nomeada (ADR 0008); o titular é informado no aviso; o prazo de guarda desses registros deve ser definido junto com a configuração do servidor |

O titular pode se opor a esses tratamentos pelo e-mail da equipe (art. 18,
§2º). Como eles são necessários para o aplicativo funcionar com segurança, a
oposição é atendida com a exclusão da conta.

## Alternativa considerada

**Tela administrativa ou API de administração.** Daria mais segurança
operacional (controle de acesso por perfil, registro de ações, validações),
mas foi deixada fora do escopo (RNF08) pelo custo de desenvolvimento em um
projeto de um semestre. Continua sendo o caminho natural para a automação
futura da moderação de rotina.

## Relacionadas

- Requisitos: RNF07 (RNF07.4), RNF08, L01, L02.
- Lei Geral de Proteção de Dados (Lei nº 13.709/2018): art. 6º, III; art. 7º, IX; art. 12; art. 16; art. 18, VI.
- `docs/arquitetura/adr/0001-escolha-stack-backend.md` (bancos de dados usados em
  desenvolvimento e produção).
- `docs/arquitetura/adr/0002-matricula-apelido-extraidos-do-email.md` (origem da matrícula
  e do apelido rastreados).
