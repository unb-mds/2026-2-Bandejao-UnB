# ADR 0002 — Matrícula e apelido extraídos do e-mail institucional

**Status:** Aceita
**Data:** 2026-09-24 (revisada em 2026-11-14: limitações conhecidas da matrícula de estudante e prefixo conferido só pelo ano)
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

## Limitações conhecidas (revisão de 2026-11-14)

A extração da matrícula depende de regras de formato que só foram conferidas
em parte. Elas ficam registradas aqui e na seção de limitações do Documento
de Requisitos (L10 e L16):

- **Matrícula de 8 dígitos (L10).** Só a matrícula de 9 dígitos, em uso
  desde 2010, é aceita. Quem tem matrícula anterior não consegue se
  cadastrar. Isso já estava decidido e não muda.
- **Outros níveis de ensino (L16).** As regras da RN01 (9 dígitos, ano no
  prefixo, 6 dígitos finais sem sequência óbvia) foram conferidas só com
  matrículas de graduação. Na graduação, o 3º dígito indica o semestre de
  ingresso e é sempre `1` ou `2`. Para a pós-graduação e os outros níveis,
  que usam o mesmo domínio `@aluno.unb.br`, o formato não foi confirmado.
- **Por isso, o prefixo passa a conferir só o ano.** Os 2 primeiros dígitos
  precisam ser um ano entre 2010 e o ano corrente, calculado pela data do
  sistema, e o 3º dígito pode ser qualquer um. Antes, o prefixo conferia o
  código de ano/semestre (de `101` ao semestre corrente), o que recusaria
  um estudante de outro nível com outro 3º dígito, e dependia de uma
  aproximação do semestre pelo calendário civil, que não segue o
  calendário letivo da UnB. O método mantém o nome do Nível 4
  (`validarPrefixoAnoSemestre`).
- **O tamanho de 9 dígitos continua sendo uma suposição para os outros
  níveis.** O login usa o tamanho para separar matrícula (9) de SIAPE (7)
  (RF03.1). Se a matrícula de outro nível tiver outro tamanho, essa pessoa
  não consegue se cadastrar, e a correção exige revisar a RN01 e o RF03.1
  juntos.
- **A defesa real é a confirmação do e-mail.** A matrícula sai do e-mail, e
  a conta só funciona depois que a pessoa abre o link enviado para aquela
  caixa (RF02). Uma matrícula inventada gera um e-mail que não existe, e a
  conta pendente é apagada em 24 horas. As regras de formato servem como
  filtro de erro de digitação, e afrouxar o prefixo não abre brecha de
  segurança.

**Pendente:** confirmar o formato da matrícula com estudantes de outros
níveis de ensino. Se for diferente, revisar a RN01, o RF03.1 e esta ADR.
