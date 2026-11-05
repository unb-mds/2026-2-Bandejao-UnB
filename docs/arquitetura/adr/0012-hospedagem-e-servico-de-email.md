# ADR 0012 — Hospedagem em Hostinger VPS e e-mail transacional pelo Brevo

**Status:** Aceita
**Data:** 2026-11-05
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

Além disso, a equipe pretende manter o sistema no ar após o fim da
disciplina, para ver se a comunidade acadêmica o adota no dia a dia, com
correções eventuais de falhas. Por isso, o custo recorrente precisa ser baixo
e previsível, e a operação, simples para uma equipe iniciante.

## Decisão

### Hospedagem

O Bandejão é hospedado em uma **VPS da Hostinger**, com Linux e Docker
Compose:

- **Caddy** como servidor web e proxy reverso, com certificado HTTPS
  automático. Ele serve o build do PWA na raiz do domínio e encaminha `/api/`
  (e `/admin/`, se usado) ao backend. Assim, PWA e API ficam no mesmo domínio,
  como exige a ADR 0007.
- **Backend Django** servido por Gunicorn.
- **MySQL 8** `utf8mb4`, com isolamento READ COMMITTED, acessível apenas
  pela rede interna da VPS. A porta do banco não é exposta à internet.
- **Cron do sistema operacional** chamando os comandos do Django (ADR 0003,
  BD-07).
- Segredos (chave do Django, senhas do banco, chave SMTP) ficam em variáveis
  de ambiente no servidor, fora do repositório.

O domínio de produção é **`bandejaounb.com.br`**.

### Serviço de E-mail

- **Envio:** os e-mails automáticos (RF02, RF04 e alertas da ADR 0006) saem
  pelo **Brevo**, via SMTP, inicialmente no **plano gratuito**. O remetente é
  **`nao-responda@bandejaounb.com.br`**. O domínio é verificado no Brevo, com
  registros SPF, DKIM e DMARC no DNS.
- **Recebimento:** o endereço **`equipe@bandejaounb.com.br`** é o canal de
  contato divulgado no site (RNF08) e o destinatário dos alertas do Leitor
  (ADR 0006). Ele é encaminhado para a caixa da equipe,
  `equipe.bandejao@gmail.com`.
- **Contas:** a conta `equipe.bandejao@gmail.com` é a conta-mestra da equipe.
  Com ela são criadas as contas da Hostinger (VPS e domínio) e do Brevo, para
  que nenhum serviço dependa do e-mail pessoal de um membro.

## Consequências

- Todas as exigências das ADRs 0001, 0003, 0004, 0007 e 0008 são atendidas
  sem mudar a arquitetura: o Caddy, o Docker Compose e o cron são
  infraestrutura de deploy e não aparecem como containers nos diagramas C4.
- O custo recorrente se limita à VPS e ao domínio. O Brevo começa sem custo.
- A equipe passa a ser responsável pela manutenção do servidor: atualizações
  de segurança do sistema, acesso SSH apenas por chave, firewall liberando só
  as portas 22, 80 e 443, e backup diário do banco guardado fora da VPS, com
  o mesmo acesso restrito do banco de produção (ADR 0008).
- O acesso direto da equipe ao banco (ADR 0004) é feito por túnel SSH até a
  VPS, com chave SSH individual por membro e usuário de banco individual.
- A conexão entre a aplicação e o banco não sai da VPS, e o acesso da equipe
  passa pelo túnel SSH, que já é criptografado (ADR 0008).
- O plano gratuito do Brevo tem limite diário de envio. Num pico de
  cadastros, como no lançamento, o limite pode ser atingido e os e-mails
  restantes deixam de ser enviados naquele dia, inclusive os alertas do
  Leitor, que compartilham o mesmo limite. O reenvio da confirmação (RF02)
  cobre os cadastros afetados. Se os picos se repetirem, a equipe deve migrar
  para um plano pago do Brevo.
- Como o envio é por SMTP comum, trocar de provedor exige só mudar as
  variáveis de ambiente, sem alterar o código.
- A entrega real em `@aluno.unb.br` e `@unb.br` precisa ser testada antes da
  entrega final (QA-01), conferindo também a caixa de spam.
- O site informa que **não é um site oficial da UnB nem do RU**: é feito pela
  comunidade acadêmica para a própria comunidade e usa dados públicos e
  oficiais, como o PDF do cardápio publicado pelo RU.
- As instruções de deploy (BD-05, BD-07) devem registrar como subir o
  servidor do zero, o crontab, o backup e a restauração, o vencimento do
  domínio e da VPS e quem tem acesso a cada conta.

## Alternativas consideradas

- **Hospedagem compartilhada da Hostinger:** descartada. Esses planos são
  voltados a PHP e não permitem manter o processo do Django rodando, agendar
  o cron do sistema nem instalar as bibliotecas do Leitor de Cardápio.
- **Azure (Azure for Students):** viável no primeiro ano, com o crédito de
  estudante. Descartada porque o crédito acaba e depende do vínculo
  estudantil de quem criou a assinatura, o custo depois é em dólar e menos
  previsível, e a equipe não tem experiência com a plataforma.
- **Plataformas gratuitas que hibernam (como o plano gratuito do Render):**
  descartadas porque não rodam o cron e demoram a responder no primeiro
  acesso.
- **SMTP do Gmail como provedor de envio:** descartado. Ele limita o envio
  diário, prende o sistema a uma conta pessoal e tem pior entregabilidade.
  E-mails com remetente `@gmail.com` enviados por outro servidor tendem a ser
  rejeitados ou a cair no spam.
- **Caixa de e-mail da Hostinger como provedor de envio:** descartada para os
  e-mails automáticos, por ter limite de envio pensado para uso pessoal.

## Relacionadas

- Documento de Visão: 4.3, 4.4, 9.1 e 9.2.
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
- `docs/arquitetura/c4-niveis-1-2.md` (Serviço de E-mail).
