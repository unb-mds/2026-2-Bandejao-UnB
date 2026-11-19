# Aviso de privacidade do Bandejão

**Versão:** 2026-11-14

O Bandejão é um aplicativo feito por estudantes da disciplina de Métodos de
Desenvolvimento de Software (MDS) da UnB para a comunidade acadêmica. **Não é
um serviço oficial da UnB nem do Restaurante Universitário.** Este aviso
explica quais dados pessoais o Bandejão guarda, para quê, por quanto tempo e
como você pode pedir acesso, correção ou exclusão, conforme a Lei Geral de
Proteção de Dados (Lei nº 13.709/2018, LGPD).

Quem cuida dos seus dados é a equipe do Bandejão. O contato é
**equipe@bandejaounb.com.br**.

## 1. Sem conta

Você pode ver o cardápio, as avaliações e a previsão da fila sem criar conta.
Nesse caso, o Bandejão não guarda nenhum dado que identifique você:

- o campus e os filtros que você escolhe ficam salvos só no seu aparelho,
  para a tela já abrir do jeito que você deixou;
- se você permitir, o aplicativo usa a localização para abrir a tela do
  campus em que você está, mas essa conta é feita no seu aparelho e as
  coordenadas não saem dele (seção 5);
- ao abrir o aplicativo, o navegador recebe o cookie de segurança descrito na
  seção 3, que não identifica você.

## 2. Dados que guardamos quando você cria uma conta

| Dado | Para quê |
|---|---|
| Tipo de usuário (estudante ou professor/servidor) | Saber quais campos pedir no cadastro |
| Matrícula (estudante) ou SIAPE (professor/servidor) | Garantir uma conta por pessoa |
| E-mail institucional (`@aluno.unb.br` ou `@unb.br`) | Entrar na conta, confirmar a conta e enviar o link de redefinição de senha |
| Apelido | Identificar você nas avaliações e, se quiser, no ranking |
| Senha | Entrar na conta. Guardamos só uma versão embaralhada (hash), nunca a senha em si |
| Data e versão deste aviso que você aceitou | Comprovar o seu consentimento |
| Situação da conta (pendente, ativa, suspensa ou removida) e data de criação | Saber se a conta pode entrar |
| Tentativas de login erradas e horário de bloqueio | Bloquear a conta por alguns minutos depois de várias senhas erradas |
| Links de confirmação de e-mail e de redefinição de senha | Conferir o link quando você o abre. Guardamos só uma versão embaralhada do link, com a validade |

A matrícula e o SIAPE são conferidos só pelo formato: o Bandejão não consulta
nenhum sistema da UnB.

## 3. Dados gerados pelo uso do aplicativo

- **Avaliações:** a nota e o comentário que você deixa sobre uma refeição
  ficam ligados à sua conta.
- **Check-in:** quando você tenta fazer check-in no RU, guardamos o campus, a
  refeição, a data, a hora, a faixa de 15 minutos em que você chegou e se o
  check-in foi confirmado ou recusado. Quando é recusado, guardamos também o
  motivo (por exemplo, fora do horário, check-in repetido ou localização não
  confirmada). Esses registros servem para calcular a previsão de movimento
  da fila e os seus pontos.
- **Pergunta de saída da fila:** depois do check-in, o aplicativo pode
  perguntar se você já saiu da fila. Guardamos a sua resposta, a hora em que
  você respondeu e o tempo de espera calculado a partir dela, para estimar o
  tempo de espera de cada faixa de horário.
- **Pontos, sequência e ranking:** guardamos os seus pontos totais, os pontos
  de cada semestre em cada campus, a sua sequência de semanas com check-in e
  se você escolheu aparecer no ranking. A patente é calculada a partir dos
  pontos.
- **Cookies:** são dois, e os dois são necessários para o aplicativo
  funcionar.
  - O **cookie de segurança** (CSRF) é gravado ao abrir o aplicativo, com ou
    sem conta. Ele protege contra pedidos falsificados por outros sites e não
    identifica você.
  - O **cookie de sessão** é gravado quando você entra na conta. Ele vale por
    14 dias e é renovado a cada uso. Sair da conta o encerra.

  Não usamos cookies de publicidade nem ferramentas de análise de uso.
- **Registros técnicos:** o servidor pode registrar informações técnicas das
  requisições (como data, hora, página acessada e endereço IP) para
  diagnosticar falhas e se defender de ataques. O conteúdo dos formulários de
  cadastro e login não é registrado.

## 4. Base legal

- **Consentimento** (LGPD, art. 7º, I): a conta, as avaliações, o check-in, a
  localização, a pergunta de saída da fila, os pontos e o ranking. Você dá o
  consentimento ao aceitar este aviso no cadastro e pode revogá-lo excluindo
  a conta (seção 9).
- **Legítimo interesse** (LGPD, art. 7º, IX): os dados de segurança da conta
  (tentativas de login e bloqueio), os cookies necessários e os registros
  técnicos do servidor, usados só para proteger o aplicativo e as contas.

## 5. Localização

O aplicativo pede permissão para usar a localização do aparelho, com ou sem
conta. Você pode negar. Ela tem dois usos:

- **Abrir a tela do campus em que você está.** Essa conta é feita **no seu
  aparelho**: as coordenadas não são enviadas ao Bandejão.
- **Confirmar o check-in.** Só nesse momento as coordenadas são enviadas ao
  servidor, uma vez, para conferir se você está perto do RU. Elas são
  descartadas logo em seguida, aconteça o que acontecer. Fica registrado só se
  o check-in foi confirmado ou recusado, e o motivo.

**O Bandejão não guarda as suas coordenadas.** Sem a permissão, você escolhe
o campus na mão e o check-in não fica disponível, mas o resto do aplicativo
funciona normalmente.

## 6. O que fica público

- **O seu apelido** aparece junto das suas avaliações.
- **No ranking,** só aparece quem escolheu participar, e só com a posição, o
  apelido e a patente, sem os pontos. Você pode sair do ranking quando quiser.

Matrícula, SIAPE e e-mail **nunca** aparecem para outros usuários.

## 7. Quem tem acesso

- **A equipe do Bandejão.** Só membros nomeados da equipe acessam o banco de
  dados diretamente. Eles podem ver a matrícula ou o SIAPE ligados a um
  apelido para moderar avaliações e tratar denúncias, como uma matrícula usada
  por outra pessoa.
- **Prestadores de serviço:** o aplicativo fica hospedado na Microsoft Azure,
  e os e-mails automáticos (confirmação de conta e redefinição de senha) são
  enviados pelo Brevo, que recebe o seu e-mail institucional para isso.

Não vendemos nem compartilhamos os seus dados com mais ninguém, nem para
publicidade.

## 8. Por quanto tempo guardamos

- **Cadastro não confirmado:** se você não confirmar o e-mail em 24 horas, a
  conta pendente é apagada.
- **Check-ins e respostas da pergunta de saída:** a ligação desses registros
  com a sua conta dura 4 semanas. Depois disso, fica só o registro anônimo
  (campus, refeição, data, faixa de 15 minutos e tempo de espera), usado na
  previsão da fila.
- **Pontos e sequência:** ficam ligados à sua conta enquanto ela existir, sem
  o histórico dos check-ins, respostas e avaliações que os geraram.
- **Conta e apelido:** enquanto a conta existir. Na exclusão, são apagados
  (seção 9).
- **Avaliações:** enquanto a conta existir, ligadas a ela. Depois da
  exclusão, continuam publicadas sem ligação com a sua conta (seção 9).
- **Cópias de segurança:** o banco de dados é copiado uma vez por dia, e cada
  cópia é guardada por até 7 dias. Por isso, os dados de uma conta excluída
  somem de todas as cópias em até 7 dias depois da exclusão.

## 9. Exclusão da conta

Para excluir a sua conta, escreva para **equipe@bandejaounb.com.br** a partir
do seu e-mail institucional. Na exclusão:

- você não consegue mais entrar, e as suas sessões são encerradas;
- os seus pontos e a sua sequência são apagados, e você sai do ranking na
  hora;
- os seus check-ins e respostas deixam de ser ligados à sua conta na hora;
- **a conta é apagada de vez:** matrícula ou SIAPE, e-mail, apelido, a versão
  embaralhada da senha e os links de confirmação deixam de existir;
- as suas avaliações continuam publicadas, mas aparecem como "usuário
  removido", sem ligação com a sua conta. Se o texto de alguma delas puder
  identificar você, ou se preferir, peça no mesmo e-mail que elas também
  sejam apagadas;
- as cópias de segurança do banco são substituídas em até 7 dias, e com elas
  somem os dados da conta excluída (seção 8).

Depois da exclusão, você pode criar uma conta nova com a mesma matrícula/SIAPE
e o mesmo e-mail.

## 10. Os seus direitos

Pela LGPD, você pode pedir à equipe, pelo e-mail
**equipe@bandejaounb.com.br**:

- a confirmação de que tratamos os seus dados e uma cópia deles;
- a correção de dados incompletos ou errados (o apelido é escolhido só no
  cadastro e não pode ser trocado depois);
- a exclusão da conta, como descrito na seção 9;
- informações sobre com quem os seus dados são compartilhados;
- a revogação do seu consentimento, que é feita pela exclusão da conta.

Respondemos pelo mesmo e-mail. O pedido de cópia dos seus dados é atendido
em até 15 dias (LGPD, art. 19). Você também pode reclamar à Autoridade
Nacional de Proteção de Dados (ANPD).

## 11. Mudanças neste aviso

Quando este aviso mudar, a data da versão no topo muda junto. Na próxima vez
que você entrar, o aplicativo mostra o novo texto para você dar ciência, e o
check-in só volta a funcionar depois disso.
