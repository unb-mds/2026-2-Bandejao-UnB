# ADR 0002 — Matrícula e apelido extraídos do e-mail institucional

**Status:** Aceita
**Data:** 2026-09-24
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

O Bandejão não tem acesso a um banco de dados da universidade para conferir se uma matrícula ou SIAPE realmente existe: o sistema só pode validar o **formato** do identificador (RF01, L01). Ao mesmo tempo, o cadastro exige um e-mail institucional, que já é o único canal de confirmação de conta e de recuperação de senha (RF02, RF04).

Os e-mails institucionais da UnB seguem um padrão previsível:
- Estudantes: `matricula@aluno.unb.br` (ex.: `251098732@aluno.unb.br`).
- Professores e servidores: geralmente `nome.sobrenome@unb.br`.

Pedir matrícula e apelido como campos digitados separadamente do e-mail institucional cria redundância (a mesma informação, ou uma derivável dela, sendo informada duas vezes) e uma fonte extra de erro de digitação, sem ganho real de confiabilidade — já que nenhuma dessas informações é validada contra um sistema externo de qualquer forma.

## Decisão

- Para **Estudante**, a matrícula não é digitada no cadastro: é **extraída automaticamente** da parte antes do "@" do e-mail institucional, que deve seguir exatamente o formato `matricula@aluno.unb.br`. O apelido, por outro lado, continua sendo escolhido manualmente pelo estudante, pois não há uma fonte confiável equivalente para derivá-lo.
- Para **Professor/Servidor**, a matrícula funcional/SIAPE continua sendo digitada diretamente (o padrão do e-mail institucional não carrega esse identificador). O apelido, porém, **não é digitado**: é extraído automaticamente da parte antes do "@" do e-mail institucional `@unb.br`, aceitando qualquer texto (não é exigido o formato exato nome.sobrenome). Em caso de colisão com um apelido já existente — considerado improvável, já que servidores e professores não costumam ter conflito de nome no e-mail institucional —, o cadastro automático é rejeitado e a pessoa é solicitada a digitar um apelido alternativo manualmente.

## Consequências

- Reduz a quantidade de campos preenchidos manualmente no cadastro e elimina uma fonte de inconsistência entre e-mail e matrícula/apelido digitados separadamente.
- Cria uma dependência forte no formato do e-mail institucional: uma mudança futura no padrão de e-mails da UnB (ex.: novo domínio, novo formato de e-mail para servidores) quebraria a extração e exigiria ajuste no sistema.
- Para Professor/Servidor, como qualquer texto antes do "@" é aceito como apelido, e-mails fora do padrão nome.sobrenome (nomes compostos, abreviações, números por duplicidade) geram apelidos menos legíveis, mas o cadastro não trava por causa disso.
- A regra de colisão de apelido (rejeitar e pedir apelido manual) é simples de implementar, mas depende de a extração para Professor/Servidor ser de fato rara o suficiente para não frustrar muitos cadastros; se isso mudar na prática, a decisão deve ser revisitada.
