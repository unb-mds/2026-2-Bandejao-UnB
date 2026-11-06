# ADR 0012 — Hospedagem na Azure for Students e e-mail transacional pelo Brevo

**Status:** Aceita (revisada)
**Data:** 2026-11-06 (revisão; a primeira versão, de 2026-11-05, escolhia uma VPS da Hostinger)
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

A hospedagem e o provedor do Serviço de E-mail estavam em aberto desde o
início do projeto (4.4 e 9.2 do Documento de Visão, Níveis 1 e 2 do C4). As
ADRs anteriores já fixavam o que a hospedagem precisa oferecer:

- **cron do sistema operacional** para o Leitor de Cardápio e as demais
  tarefas periódicas do backend (ADR 0003, ADR 0007);
- **MySQL 8 `utf8mb4`** em produção (ADR 0001), com acesso direto da equipe
  para moderação (ADR 0004) e usuário de banco da aplicação separado do da
  equipe (ADR 0008);
- **PWA e API no mesmo domínio**, para o cookie de sessão `SameSite`
  funcionar sem CORS com credenciais (ADR 0007);
- HTTPS em toda comunicação (RNF04).

O Serviço de E-mail envia a confirmação de cadastro (RF02), a redefinição de
senha (RF04) e os alertas de falha do Leitor (ADR 0006). As mensagens precisam
chegar às caixas `@aluno.unb.br` e `@unb.br` sem cair no spam.

Em 05/11, a primeira versão desta ADR escolheu uma VPS da Hostinger, pensando
em manter o sistema no ar depois da disciplina com custo baixo e previsível.
Em 06/11, a monitoria recomendou usar um crédito de estudante para a entrega.
Com isso, o objetivo da hospedagem mudou: **ela atende a entrega da
disciplina** (Release 2, 25/11/2026). Se a equipe decidir manter o sistema no
ar depois, a hospedagem será reavaliada, inclusive quanto a uma opção que
suporte mais tráfego.

Duas opções com crédito de estudante foram citadas:

- **DigitalOcean pelo GitHub Student Developer Pack:** a DigitalOcean saiu do
  pacote em 2026, e os créditos de US$ 200 só podiam ser resgatados até
  31/07/2026. A oferta não está mais disponível.
- **Azure for Students:** US$ 100 de crédito, sem cartão de crédito, válido
  por 12 meses, para quem tem e-mail institucional. Renovável enquanto houver
  vínculo estudantil.

## Decisão

### Hospedagem

O Bandejão é hospedado numa **máquina virtual Linux da Azure**, paga com o
crédito da assinatura **Azure for Students**, com Docker Compose. A
arquitetura de implantação é a mesma da primeira versão desta ADR; só muda o
provedor:

- **VM pequena** da série B (2 GB de RAM ou mais), com Ubuntu LTS. O tamanho e
  a região são escolhidos pela calculadora de preços da Azure, para o crédito
  cobrir pelo menos até a entrega.
- **Caddy** como servidor web e proxy reverso, com certificado HTTPS
  automático. Ele serve o build do PWA na raiz do domínio e encaminha `/api/`
  (e `/admin/`, se usado) ao backend. Assim, PWA e API ficam no mesmo domínio,
  como exige a ADR 0007.
- **Backend Django** servido por Gunicorn.
- **MySQL 8** `utf8mb4`, com isolamento READ COMMITTED, num container dentro
  da VM, acessível apenas pela rede interna. A porta do banco não é exposta à
  internet. O banco gerenciado da Azure (Azure Database for MySQL) não é
  usado, porque consumiria o crédito rapidamente.
- **Cron do sistema operacional** da VM chamando os comandos do Django (ADR
  0003, BD-07).
- **IP público estático** na VM, apontado pelo DNS do domínio.
- **Grupo de segurança de rede** (NSG) liberando só as portas 22 (SSH), 80 e
  443 de entrada.
- Segredos (chave do Django, senhas do banco, chave do Brevo) ficam em
  variáveis de ambiente na VM, fora do repositório.

O domínio de produção continua **`bandejaounb.com.br`**, no registrador onde
foi contratado. Só o registro DNS passa a apontar para o IP da VM.

### Serviço de E-mail

- **Envio:** os e-mails automáticos (RF02, RF04 e alertas da ADR 0006) saem
  pelo **Brevo**, via SMTP autenticado na **porta 587**, inicialmente no
  **plano gratuito**. A Azure bloqueia a saída pela porta 25, mas não o envio
  autenticado a um provedor pela 587. Se a 587 falhar, o Brevo também aceita
  a porta 2525. Como último recurso, o envio passa para a **API HTTP do
  Brevo** (porta 443) com a biblioteca `django-anymail`, trocando só o
  `EMAIL_BACKEND` nas configurações, sem mudar o código que envia os e-mails.
- **Remetente:** **`nao-responda@bandejaounb.com.br`**. O domínio é
  verificado no Brevo, com registros SPF, DKIM e DMARC no DNS.
- **Recebimento:** o endereço **`equipe@bandejaounb.com.br`** é o canal de
  contato divulgado no site (RNF08) e o destinatário dos alertas do Leitor
  (ADR 0006). Ele é encaminhado para a caixa da equipe,
  `equipe.bandejao@gmail.com`.

### Contas

- A conta `equipe.bandejao@gmail.com` é a conta-mestra da equipe. Com ela são
  criadas a conta do Brevo e a do registro do domínio, para que nenhum desses
  serviços dependa do e-mail pessoal de um membro.
- A assinatura **Azure for Students** exige o e-mail institucional de um
  estudante e fica presa ao vínculo dele. Ela é criada por um membro, que dá
  acesso aos demais pelo controle de acesso (IAM) da assinatura. O nome de
  quem é dono da assinatura fica registrado nas instruções de deploy.

## Consequências

- Todas as exigências das ADRs 0001, 0003, 0004, 0007 e 0008 são atendidas
  sem mudar a arquitetura: o Caddy, o Docker Compose e o cron são
  infraestrutura de deploy e não aparecem como containers nos diagramas C4.
  As relações de e-mail continuam marcadas como `[SMTP]` nos diagramas.
- A entrega não tem custo para a equipe, desde que o consumo fique dentro do
  crédito. O Brevo começa sem custo.
- **O crédito é limitado e tem prazo.** Recursos esquecidos ligados (discos,
  IPs, VMs de teste) consomem o crédito. Quando ele acaba, a Azure desliga os
  recursos, e a VM sai do ar. A equipe acompanha o consumo no portal e
  configura um alerta de orçamento.
- **A assinatura depende do vínculo estudantil** do membro que a criou. Se
  esse vínculo acabar, a assinatura não é renovada.
- A equipe passa a ser responsável pela manutenção da VM: atualizações de
  segurança do sistema, acesso SSH apenas por chave, NSG liberando só as
  portas 22, 80 e 443, e backup diário do banco guardado fora da VM, com o
  mesmo acesso restrito do banco de produção (ADR 0008).
- O acesso direto da equipe ao banco (ADR 0004) é feito por túnel SSH até a
  VM, com chave SSH individual por membro e usuário de banco individual.
- A conexão entre a aplicação e o banco não sai da VM, e o acesso da equipe
  passa pelo túnel SSH, que já é criptografado (ADR 0008).
- O plano gratuito do Brevo tem limite diário de envio. Num pico de
  cadastros, como no lançamento, o limite pode ser atingido e os e-mails
  restantes deixam de ser enviados naquele dia, inclusive os alertas do
  Leitor, que compartilham o mesmo limite. O reenvio da confirmação (RF02)
  cobre os cadastros afetados. Se os picos se repetirem, a equipe deve migrar
  para um plano pago do Brevo.
- Trocar de provedor de e-mail, ou de SMTP para a API do Brevo, exige só
  mudar as variáveis de ambiente e o `EMAIL_BACKEND`, sem alterar o código.
- A entrega real em `@aluno.unb.br` e `@unb.br` precisa ser testada a partir
  da VM antes da entrega final (QA-01), conferindo também a caixa de spam.
- Como a arquitetura de implantação é a mesma da Hostinger (Linux, Docker
  Compose, Caddy e cron), mudar de provedor depois da disciplina é levar o
  mesmo `docker-compose.yml`, restaurar o backup do banco e apontar o DNS.
- O site informa que **não é um site oficial da UnB nem do RU**: é feito pela
  comunidade acadêmica para a própria comunidade e usa dados públicos e
  oficiais, como o PDF do cardápio publicado pelo RU.
- As instruções de deploy (BD-05, BD-07) devem registrar como subir o
  servidor do zero, o crontab, o backup e a restauração, o dono da assinatura
  Azure, o vencimento do crédito e do domínio e quem tem acesso a cada conta.

## Alternativas consideradas

- **VPS da Hostinger** (primeira versão desta ADR): atende todas as
  exigências e tem custo baixo e previsível, mas é paga. Para a entrega, o
  crédito de estudante da Azure cobre o mesmo uso sem custo. Continua sendo
  candidata se a equipe mantiver o sistema no ar depois da disciplina.
- **DigitalOcean pelo GitHub Student Developer Pack:** descartada. O crédito
  de estudante deixou de existir em 31/07/2026, e contas novas têm as portas
  de envio de e-mail bloqueadas.
- **Serviços gerenciados da Azure** (App Service e Azure Database for MySQL):
  descartados. Consomem o crédito mais rápido que uma VM e não têm o cron do
  sistema operacional de que o Leitor depende.
- **Hospedagem compartilhada da Hostinger:** descartada. Esses planos são
  voltados a PHP e não permitem manter o processo do Django rodando, agendar
  o cron do sistema nem instalar as bibliotecas do Leitor de Cardápio.
- **Plataformas gratuitas que hibernam (como o plano gratuito do Render):**
  descartadas porque não rodam o cron e demoram a responder no primeiro
  acesso.
- **SMTP do Gmail como provedor de envio:** descartado. Ele limita o envio
  diário, prende o sistema a uma conta pessoal e tem pior entregabilidade.
  E-mails com remetente `@gmail.com` enviados por outro servidor tendem a ser
  rejeitados ou a cair no spam.
- **Servidor de e-mail próprio na VM:** descartado. A Azure bloqueia a porta
  25, e a entregabilidade de um servidor novo é ruim.

## Relacionadas

- Documento de Visão: 4.3, 4.4, 6, 9.1 e 9.2.
- Requisitos: RF02, RF04, RF06, RNF04, RNF07, RNF08.
- `docs/arquitetura/adr/0001-escolha-stack-backend.md` (MySQL em produção).
- `docs/arquitetura/adr/0003-leitor-pdf-como-modulo-do-backend.md` (cron).
- `docs/arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md` (acesso
  da equipe ao banco).
- `docs/arquitetura/adr/0006-alerta-de-falha-do-leitor-por-email.md`
  (destinatário dos alertas).
- `docs/arquitetura/adr/0007-sessao-autenticada-por-cookie-httponly.md`
  (PWA e API no mesmo domínio).
- `docs/arquitetura/adr/0008-matricula-siape-em-texto-claro.md` (acesso ao
  banco e backups).
- `docs/arquitetura/c4-niveis-1-2.md` (Serviço de E-mail e hospedagem).
