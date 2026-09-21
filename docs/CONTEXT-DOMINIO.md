# Bandejão — Glossário do domínio

Vocabulário canônico do projeto Bandejão (Grupo 6, MDS, FCTE/UnB, 2026). É a referência única de termos para o Documento de Visão e o Documento de Requisitos. Contém só definições: regras, parâmetros e decisões de implementação ficam nos requisitos.

## Pessoas

**Frequentadores do RU**
Todas as pessoas que se alimentam nos RUs da UnB, tenham conta no Bandejão ou não. Inclui a Comunidade, terceirizados e externos.

**Comunidade**
Estudantes (com matrícula de aluno) e professores/servidores (com SIAPE/matrícula funcional) da UnB. É o público que pode ter conta no Bandejão.
_Evitar:_ usar "comunidade" para todos que frequentam o RU. Terceirizados e externos frequentam o RU, mas não fazem parte da Comunidade.

**Visitante**
Quem usa o Bandejão sem estar logado, tenha ou não conta. Consulta o cardápio e a previsão de pico, mas não avalia refeições nem faz check-in. É uma condição de uso, não um tipo de pessoa: quem faz login deixa de ser Visitante.

**Usuário**
Conta no Bandejão, ligada a exatamente uma matrícula ou um SIAPE. É a conta que se autentica, avalia e faz check-in, não a pessoa: quem tem mais de uma vinculação (ex.: matrícula de aluno e SIAPE) pode ter mais de um Usuário.
_Evitar:_ usar "usuário" para quem apenas frequenta o RU sem ter conta.

**Tipo de usuário**
Vínculo declarado no cadastro: Estudante (matrícula) ou Professor/Servidor (SIAPE/matrícula funcional).

**Matrícula / SIAPE**
Identificador institucional informado no cadastro. É dado privado: nunca é exibido a outros usuários.

**Apelido**
Nome público do usuário, escolhido uma única vez no cadastro e único entre os usuários. É sob ele que as avaliações aparecem.
_Evitar:_ "nome do usuário".

## Lugares

**RU (Restaurante Universitário)**
Restaurante oficial da UnB em um campus. É o único tipo de restaurante coberto pelo Bandejão.

**Restaurante Executivo**
Restaurante do Campus Darcy Ribeiro. Fora do escopo do Bandejão.

**Campus**
Unidade da UnB com RU: Darcy Ribeiro, Ceilândia, Gama, Planaltina e Fazenda Água Limpa.

## Cardápio

**Refeição**
Cada serviço de café da manhã, almoço ou jantar de um dia em um campus. É a unidade avaliada.

**Categoria**
Linha do cardápio de uma refeição (Bebidas, Guarnição, Sopa, Prato principal ovolactovegetariano…).

**Prato**
Cada opção individual dentro de uma categoria. Não é unidade de avaliação.

**Marcador**
Cada um dos 10 ícones da legenda do cardápio oficial: cogumelo, leite e derivados, mel, pimenta, soja, trigo/glúten, amendoim, oleaginosa, ovo e suíno. Sinaliza a presença de um ingrediente ou característica em um prato.
_Evitar:_ "alérgeno". Nem todos os marcadores são alérgenos, e a ausência de marcador não garante que o prato esteja livre do ingrediente.

**Dieta**
Uma das três linhas de prato principal do cardápio oficial: padrão, ovolactovegetariano e vegetariano estrito (no café da manhã, o "complemento" equivalente).

## Avaliação

**Avaliação**
Nota de 1 a 5 estrelas dada por um usuário a uma refeição, com comentário opcional, exibida com o apelido do autor.

## Fila

**Check-in**
Registro de presença do usuário no RU de um campus durante uma refeição. É a única fonte de dados da fila: não há votação nem sensores.

**Nível de fila**
Classificação em quatro níveis: vazia, curta, moderada e longa. Aplica-se tanto à Previsão de pico quanto ao Nível agora.

**Previsão de pico**
Níveis de fila esperados em cada faixa de horário de uma refeição, calculados a partir do histórico de check-ins.

**Nível agora**
Nível de fila atual da refeição em andamento, calculado a partir dos check-ins recentes.
