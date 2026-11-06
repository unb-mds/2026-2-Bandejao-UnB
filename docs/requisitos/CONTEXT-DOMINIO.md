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
Vínculo declarado no cadastro: Estudante (matrícula) ou Professor/Servidor (SIAPE/matrícula funcional). É um único tipo interno: a tela de cadastro oferece "Professor" e "Servidor" como duas opções separadas por clareza para quem preenche, mas as duas levam ao mesmo fluxo e são o mesmo Tipo de usuário no sistema.

**Matrícula / SIAPE**
Identificador institucional associado à conta. Para Estudante, é extraído do E-mail institucional informado no cadastro, não digitado separadamente. Para Professor/Servidor, é informado diretamente no cadastro. É dado privado: nunca é exibido a outros usuários.

**E-mail institucional**
E-mail da UnB informado no cadastro, único canal de confirmação de cadastro e de recuperação de senha. Para Estudante, segue o formato `matricula@aluno.unb.br`, do qual o sistema extrai a Matrícula. Para Professor/Servidor, é um e-mail `@unb.br`, geralmente no formato nome.sobrenome, do qual o sistema extrai o Apelido.

**Apelido**
Nome público do usuário, escolhido uma única vez no cadastro e único entre os usuários. É sob ele que as avaliações e, para quem optar por aparecer, o Ranking são exibidos. Para Estudante, é escolhido manualmente no cadastro; para Professor/Servidor, é extraído automaticamente do E-mail institucional (o texto antes do "@").
_Evitar:_ "nome do usuário".

## Lugares

**RU (Restaurante Universitário)**
Restaurante oficial da UnB em um campus. É o único tipo de restaurante coberto pelo Bandejão.

**Restaurante Executivo**
Restaurante do Campus Darcy Ribeiro. Fora do escopo do Bandejão.

**Campus**
Unidade da UnB com RU: Darcy Ribeiro, Ceilândia, Gama, Planaltina e Fazenda Água Limpa.

**Campus detectado**
Campus em que o dispositivo do usuário ou visitante se encontra, identificado pela localização no início de uma sessão de uso. Não é o mesmo que estar no RU: basta estar dentro da área do campus.
_Evitar:_ confundir com a confirmação de localização do Check-in, que exige estar nas imediações do RU.

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
Registro de presença do usuário no RU de um campus durante uma refeição. Junto com a Saída da fila, é a fonte de dados da fila: ela é estimada exclusivamente a partir do que os próprios usuários informam sobre a sua presença e a sua saída da fila. Não há votação sobre o nível da fila nem sensores.

**Nível de fila**
Classificação em quatro níveis: vazia, curta, moderada e longa. Aplica-se tanto à Previsão de pico quanto ao Nível agora.

**Previsão de pico**
Níveis de fila esperados em cada faixa de horário de uma refeição, calculados a partir do histórico de check-ins.

**Nível agora**
Nível de fila atual da refeição em andamento, calculado a partir dos check-ins recentes.

**Saída da fila**
Momento em que o usuário, depois de um Check-in, deixa a fila e começa a comer, informado por ele mesmo ao responder a pergunta de saída da fila. É, junto com a Desistência, o único desfecho posterior ao Check-in registrado pelo sistema: o fim da refeição não é registrado.
_Evitar:_ "fim da refeição" ou "terminou de comer" para este evento.

**Tempo de espera**
Intervalo entre o Check-in e a Saída da fila de um mesmo usuário em uma refeição. Só existe para check-ins que tiveram Saída da fila informada.

**Desistência**
Resposta do usuário à Pergunta de saída da fila informando que desistiu de comer no RU depois de ter feito o Check-in. Não gera Saída da fila nem Tempo de espera.

**Pergunta de saída da fila**
Pergunta feita ao usuário, algum tempo depois do Check-in, sobre se ele já saiu da fila e começou a comer. Sua resposta é a fonte da Saída da fila.

**Espera estimada**
Estimativa, em minutos, do Tempo de espera em uma faixa de horário de uma refeição, calculada a partir do histórico de Tempos de espera. Acompanha a Previsão de pico quando há dados suficientes; não substitui o Nível de fila.

## Gamificação

**Contribuição**
Ação de um Usuário que alimenta os dados do Bandejão: um Check-in, uma resposta à Pergunta de saída da fila (qualquer uma das respostas, inclusive a Desistência) ou uma Avaliação.
_Evitar:_ "participação" ou "engajamento" para este conceito. Consultar o cardápio não é Contribuição.

**Pontos**
Valor numérico que um Usuário acumula ao fazer Contribuições. É a base da Patente e do Ranking. Pertencem ao Usuário (a conta), não à pessoa: quem tem dois Usuários tem duas pontuações separadas.

**Patente**
Título que um Usuário ganha ao acumular Pontos, indicando seu grau de Contribuição.
_Evitar:_ "nível", que no Bandejão já significa Nível de fila.

**Sequência**
Quantidade de semanas consecutivas em que um Usuário fez Check-ins em dias suficientes para a semana contar. Não conta dias nem Refeições consecutivas.
_Evitar:_ "streak" e "dias seguidos".

**Ranking**
Lista pública, por Campus, dos Usuários que optaram por aparecer nela, ordenada pelos Pontos obtidos naquele Campus no semestre letivo corrente da UnB e exibindo o Apelido, a Patente e, quando houver, o Distintivo de cada um. Recomeça do zero a cada semestre letivo. Quem não optou não aparece.
_Evitar:_ confundir com a Patente: a Patente é pessoal e acumulada, o Ranking compara Usuários.

**Distintivo**
Marca pública exibida ao lado do Apelido, no Ranking e nas Avaliações, que reconhece a colocação de um Usuário no Ranking de um semestre letivo. Hoje existe um único Distintivo: a Bandeja de Ouro.
_Evitar:_ "ícone", "selo" (os Selos de conquista são outro conceito, do Backlog) e "perfil" (o Bandejão não tem perfil público; o Apelido só aparece no Ranking e nas Avaliações).

**Bandeja de Ouro**
Distintivo dos 30 primeiros colocados do Ranking de um Campus ao fim de um semestre letivo. Vale durante o semestre letivo seguinte e precisa ser reconquistado para continuar.
_Evitar:_ "sommelier" ou "avaliador": a colocação vem de todas as Contribuições, não só das Avaliações.
