# Arquitetura de Software e C4 Model

**Integrante:** Cristiano
**Semana:** 03
**Data:** 26/09/2026
**Tags:** arquitetura-de-software, c4-model, diagramas

## Resumo

Arquitetura de software é o conjunto de decisões estruturais de um sistema que são caras de mudar depois — como as partes se conectam, não como cada função é escrita por dentro. Projetar uma arquitetura significa responder perguntas sobre quem usa o sistema, quais requisitos não-funcionais importam mais (performance, disponibilidade, escalabilidade) e onde ficam as fronteiras do sistema. O C4 Model, criado por Simon Brown, é uma forma padronizada de documentar essa arquitetura em 4 níveis de zoom progressivo — Context, Container, Component e Code — cada um voltado a um público diferente, do stakeholder não-técnico até o desenvolvedor mexendo em uma classe específica.

## Aplicação no projeto

A modelagem em C4 é uma exigência da professora da disciplina e serve como base formal da arquitetura do RU-UnB. Os diagramas de Context e Container vão registrar oficialmente como o sistema (fila, cardápio, previsão de pico) se conecta com seus usuários e quais peças tecnológicas compõem a solução. O grupo ainda não bateu o martelo nas decisões concretas — por exemplo, se o módulo de previsão de pico será parte do Backend Flask ou um container separado — e o C4 é justamente a ferramenta que vai forçar essas decisões a ficarem explícitas antes da implementação.

## Principais conceitos / como usar

- **Arquitetura = decisões caras de reverter.** Não é "todo o código", é o mapa estrutural de como as partes se conectam.
- **C4 = zoom progressivo**, como um mapa (país → estado → cidade → rua):
  - **Context**: o sistema como uma caixa única, cercado pelos usuários (estudante, nutricionista/admin) e sistemas externos. Sem tecnologia, público geral.
  - **Container**: unidades que rodam separadamente — Frontend, Backend Flask, banco de dados, possível serviço de previsão de pico. Já mostra tecnologia e como as peças conversam (REST, etc.).
  - **Component**: zoom dentro de UM container — ex: módulos de fila, cardápio, previsão e autenticação dentro do Backend Flask.
  - **Code**: nível de classe/UML, geralmente não vale a pena manter manualmente; usado só pontualmente.
- **Notação:** retângulos com nome + tipo, pessoas como bonequinho/caixa arredondada, setas sempre com o verbo da interação escrito (nunca deixar seta sem legenda).
- **Ferramentas práticas pro grupo:** Mermaid.js (renderiza direto no Markdown do GitHub) ou PlantUML com a lib C4-PlantUML; Structurizr é a ferramenta "oficial" do criador do C4, mas com curva de aprendizado maior.
- **Perguntas-guia antes de desenhar:** quem usa o sistema e como, quais requisitos não-funcionais pesam mais (performance, disponibilidade, escala), onde ficam as fronteiras do sistema, e o que é estável vs. o que muda com frequência.

## Fontes / materiais usados

- Vídeo: https://www.youtube.com/watch?v=n0uPRtQ8wuY — explicação sobre arquitetura de software e C4 Model
