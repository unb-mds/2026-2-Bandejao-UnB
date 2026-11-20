# ADR 0016 — Login com e-mail institucional e senha

**Status:** Proposta (2026-11-19; passa a Aceita na revisão do PR da DOC-12, #202)
**Data:** 2026-11-19
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

No MVP, o Usuário entrava com a matrícula ou o SIAPE e a senha, no mesmo
campo (RF03.1). O sistema separava os dois pelo tamanho: 9 dígitos para
matrícula e 7 para SIAPE (RN01). Assim ficaram o protótipo da Release 1 e a
BE-07 (#97).

Esse identificador tem dois problemas:

- **Ele não é confirmado.** O sistema confere só o formato da matrícula/SIAPE
  (L01). O dado que a conta prova ter é o e-mail institucional, porque a conta
  só funciona depois que a pessoa abre o link enviado para aquela caixa (RF02,
  ADR 0002).
- **O login dependia do tamanho da matrícula.** A ADR 0002 registra que o
  tamanho de 9 dígitos é uma suposição para os níveis de ensino fora da
  graduação (L16). Se um desses níveis tiver outro tamanho, a separação entre
  matrícula e SIAPE no login quebra junto com o cadastro.

Além disso, a recuperação de senha já pede o e-mail na tela
(`RecuperarSenhaView`), e o reenvio da confirmação pela tela de login pedia a
matrícula/SIAPE. A pessoa precisava saber dois dados diferentes para entrar e
para recuperar a conta.

O e-mail institucional já é único (`USUARIO.email_institucional`, `UNIQUE`,
indexada) e é guardado normalizado, sem espaços nas pontas e em minúsculas
(`normalizar_email`).

## Decisão

O login da Release 2 usa o **e-mail institucional e a senha**.

- **Domínios aceitos** (ADR 0002, sem mudança): `@aluno.unb.br` para
  Estudante (ex.: `251098732@aluno.unb.br`) e `@unb.br` para
  Professor/Servidor, em geral `nome.sobrenome@unb.br`. O `LoginService` usa
  o `EmailInstitucionalValidator` como está: o e-mail é aceito se um dos dois
  domínios bater. O login confere **só o domínio**: o formato da matrícula
  (RN01) é conferido no cadastro, e `abc@aluno.unb.br` não acha conta e
  recebe o 401 genérico, não o 422. Não há regra de formato nova.
- **Normalização:** o e-mail digitado passa pelo `normalizar_email` antes da
  busca. Maiúsculas e espaços nas pontas entram na mesma conta.
- **Domínio inválido:** e-mail fora dos domínios institucionais dá `422`,
  antes de consultar o banco, e não conta como tentativa (RF03.2).
- **Busca da conta:** `ContaRepository.buscarPorEmail(email, travar)`, com o
  mesmo `select_for_update` que o login já usava.
- **Reenvio da confirmação pela tela de login** recebe o mesmo e-mail do login
  (`contaParaReenvio(email, token)`; no corpo HTTP, o campo é
  `emailInstitucional`). Ao contrário do login, o reenvio não confere o
  domínio: um e-mail fora do padrão só não acha conta, e a resposta é a mesma
  (RF02.2). Se vierem o e-mail e o token, vale o e-mail; se ele não achar
  conta, o token é tentado. O reenvio só pelo token do link expirado não muda.
- **Recuperação de senha (RF04.1)** pede o e-mail institucional, e o limite de
  3 solicitações por hora (Anexo A) passa a contar por e-mail.
- **Continua valendo:** mensagem genérica que não revela se a conta existe
  (RF03.1), o mesmo custo de hash para conta inexistente, o bloqueio por conta
  (`TentativaLoginTracker`, RF03.2), o limite por IP (#123), o CSRF no login
  (#112) e nada de e-mail na resposta nem no log (RI10, ADR 0008).
- **A matrícula/SIAPE continua no cadastro**, para garantir uma conta por
  matrícula/SIAPE (RF01.5) e para a moderação (RNF08, ADR 0004). Ela só deixa
  de servir para entrar.

## Consequências

- O login usa o dado que a conta confirmou (RF02), e não um dado de que o
  sistema só confere o formato (L01).
- O login não depende mais do tamanho da matrícula. A regra "9 dígitos são
  matrícula e 7 são SIAPE" sai da RN01, e a L16 passa a afetar só o cadastro.
- A pessoa usa o mesmo dado para entrar, reenviar a confirmação e recuperar a
  senha.
- Não precisa de migration: `email_institucional` já é `UNIQUE` e indexada. O
  `USERNAME_FIELD` do Django continua `matricula_siape`, porque o login não
  passa pelo `authenticate()`.
- O contrato muda: o corpo do `POST /api/sessao/` troca `matriculaSiape` por
  `emailInstitucional`, e o corpo do reenvio também. Um corpo com
  `matriculaSiape` dá `422`. O front (`LoginView`, `authStore`) muda junto
  (FE-03, #101).
- O motivo da ADR 0008 de buscar a conta pela matrícula/SIAPE no login, na
  recuperação e no reenvio deixa de valer. A matrícula/SIAPE continua em texto
  claro pelos outros motivos daquela ADR: unicidade e leitura pela equipe na
  moderação e na matrícula contestada.
- Quem tinha conta e entrava pela matrícula/SIAPE passa a entrar pelo e-mail
  institucional, o mesmo que recebeu o link de confirmação.

## Alternativas consideradas

- **Manter a matrícula/SIAPE:** já estava implementado (BE-07, #97), mas
  mantém o login preso a um dado não confirmado e ao tamanho da matrícula.
  Descartada.
- **Aceitar e-mail ou matrícula/SIAPE no mesmo campo:** mais flexível, mas
  dobra os caminhos do login, do bloqueio e do reenvio, e mantém a separação
  pelo tamanho. Descartada pela complexidade, com prazo até 22/11.

## Relacionadas

- Requisitos: RF02.2, RF03.1, RF03.2, RF04.1, RN01, L01, L16, Anexo A.
- `docs/arquitetura/adr/0002-matricula-apelido-extraidos-do-email.md` (formato do e-mail).
- `docs/arquitetura/adr/0007-sessao-autenticada-por-cookie-httponly.md` (rotas de sessão).
- `docs/arquitetura/adr/0008-matricula-siape-em-texto-claro.md` (motivo da busca pela matrícula).
- `c4-nivel-4-cadastro-autenticacao.md` (fluxo 4c, `LoginService`, `ContaRepository`).
- Implementação: BE-20 (#201, backend) e FE-03 (#101, frontend).
