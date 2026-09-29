# Review e Retrospectiva das Sprints — Projeto Bandejão UnB (MDS)

## 📌 Visão Geral do Projeto
- **Disciplina**: Métodos de Desenvolvimento de Software (MDS / UnB)
- **Projeto**: Bandejão UnB (`unb-mds/2026-2-Bandejao-UnB`)
- **Grupo**: Grupo 6
- **Contexto**: Compilação e análise das respostas dos formulários de feedback das Sprints (Sprint 0 à Sprint 4), com dados dos 6 integrantes do grupo.

---

## 🏁 Sprint 0 — Nivelamento Técnico e Estudo das Ferramentas Base

### 📊 Respostas dos Integrantes (Formulário Sprint 0/1)

| Membro | O que deu certo? | O que deu errado? | O que podemos melhorar? |
| :--- | :--- | :--- | :--- |
| **Membro 1** | A instalação do ambiente Docker e o entendimento inicial dos comandos básicos rodaram sem grandes problemas. | Dificuldade inicial para compreender a arquitetura de containers em SOs diferentes no grupo. | Criar um script único de setup do ambiente para unificar os comandos do time. |
| **Membro 2** | Boa assimilação dos conceitos do Git e GitHub (commits, branches e pull requests). | Algumas dúvidas conceituais sobre quando utilizar o Gitflow em vez de commits diretos na main. | Definir o fluxo de trabalho no Gitflow logo no primeiro dia de cada sprint. |
| **Membro 3** | Estudo produtivo da sintaxe do Django e compreensão do padrão MVT/MVC. | O tempo estimado para ler a documentação oficial do Django foi insuficiente perante a rotina da semana. | Estabelecer metas diárias e menores de leitura técnica para não sobrecarregar. |
| **Membro 4** | Comparação clara e aprendizado prático sobre os bancos de dados SQLite e MySQL. | Dúvidas sobre qual dos bancos seria o mais indicado para a fase de testes e produção do Bandejão. | Documentar os prós e contras de cada tecnologia antes de fechar a escolha da stack. |
| **Membro 5** | O grupo demonstrou excelente disposição para ajudar quem estava com dificuldades de ambiente. | Desencontros de horários para realizar estudos em conjunto na primeira semana. | Fixar horários semanais para estudos em grupo e alinhamentos rápidos. |
| **Membro 6** | Todas as 6 *issues* de estudo individual da Sprint 0 foram concluídas com sucesso (100% de entrega). | Sentimos falta de um repositório centralizado de anotações dos conteúdos estudados. | Criar uma pasta na Wiki/Documentação para compartilhar resumos dos estudos de cada membro. |

### 📝 Síntese da Sprint 0
- **Pontos Fortes**: Sucesso no nivelamento individual das tecnologias de base (Docker, Git, Django, SQLite, MySQL). Todas as 6 *issues* de estudo foram finalizadas.
- **Gargalos**: Pequenas divergências de configuração de ambiente entre diferentes sistemas operacionais e incertezas sobre o fluxo de branches.
- **Plano de Ação**: Unificar scripts de ambiente via Docker, registrar o fluxo de Gitflow no repositório e compartilhar notas de estudo.

---

## 🚀 Sprint 1 — Aprofundamento Técnico e Documento de Visão

### 📊 Respostas dos Integrantes (Formulário Sprint 0/1)

| Membro | O que deu certo? | O que deu errado? | O que podemos melhorar? |
| :--- | :--- | :--- | :--- |
| **Membro 1** | Consegui evoluir nos estudos de HTML/CSS e na integração de APIs com Django REST Framework. | O tempo de leitura das especificações do Documento de Visão foi mais longo do que o esperado. | Dividir as seções de documentação em tarefas menores por membro no board. |
| **Membro 2** | O alinhamento inicial do grupo foi excelente e fechamos a 1ª versão do Documento de Visão. | Tivemos dúvidas práticas sobre a nomenclatura correta das branches ao abrir Pull Requests. | Criar um guia rápido (*cheatsheet*) com os padrões de mensagens de commit e nomes de branch. |
| **Membro 3** | Compreensão clara da modelagem inicial em SQLite/MySQL e dos scripts em Python de leitura do PDF do cardápio. | Dificuldade em conciliar o tempo de estudo da disciplina com trabalhos de outras matérias. | Organizar sessões de estudo em dupla (*pair learning*) para resolver dúvidas de forma ágil. |
| **Membro 4** | Mapeamento completo dos requisitos do Bandejão e bom entendimento dos scripts leitores do cardápio. | Discussões longas e sem foco definido sobre escolhas técnicas no início das reuniões. | Estabelecer um *timebox* rígido para reuniões de tomada de decisão técnica. |
| **Membro 5** | O aprofundamento em REST APIs e Django REST Framework foi muito esclarecedor para a arquitetura. | Falta de clareza inicial sobre quem revisaria qual seção do Documento de Visão. | Definir revisores de documentação com antecedência no planejamento da sprint. |
| **Membro 6** | Todas as 6 *issues* planejadas foram concluídas e fechadas no GitHub (100% de entrega). | Acompanhamento do andamento individual no meio da semana foi um pouco frouxo. | Adotar checagens assíncronas (*dailies* no Discord/WhatsApp) no meio da sprint. |

### 📝 Síntese da Sprint 1
- **Pontos Fortes**: Finalização bem-sucedida do Documento de Visão e aprofundamento técnico em APIs REST, scripts em Python para leitura de cardápios e banco de dados.
- **Gargalos**: Falta de padronização estrita no Gitflow e reuniões que se estendiam por falta de limites de tempo.
- **Plano de Ação**: Aplicar *timebox* nas reuniões, adotar *dailies* assíncronas e oficializar o guia de commits e Pull Requests.

---

## 🛠️ Sprint 2 — Setup Técnico e Primeiros Esqueletos do Sistema

### 📊 Respostas dos Integrantes (Formulário Sprint 2)

| Membro | O que deu certo? | O que deu errado? | O que podemos melhorar? |
| :--- | :--- | :--- | :--- |
| **Membro 1** | O setup do ambiente Django e a criação do esqueleto das rotas de autenticação (`/cadastro` e `/login`) fluíram bem. | A integração do banco de dados local com o container Docker apresentou conflitos de ambiente. | Padronizar o arquivo `.env` e os scripts de inicialização no Docker para todos do grupo. |
| **Membro 2** | Conclusão do setup do Frontend e criação das telas *placeholder* de Home e Cardápio. | A modelagem da tabela de Avaliações ficou dependente de revisão e a PR demorou para ser aprovada. | Agilizar as revisões de PR no GitHub definindo revisores fixos por área. |
| **Membro 3** | Estruturação e criação do schema inicial no SGBD (tabelas `Usuario` e `Cardapio/Prato`). | Pequenos desalinhamentos entre os nomes das rotas do Backend e os endpoints esperados pelo Frontend. | Documentar o contrato de API (endpoints, payloads e status HTTP) antes da implementação. |
| **Membro 4** | Boa cooperação técnica entre backend e banco durante a modelagem das tabelas do sistema. | Algumas *issues* ficaram sem estimativa precisa de esforço, acumulando trabalho no fim da sprint. | Estipular melhor a complexidade das tarefas durante a reunião de planejamento. |
| **Membro 5** | Telas *placeholder* ficaram visualmente agradáveis e o fluxo inicial atende à proposta do Bandejão. | Ausência de testes unitários automatizados para garantir a estabilidade do setup. | Incluir a escrita de testes simples como critério de aceitação nas *issues* técnicas. |
| **Membro 6** | Todas as 6 *issues* de setup e esqueletos foram finalizadas, permitindo a integração dos módulos. | O processo de *merge* no GitHub gerou conflitos de branches que tomaram tempo excessivo. | Fazer *pull* constante da branch principal antes de abrir novas branches de funcionalidade. |

### 📝 Síntese da Sprint 2
- **Pontos Fortes**: Transição bem-sucedida da fase de estudos para a prática. Os três pilares do projeto (Backend Django REST, Frontend e Banco de Dados) foram configurados e integrados com esqueletos funcionais.
- **Gargalos**: Demora na revisão de Pull Requests e falta de formalização prévia dos contratos de API.
- **Plano de Ação**: Atribuir revisores dedicados por área, padronizar configurações Docker e definir contratos de API antes da codificação.

---

## 📐 Sprint 3 — Estudo e Preparação para Arquitetura de Software (C4 Model)

### 📊 Respostas dos Integrantes (Formulário Sprint 3)

| Membro | O que deu certo? | O que deu errado? | O que podemos melhorar? |
| :--- | :--- | :--- | :--- |
| **Membro 1** | O estudo do C4 Model ajudou a entender como abstrair a arquitetura em diferentes níveis de detalhe. | A sprint ficou com um escopo muito genérico e poucas tarefas práticas registradas no GitHub. | Manter um equilíbrio entre *issues* de documentação e *issues* de desenvolvimento em cada sprint. |
| **Membro 2** | Boa compreensão conceitual dos diagramas de Contexto (Nível 1) e Contêineres (Nível 2). | Indefinição sobre qual ferramenta utilizar para desenhar os diagramas (Excalidraw vs Structurizr vs PlantUML). | Definir previamente a ferramenta oficial de diagramação do grupo antes do início da sprint. |
| **Membro 3** | Alinhamento teórico consistente entre todo o grupo em relação à arquitetura do sistema Bandejão UnB. | Algumas conversas sobre a modelagem detalhada dos componentes se estenderam sem fechar decisões. | Nomear um facilitador técnico a cada sprint para desempatar decisões de arquitetura. |
| **Membro 4** | Mapeamento dos pontos críticos de integração entre os scripts em Python de leitura do PDF do cardápio e a API. | O ritmo de trabalho reduziu em comparação às sprints de setup prático. | Quebrar tarefas teóricas de estudo em entregáveis práticos e rascunhos de diagramas. |
| **Membro 5** | Boa participação da equipe na discussão sobre a visão sistêmica e os limites do software. | Pouca quantidade de *issues* detalhadas e divididas no board do repositório. | Detalhar melhor o backlog de *issues* da sprint seguinte durante o planejamento. |
| **Membro 6** | Entendimento claro do valor da documentação arquitetural para guiar o desenvolvimento do MVP. | Sentimento de que o foco exclusivo em estudo teórico gerou acúmulo para as entregas seguintes. | Planejar a Sprint 4 com metas divididas entre documentação arquitetural e implantação do Frontend. |

### 📝 Síntese da Sprint 3
- **Pontos Fortes**: Consolidação dos conhecimentos teóricos sobre Arquitetura de Software e padrão C4 Model, fornecendo embasamento técnico sólido para o grupo.
- **Gargalos**: Concentração do escopo apenas em estudos teóricos, resultando em poucas *issues* no board e lentidão nas tomadas de decisão sobre ferramentas de diagramação.
- **Plano de Ação**: Retomar o equilíbrio entre código e documentação e pré-selecionar ferramentas antes do início de tarefas de modelagem.

---

## 📄 Sprint 4 — Documentação da Arquitetura (C4 Model) e Implantação Frontend

### 📊 Respostas dos Integrantes (Formulário Sprint 4)

| Membro | O que deu certo? | O que deu errado? | O que podemos melhorar? |
| :--- | :--- | :--- | :--- |
| **Membro 1** | A documentação de arquitetura no padrão C4 Model foi concluída com sucesso e alto padrão técnico. | A documentação acabou tomando muito mais tempo do que tínhamos planejado originalmente. | Aprimorar a estipulação de quanto tempo demora cada *issue*, evitando subestimar tarefas de documentação. |
| **Membro 2** | Apesar do pouco tempo restante, conseguimos nos mobilizar e entregar todas as prioridades do Frontend. | A implantação e integração do Frontend ficou com um prazo extremamente reduzido e apertado no final. | Melhorar a organização e o planejamento das sprints, distribuindo melhor as entregas ao longo do tempo. |
| **Membro 3** | Os diagramas de Componentes e Código deixaram o fluxo do sistema totalmente claro para a equipe. | A correria no final da sprint para concluir a implantação do Frontend causou desgaste no time. | Fazer estimativas de tempo/esforço mais realistas nas reuniões de planejamento. |
| **Membro 4** | A cooperação e o foco do grupo permitiram salvar a entrega das funcionalidades prioritárias do MVP. | Houve gargalo na transição da documentação para o código do Frontend por falta de paralelização. | Dividir o time em duplas em paralelo: enquanto parte finaliza os documentos, outra avança no Frontend. |
| **Membro 5** | A qualidade da documentação foi excelente e serve como guia seguro para as próximas fases do projeto. | Restou pouca margem de tempo para testar e refinar a interface visual e a usabilidade do Frontend. | Reservar dias de *buffer* no final da sprint para testes, ajustes e refinamento de interface. |
| **Membro 6** | Atingimos o objetivo principal e fechamos a documentação arquitetural completa do Bandejão UnB. | A subestimativa do tempo necessário para o C4 Model desbalanceou a carga de trabalho do time. | Refinar a quebra de *issues* no planejamento, tornando as tarefas menores e mais gerenciáveis. |

### 📝 Síntese da Sprint 4
- **Pontos Fortes**: A documentação arquitetural no padrão C4 Model foi concluída com elevado nível de detalhamento e clareza. Mesmo diante da restrição de tempo decorrente do atraso na documentação, a equipe atuou com grande sinergia e capacidade de execução, garantindo a entrega de todas as prioridades estipuladas para a implantação do Frontend.
- **Gargalos**: A elaboração dos diagramas e documentos de arquitetura consumiu substancialmente mais tempo do que o estimado, comprimindo a janela reservada para o desenvolvimento do Frontend e gerando uma sobrecarga na reta final.
- **Principais Ações de Melhoria**:
  1. **Estimativa Realista de Prazos**: Aperfeiçoar a estipulação do tempo e complexidade necessários para cada *issue*.
  2. **Organização e Paralelismo**: Melhorar a organização geral das sprints e paralelizar tarefas de documentação e desenvolvimento, evitando gargalos em cascata.
