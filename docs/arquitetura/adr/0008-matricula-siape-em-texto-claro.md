# ADR 0008 — Matrícula/SIAPE armazenada em texto claro, com acesso restrito

**Status:** Aceita
**Data:** 2026-09-28
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

A matrícula/SIAPE é dado pessoal (RNF07, LGPD) e nunca pode ser exibida a outros usuários (RI10). Ao mesmo tempo, o sistema precisa:

- **garantir unicidade:** cada matrícula/SIAPE pertence a uma única conta (RF01);
- **buscar a conta pela matrícula/SIAPE** no login (RF03), na recuperação de senha (RF04) e no reenvio de confirmação;
- **recuperar a matrícula a partir do apelido** para moderação e matrícula contestada, e por isso ela **não pode** ser guardada como hash irreversível (RNF07, RNF08, ADR 0004).

Os documentos de arquitetura divergiam:

- o dicionário de dados (C4 Banco) define `matricula_siape` como `CharField` em texto claro, com `UNIQUE`;
- o Nível 4 de Cadastro/Autenticação define `identificadorCifrado`, com criptografia simétrica.

A criptografia simétrica comum (como AES-GCM) gera um texto cifrado diferente a cada gravação. Com ela, a restrição `UNIQUE` e a busca por igualdade no login deixam de funcionar. Para ter as duas coisas seria preciso um "índice cego" (HMAC da matrícula, com chave separada) mais o valor cifrado, com gestão de duas chaves. É uma complexidade alta para uma equipe iniciante, com prazo até 25/11.

O RNF07 exige que a matrícula seja recuperável e de **acesso restrito à equipe**. Ele não exige criptografia.

## Decisão

A matrícula/SIAPE é armazenada **em texto claro**, na coluna `USUARIO.matricula_siape` (`CharField(9)`, `UNIQUE`, indexada), conforme o dicionário de dados. A proteção vem do controle de acesso, e não de criptografia na coluna:

- **Banco:** acesso direto restrito aos membros nomeados da equipe (ADR 0004), com credenciais individuais e não compartilhadas informalmente. O usuário de banco da aplicação não é o mesmo da equipe.
- **API:** nenhum serializer público inclui `matricula_siape` ou `email_institucional` (RI10). Há teste automatizado que verifica isso nas respostas de avaliação, histórico e sessão.
- **Logs:** matrícula/SIAPE e senha não são gravadas em log de aplicação nem de acesso. As rotas de cadastro, login, recuperação e reenvio não registram o corpo da requisição.
- **Backups:** mesmo nível de acesso restrito do banco de produção.
- **Transporte:** HTTPS em toda comunicação (RNF04), e conexão da aplicação com o banco criptografada quando a hospedagem oferecer.

O campo `identificadorCifrado` do Nível 4 de Cadastro/Autenticação passa a se chamar `matriculaSiape`, igual ao dicionário de dados.

## Consequências

- `UNIQUE` e busca no login funcionam direto pelo ORM, iguais em SQLite e MySQL, sem gestão de chaves.
- A moderação por acesso direto (ADR 0004) consegue ler a matrícula a partir do apelido sem ferramenta extra.
- **Risco aceito:** um vazamento do banco ou de um backup expõe as matrículas/SIAPEs de todos os usuários em texto claro. O impacto é limitado (matrícula não é credencial nem dá acesso a nada no Bandejão), mas é dado pessoal. A política de privacidade (US-RNF07.1) deve refletir isso honestamente.
- O Nível 4 de Cadastro/Autenticação precisa ser atualizado (`identificadorCifrado` → `matriculaSiape`, e a nota sobre armazenamento recuperável).
- Se o sistema continuar no ar após a disciplina, ou se o número de usuários crescer muito, esta decisão deve ser revista.

## Alternativas consideradas

- **Criptografia simétrica com índice cego (HMAC):** protege contra vazamento do banco sem as chaves e mantém unicidade e busca. Descartada por ora pelo custo de implementar e operar duas chaves. É o caminho natural de evolução.
- **Hash irreversível (como a senha):** mantém unicidade e busca, mas impede recuperar a matrícula a partir do apelido. Descartada por violar o RNF07 e a ADR 0004.
- **Criptografia de disco ou de banco pela hospedagem:** complementar, não substitui o controle de acesso. Pode ser adotada se a hospedagem oferecer sem custo (SP-02).

## Relacionadas

- Requisitos: RF01, RF03, RF04, RNF04, RNF07, RNF08, RI10, L01.
- `docs/adr/0002-matricula-apelido-extraidos-do-email.md`.
- `docs/adr/0004-acesso-direto-da-equipe-ao-banco.md`.
- `C4-niveis-3-4-banco-de-dados-bandejao.md` (`USUARIO.matricula_siape`).
- `c4-nivel-4-cadastro-autenticacao.md` (`Conta.identificadorCifrado`).
