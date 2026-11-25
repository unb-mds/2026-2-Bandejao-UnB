# Review e Retrospectiva das Sprints — Projeto Bandejão UnB (MDS)

## 📌 Visão Geral do Projeto
- **Disciplina**: Métodos de Desenvolvimento de Software (MDS / UnB)
- **Projeto**: Bandejão UnB (`unb-mds/2026-2-Bandejao-UnB`)
- **Grupo**: Grupo 6
- **Contexto**: Compilação das retrospectivas das Sprints 0 a 4 e análise documental das Sprints 5 a 12. A Sprint 13 está em andamento e não integra esta avaliação.
- **Metodologia**: As tabelas originais foram preservadas. Nas Sprints 5 a 12, as perspectivas dos seis membros são propostas de feedback para validação, elaboradas a partir das atas e do histórico de tarefas, não respostas individuais coletadas. O encerramento de uma sprint não implica a conclusão de todas as suas issues.

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

---

## Sprint 5 — Feedback da Release 1 e coerência da arquitetura

### Contexto e evidências

A reunião discutiu o retorno da professora e dos monitores, alternativas de check-in e a adoção de ranking para incentivar participação. As issues #58 a #62 organizaram a revisão de coerência entre visão, requisitos, ADRs e C4.

- **Fontes**: Ata da Reunião 5 (01/10/2026); [issues da Sprint 5](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues?q=is%3Aissue+%22Sprint+5%22).

### 📊 Perspectivas dos integrantes (propostas para validação)

| Membro | O que deu certo? | O que deu errado ou merece atenção? | O que podemos melhorar? |
| :--- | :--- | :--- | :--- |
| **Membro 1** | A revisão da visão e do frontend deu direção aos ajustes. | Conciliar revisão e planejamento da próxima entrega. | Definir prazos intermediários para cada documento. |
| **Membro 2** | O ranking trouxe uma direção para a experiência do usuário. | Ainda havia dúvidas sobre como incentivar check-ins. | Esboçar fluxos antes de detalhar a interface. |
| **Membro 3** | As ADRs e requisitos ganharam uma frente própria de revisão. | Mudanças de regras podem afetar várias áreas. | Registrar dependências no backlog. |
| **Membro 4** | A revisão dos diagramas do backend ajudou a identificar inconsistências. | Conferir vários níveis do C4 demanda tempo. | Revisar por módulo. |
| **Membro 5** | A coerência do C4 do banco recebeu atenção específica. | Alterações de requisitos podem exigir retrabalho. | Validar entidades com o backend. |
| **Membro 6** | A divisão da revisão por área foi clara. | O tempo de conferência cruzada é difícil de estimar. | Reservar uma janela para revisão conjunta. |

### 📝 Síntese da Sprint 5
- **Pontos Fortes**: A divisão por documentos e áreas facilitou a revisão.
- **Gargalos**: O volume de correções após a release disputou tempo com a evolução do produto.
- **Plano de Ação**: Priorizar inconsistências que bloqueiam a implementação e revisar documentos em paralelo.

---

## Sprint 6 — Atualização dos requisitos e decisões da Release 2

### Contexto e evidências

A ata registra discussão sobre documentos ainda desatualizados e ideias de gamificação. As issues #63 e #64 trataram das ADRs de detecção de campus e espera estimada, além de visão, requisitos e glossário.

- **Fontes**: Ata da Reunião 6 (06/10/2026); [issues da Sprint 6](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues?q=is%3Aissue+%22Sprint+6%22).

### 📊 Perspectivas dos integrantes (propostas para validação)

| Membro | O que deu certo? | O que deu errado ou merece atenção? | O que podemos melhorar? |
| :--- | :--- | :--- | :--- |
| **Membro 1** | A atualização da visão ajuda a orientar as telas. | Mudanças de fluxo exigem revisar protótipos. | Validar primeiro o fluxo principal. |
| **Membro 2** | A detecção de campus tem potencial para simplificar a navegação. | É necessário considerar a recusa de localização. | Desenhar também o caminho manual. |
| **Membro 3** | As ADRs permitem explicitar decisões da fila. | A estimativa de espera exige regras claras. | Separar decisões indispensáveis de melhorias futuras. |
| **Membro 4** | O glossário ajuda a uniformizar os conceitos. | Revisar documentos interdependentes toma tempo. | Conferir termos junto aos contratos. |
| **Membro 5** | As regras de fila orientam a modelagem. | Ainda há impacto a avaliar sobre os dados coletados. | Mapear dados necessários por requisito. |
| **Membro 6** | A revisão de requisitos facilita identificar dependências. | Mudanças sucessivas dificultam estimar esforço. | Definir uma versão de referência para implementação. |

### 📝 Síntese da Sprint 6
- **Pontos Fortes**: As tarefas de atualização ficaram concentradas em objetivos definidos.
- **Gargalos**: O refinamento das regras consumiu tempo que também seria necessário para implementar.
- **Plano de Ação**: Fechar decisões essenciais antes de expandir o escopo.

---

## Sprint 7 — Simplificação dos requisitos e critérios de aceite

### Contexto e evidências

A equipe decidiu enxugar requisitos funcionais e critérios de aceite em resposta às orientações da Release 1. A issue #65 concentrou essa atividade; a ata atribuiu a publicação das mudanças a Alana.

- **Fontes**: Ata da Reunião 7 (13/10/2026); [issues da Sprint 7](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues?q=is%3Aissue+%22Sprint+7%22).

### 📊 Perspectivas dos integrantes (propostas para validação)

| Membro | O que deu certo? | O que deu errado ou merece atenção? | O que podemos melhorar? |
| :--- | :--- | :--- | :--- |
| **Membro 1** | A simplificação tornou o backlog mais fácil de consultar. | A consolidação e publicação demandam tempo. | Dividir a revisão antes da publicação. |
| **Membro 2** | Critérios mais diretos facilitam verificar as telas. | Resumir sem perder estados de interface é trabalhoso. | Conferir fluxos alternativos. |
| **Membro 3** | O refinamento ajuda a delimitar o escopo. | É preciso evitar retirar regras essenciais. | Validar cada requisito com seus critérios. |
| **Membro 4** | Critérios objetivos ajudam a escrever testes. | Ambiguidades podem gerar interpretações diferentes. | Usar exemplos verificáveis. |
| **Membro 5** | Requisitos mais claros facilitam conferir a modelagem. | Regras de integridade não devem desaparecer na simplificação. | Manter referências à arquitetura. |
| **Membro 6** | A redução de redundâncias melhora a leitura. | Conferir rastreabilidade exige esforço adicional. | Revisar os vínculos entre requisitos e dados. |

### 📝 Síntese da Sprint 7
- **Pontos Fortes**: O foco em critérios mais objetivos favoreceu a rastreabilidade e os testes.
- **Gargalos**: A revisão textual exigiu cuidado para não perder regras importantes.
- **Plano de Ação**: Revisar critérios com representantes das três áreas e preservar os cenários essenciais.

---

## Sprint 8 — Arquitetura da Release 2 e gamificação

### Contexto e evidências

A ata orientou cada área a adequar sua arquitetura aos requisitos após a inserção da gamificação. As issues #66 a #80 cobriram decisões arquiteturais, ranking semestral, Bandeja de Ouro, fila, privacidade, stores e contrato entre frontend e backend.

- **Fontes**: Ata da Reunião 8 (20/10/2026); [issues da Sprint 8](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues?q=is%3Aissue+%22Sprint+8%22).

### 📊 Perspectivas dos integrantes (propostas para validação)

| Membro | O que deu certo? | O que deu errado ou merece atenção? | O que podemos melhorar? |
| :--- | :--- | :--- | :--- |
| **Membro 1** | A rastreabilidade do frontend ganhou tarefas específicas. | Sincronizar telas e requisitos exige várias conferências. | Revisar por fluxo de usuário. |
| **Membro 2** | As telas de gamificação ficaram previstas na arquitetura. | Estados de sessão e campus aumentam a complexidade. | Definir estados antes de codificar. |
| **Membro 3** | O contrato entre áreas foi tratado explicitamente. | A gamificação afeta múltiplos módulos. | Fechar contratos prioritários primeiro. |
| **Membro 4** | Os C4 da fila e avaliação receberam revisão direcionada. | A mudança de regras pode exigir ajustes em cadeia. | Revisar módulos dependentes juntos. |
| **Membro 5** | A modelagem passou a considerar ranking e pontuação. | Conciliar os diagramas com as novas regras leva tempo. | Validar invariantes com o backend. |
| **Membro 6** | Privacidade e fila receberam tarefas próprias. | Há risco de divergência entre diagramas. | Conferir o dicionário de dados a cada mudança. |

### 📝 Síntese da Sprint 8
- **Pontos Fortes**: A decomposição por níveis e áreas permitiu distribuir uma mudança transversal.
- **Gargalos**: A quantidade de documentos dependentes ampliou o esforço de sincronização.
- **Plano de Ação**: Estabelecer pontos de integração e limitar o tempo dedicado a revisões repetidas.

---

## Sprint 9 — Implementação inicial e infraestrutura

### Contexto e evidências

A reunião registrou prazo mais apertado após os ajustes documentais e decidiu priorizar os requisitos mínimos do briefing. O backlog incluiu autenticação, campi, OpenAPI, CI, models, migrations, MySQL e deploy na Azure.

- **Fontes**: Ata da Reunião 9 (27/10/2026); [issues da Sprint 9](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues?q=is%3Aissue+%22Sprint+9%22).

### 📊 Perspectivas dos integrantes (propostas para validação)

| Membro | O que deu certo? | O que deu errado ou merece atenção? | O que podemos melhorar? |
| :--- | :--- | :--- | :--- |
| **Membro 1** | A continuidade do MVP e do apiClient organizou a integração. | Dependências de autenticação podem reduzir o tempo de testes. | Combinar contratos e marcos de integração. |
| **Membro 2** | As telas de cadastro e login tiveram objetivos definidos. | É preciso tratar estados de erro e localização. | Testar fluxos com mocks enquanto a API evolui. |
| **Membro 3** | O contrato OpenAPI orientou a implementação. | Cadastro e sessão exigem validações cuidadosas. | Revisar endpoints em pequenas PRs. |
| **Membro 4** | O CI do backend e o leitor de PDF tiveram tarefas próprias. | A validação de formatos pode consumir tempo. | Testar casos representativos cedo. |
| **Membro 5** | Models e migrations foram organizados conforme o C4. | A integração com MySQL exige conferências. | Executar testes de banco desde o início. |
| **Membro 6** | O deploy e as fixtures tiveram planejamento específico. | Configurar ambientes pode bloquear outras áreas. | Documentar configuração e validar o ambiente antecipadamente. |

### 📝 Síntese da Sprint 9
- **Pontos Fortes**: A divisão entre frontend, backend e banco permitiu avançar em frentes complementares.
- **Gargalos**: O tempo disponível para integração diminuiu após a fase documental.
- **Plano de Ação**: Priorizar o caminho crítico e integrar incrementos pequenos.

---

## Sprint 10 — Integração do cardápio, fila e avaliações

### Contexto e evidências

A reunião registrou mudanças no backlog devido ao prazo e acompanhamento das dificuldades. As issues da sprint incluíram check-in, leitor de PDF, cardápio, avaliação, CampusView, integração com API, cron e deploy M2.

- **Fontes**: Ata da Reunião 10 (data conforme identificação da ata); [issues da Sprint 10](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues?q=is%3Aissue+%22Sprint+10%22).

### 📊 Perspectivas dos integrantes (propostas para validação)

| Membro | O que deu certo? | O que deu errado ou merece atenção? | O que podemos melhorar? |
| :--- | :--- | :--- | :--- |
| **Membro 1** | A integração da tela de campus organizou os fluxos. | A dependência de endpoints pode atrasar testes. | Combinar entregas intermediárias com backend. |
| **Membro 2** | Cardápio e avaliações tiveram tarefas delimitadas. | Estados de carregamento e erro exigem tempo adicional. | Testar estados com dados controlados. |
| **Membro 3** | Check-in e avaliação foram tratados como entregas próprias. | Mudanças de backlog exigem reavaliar prioridades. | Proteger o fluxo mínimo do usuário. |
| **Membro 4** | O leitor de PDF e a API de cardápio têm responsabilidades distintas. | Formatos de origem podem exigir ajustes. | Testar exemplos reais e falhas. |
| **Membro 5** | Índices e origem do cardápio receberam atenção. | A integração exige conferir consistência dos dados. | Validar consultas com casos de uso reais. |
| **Membro 6** | Cron e deploy foram previstos no backlog. | A publicação depende de várias áreas. | Planejar uma janela conjunta de integração. |

### 📝 Síntese da Sprint 10
- **Pontos Fortes**: O backlog agrupou funcionalidades que compõem o fluxo principal do RU.
- **Gargalos**: A integração entre módulos e a redução do prazo exigiram repriorização.
- **Plano de Ação**: Validar o fluxo completo em incrementos e registrar bloqueios assim que surgirem.

---

## Sprint 11 — Gamificação, previsão e responsividade

### Contexto e evidências

A reunião acompanhou o andamento da implementação e orientou sua continuidade. O backlog incluiu pontuação, progresso, previsão da fila, RankingView, layout responsivo, retenção e exclusão de conta.

- **Fontes**: Ata da Reunião 11 (data conforme identificação da ata); [issues da Sprint 11](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues?q=is%3Aissue+%22Sprint+11%22).

### 📊 Perspectivas dos integrantes (propostas para validação)

| Membro | O que deu certo? | O que deu errado ou merece atenção? | O que podemos melhorar? |
| :--- | :--- | :--- | :--- |
| **Membro 1** | O layout responsivo recebeu uma tarefa dedicada. | Ajustar desktop e celular exige verificações distintas. | Reservar tempo para conferência visual. |
| **Membro 2** | As telas de progresso e ranking tiveram escopo definido. | Estados sem dados precisam de atenção. | Testar cenários vazios e de erro. |
| **Membro 3** | Pontuação e adesão ao ranking foram separadas no backlog. | As regras precisam permanecer consistentes entre endpoints. | Validar cenários de pontuação. |
| **Membro 4** | A previsão da fila teve uma frente própria. | A qualidade dos dados pode afetar a previsão. | Testar ausência e insuficiência de dados. |
| **Membro 5** | A retenção de quatro semanas foi tratada explicitamente. | A remoção de dados exige verificar dependências. | Testar limites temporais. |
| **Membro 6** | A exclusão de conta recebeu uma tarefa específica. | A integridade das relações demanda revisão. | Conferir efeitos da exclusão com o backend. |

### 📝 Síntese da Sprint 11
- **Pontos Fortes**: A divisão por funcionalidades permitiu evoluir experiência e regras de negócio em paralelo.
- **Gargalos**: O número de integrações e verificações aumentou em uma fase de prazo reduzido.
- **Plano de Ação**: Conferir contratos e fluxos responsivos antes de acumular ajustes finais.

---

## Sprint 12 — Qualidade, ajustes finais e preparação da entrega

### Contexto e evidências

A ata registrou a necessidade de acelerar a implementação para liberar tempo para polimento documental, com meta de conclusão até o dia 21. O backlog incluiu ranking, login institucional, PWA, Playwright, mutação, carga, responsividade, design e qualidade. As issues #265 e #297 e os PRs #301 e #302 exemplificam ajustes de navegação e interface ainda em revisão no período.

- **Fontes**: Ata da Reunião 12 (data conforme identificação da ata); [issues da Sprint 12](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues?q=is%3Aissue+%22Sprint+12%22).

### 📊 Perspectivas dos integrantes (propostas para validação)

| Membro | O que deu certo? | O que deu errado ou merece atenção? | O que podemos melhorar? |
| :--- | :--- | :--- | :--- |
| **Membro 1** | Os ajustes de navegação e fila tiveram tarefas específicas. | Revisões e conflitos podem prolongar o fechamento. | Abrir PRs menores e revisar cedo. |
| **Membro 2** | Design e responsividade ganharam atenção no backlog. | Conferir diferentes tamanhos de tela demanda tempo. | Usar checklist visual por resolução. |
| **Membro 3** | O login institucional e o ranking tiveram escopo definido. | A estabilização do contrato concorre com novas demandas. | Priorizar correções que bloqueiam a entrega. |
| **Membro 4** | Testes de mutação e portas finais foram previstos. | Executar e analisar testes exige margem de tempo. | Separar falhas críticas de melhorias posteriores. |
| **Membro 5** | O teste de carga foi incluído no planejamento. | A validação depende de ambiente e dados representativos. | Preparar cenários antes da execução. |
| **Membro 6** | A publicação da versão responsiva foi prevista. | Deploy e regressão precisam de coordenação. | Reservar janela para publicação e verificação. |

### 📝 Síntese da Sprint 12
- **Pontos Fortes**: A equipe organizou tarefas de qualidade e acabamento por área.
- **Gargalos**: A proximidade da entrega reduziu a margem para revisões, conflitos e validações visuais.
- **Plano de Ação**: Encerrar funcionalidades prioritárias cedo e reservar tempo explícito para regressão e documentação.

---

## Avaliação geral das Sprints 0 a 12

O planejamento e a divisão das atividades foram, de modo geral, adequados. A separação entre frontend, backend e banco de dados, definida na Sprint 0, favoreceu a distribuição de responsabilidades. O principal problema foi o gerenciamento do tempo para executar o planejamento: o esforço dedicado à documentação e às revisões de arquitetura reduziu a margem para implementação, integração e testes. A ata da Sprint 9 registra expressamente essa pressão, e a da Sprint 12 reforça a necessidade de liberar tempo para o polimento documental.

A comunicação também merece atenção: a ata da Sprint 2 registra demora na sinalização de dificuldades e estabelece início das sprints às segundas e conclusão das issues aos sábados. A melhoria proposta é acompanhar a execução durante a semana, não apenas reorganizar o backlog ao final dela.

### Plano de melhoria geral

| Ação proposta | Responsável sugerido | Critério de acompanhamento |
| :--- | :--- | :--- |
| Estimar esforço conforme disponibilidade real | Todos | Conferir capacidade antes de assumir issues |
| Acompanhar progresso e bloqueios no meio da semana | Scrum Master e equipe | Atualizar o board e sinalizar impedimentos |
| Priorizar dependências e requisitos mínimos | Product Owner e equipe | Identificar caminho crítico no planning |
| Abrir PRs menores e antecipar revisões | Todos | Evitar concentração de revisões no último dia |
| Reservar tempo para testes, integração e documentação | Todas as áreas | Prever margem explícita antes do fechamento |

### Referências e limites do registro

- Atas semanais 0 a 12 e ata complementar de preenchimento do Figma, fornecidas para esta atualização. A ata complementar registra que o story map ficou em aberto devido ao tempo.
- [Issues do projeto](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues) e [histórico de commits](https://github.com/unb-mds/2026-2-Bandejao-UnB/commits/develop/).
- [PR #301](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/301) e [PR #302](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/302): referências de trabalho de navegação e fila; não equivalem a confirmação de aceite final.
- As atas 10, 11 e 12 apresentam datas de outubro incompatíveis com a sequência das atas 8 e 9. Foi utilizada a numeração explícita das sprints, sem corrigir datas por suposição. A ata 6 contém informações divergentes sobre a presença do PO; não foi atribuída fala individual com base nela.
- As issues descrevem escopo planejado; não foi possível confirmar individualmente o estado de fechamento de todas elas nem associar cada commit a uma sprint. As perspectivas novas são sugestões de retrospectiva, não transcrições nem comprovação de presença em reuniões.
