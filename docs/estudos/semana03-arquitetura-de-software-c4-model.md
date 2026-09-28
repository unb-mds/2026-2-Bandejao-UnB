# Arquitetura de Software (C4 Model)

**Integrante:** Álvaro Bento Moura da Silva
**Semana:** semana-03
**Data:** 2026-09-22
**Tags:** arquitetura, c4-model, backend, django-rest-framework

## Resumo

O C4 Model é uma abordagem prática criada por Simon Brown para documentar arquitetura de software em quatro níveis de zoom crescente — do mais amplo ao mais detalhado, de forma parecida com o Google Maps. Os quatro níveis são: Contexto (o sistema e quem interage com ele), Containers (as peças executáveis, como apps, APIs e bancos), Componentes (o que existe dentro de um container) e Código (classes e funções, geralmente dispensável). O modelo não exige uma ferramenta específica e evita documentações gigantescas e desatualizadas, por ser dividido em camadas fáceis de manter.

## Aplicação no projeto

No RU-UnB, backend, frontend e banco de dados são containers do nível 2. Os níveis 1 e 2 serão feitos uma vez, em conjunto pelo grupo em reunião, por mostrarem o sistema inteiro; o nível 3 será um diagrama por área (backend, frontend, banco), sendo que no banco esse nível costuma virar um modelo entidade-relacionamento em vez de componentes de código. O Flutter, se usado, entraria como a tecnologia do container de frontend (nível 2), sem substituir backend nem banco.

Ideia inicial do nível 1: o sistema aparece como uma caixa única, com Visitante e Usuário cadastrado como pessoas (Estudante e Professor/Servidor viram uma caixa só, pois o sistema trata os dois igual) e a Equipe, que opera moderação e alertas. Como sistemas externos: o site do RU (origem do PDF do cardápio) e um serviço de e-mail (usado em RF02 e RF04). O GPS da Release 2 não vira sistema externo, só nota da PWA. Fica registrado como decisão consciente que não há integração com sistemas da UnB para validar matrícula — só o formato é conferido (L01).

Ideia inicial do nível 2: rascunho inicial, com duas decisões em aberto destacadas: o acesso direto da Equipe ao banco para moderação manual (RNF08), que precisa ser restrito por causa dos dados recuperáveis de matrícula/SIAPE (RNF07); e se o Leitor do PDF deve ser um módulo do backend ou um processo/container separado — considerado o maior risco técnico do MVP, a ser testado cedo com o PDF do RU do Gama.

Para o backend (nível 3): a estrutura é um monolito modular, com cada módulo em camadas Controller/Router → Service → Repository → Model/Entity. Os módulos de domínio saem direto dos requisitos (Identidade, Cardápio, Leitor do PDF, Avaliações, Fila na Release 2, Configuração, Transversais). O nível 3 do backend mapeia cada módulo a um app Django, e o nível 4 mostra o padrão de classes que se repete dentro de cada app do Django REST Framework: Model (ORM) → Serializer (validação e formatação) → ViewSet (orquestra a resposta) → URLconf (mapeia a rota).

## Principais conceitos / como usar

- **Os 4 níveis do C4:**
  - Nível 1 (Contexto): sistema como caixa única + pessoas + sistemas externos. Visão mais macro, serve para público técnico e não técnico.
  - Nível 2 (Containers): as peças executáveis do sistema (apps, APIs, bancos, filas), com tecnologia e comunicação entre elas. *Atenção: "container" aqui não é Docker* — é qualquer coisa que roda ou guarda dados separadamente.
  - Nível 3 (Componentes): abre um container para mostrar módulos, controladores e serviços internos.
  - Nível 4 (Código): classes, interfaces, funções — geralmente evitado ou gerado por ferramenta, por ficar obsoleto rápido.
- **Benefícios do modelo:** clareza de comunicação (serve para devs e para gestores/clientes), independência de ferramenta (papel, Miro, draw.io), combate à obsolescência por ser dividido em camadas fáceis de manter.
- **Arquitetura em camadas (backend):** Controller/Router recebe a requisição → Service aplica as regras de negócio → Repository acessa o banco → Model/Entity representa os dados.
- **Por que monolito modular, e não microsserviços:** microsserviços fazem sentido quando módulos diferentes precisam escalar de forma independente, times diferentes trabalham em paralelo sem se atropelar, ou partes do sistema têm ciclos de deploy muito distintos. Nenhum desses cenários se aplica ao RU-UnB: é um grupo pequeno, com prazo acadêmico definido, e nenhum módulo (Identidade, Cardápio, Avaliações) tem motivo para escalar separadamente dos outros. Microsserviços também trazem custo extra — orquestração, comunicação entre serviços, múltiplos deploys — que a equipe não tem experiência para bancar dentro do prazo. Um monolito modular entrega o mesmo benefício de organização (módulos com fronteiras claras, RNF06) sem esse custo, e ainda deixa a porta aberta: se um módulo específico crescer muito no futuro (o Leitor de PDF é o candidato mais provável), dá para promovê-lo a um serviço separado depois, já que a fronteira interna já existe.
- **Tarefas agendadas (jobs):** relevantes para coleta periódica do cardápio e cálculo de previsão de pico.
- **Integrações externas:** a origem do cardápio (PDF) e a forma de medir a fila entram como sistemas externos no nível 1.
- **Autenticação:** o RF04 exige encerrar todas as sessões ativas do usuário quando ele redefine a senha. Isso pesa contra o uso de JWT puro, que é difícil de revogar antes do vencimento do token, e a favor de sessão gerenciada pelo servidor ou de refresh tokens revogáveis. Essa escolha ainda não foi feita — precisa virar uma decisão registrada (ADR) antes de começar a implementar o módulo Identidade.
- **ORM e validação de dados:** conforme o framework escolhido para o backend (no nosso caso, Django REST Framework: models para o ORM, serializers para validação e formatação).

## Fontes / materiais usados

- Site oficial do C4 Model — [c4model.com](https://c4model.com)
- Trechos da palestra de Simon Brown, "The C4 model for visualising software architecture"
- Artigo "Entendendo o C4 Model: uma abordagem para arquitetura de software", CajuDevs (Medium) — [medium.com/cajudevs/entendendo-o-c4-model](https://medium.com/cajudevs/entendendo-o-c4-model-uma-abordagem-para-arquitetura-de-software-3ed0f007ae66)
