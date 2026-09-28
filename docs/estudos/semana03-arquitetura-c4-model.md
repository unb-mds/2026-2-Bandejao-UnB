# C4 Model

**Integrante:** Alana
**Semana:** 03
**Data:** 2026-09-20
**Tags:** arquitetura, c4-model, diagramas, documentação, mermaid

## Resumo

O C4 Model é uma abordagem para modelar arquiteturas de software, organizada em quatro níveis de abstração, cada um oferecendo uma visão única do sistema. Não é necessário usar todos os níveis — apenas aqueles que agregam valor à documentação. Os quatro níveis, do mais abstrato ao mais detalhado, são: **Contexto** (visão panorâmica do sistema, seus usuários e sistemas externos), **Contêiner** (aplicações, bancos de dados e serviços que compõem o sistema, e como interagem), **Componente** (detalhes internos de um contêiner, seus componentes e responsabilidades) e **Código** (detalhes de implementação, como diagramas de classe e sequência — recomendado só para partes mais importantes ou complexas).

## Aplicação no projeto

O C4 Model vai ser usado para documentar a arquitetura do sistema do Bandejão. O grupo pretende usar Mermaid para gerar os diagramas, através de uma skill do Claude voltada para isso.

## Principais conceitos / como usar

- **Nível 1 — Contexto**: o sistema aparece como uma caixa central, ligada aos usuários e a outros sistemas com os quais interage. Foco em pessoas e sistemas externos, sem entrar em detalhes internos.
- **Nível 2 — Contêiner**: mostra a forma de alto nível da arquitetura, como as responsabilidades são distribuídas e as principais escolhas de tecnologia. Um contêiner é qualquer coisa que roda código ou armazena dados. Pergunta-chave: "se eu executar o sistema, isso aqui está rodando ou armazenando dados?"
- **Nível 3 — Componente**: identifica os componentes individuais dentro de um contêiner, suas responsabilidades, tecnologia e como interagem entre si.
- **Nível 4 — Código**: nível de maior detalhe (diagramas de classe, sequência etc.), recomendado apenas para os componentes mais importantes ou complexos.
- **Diagramas complementares** (usados só quando agregam valor): System Landscape (relação entre vários sistemas), Dynamic (colaboração entre elementos em um cenário específico) e Deployment (mapeamento do software para infraestrutura/ambiente de execução).
- **Ferramentas**: Structurizr (DSL textual dedicado ao C4, com exportação para Mermaid), Mermaid (diagramas em texto, versionáveis junto ao código) e draw.io (ferramenta visual manual).

## Fontes / materiais usados

- Entendendo o C4 Model: uma abordagem para arquitetura de software (Medium) — https://medium.com/cajudevs/entendendo-o-c4-model-uma-abordagem-para-arquitetura-de-software-3ed0f007ae66
- C4 Model — Diagramas oficiais — https://c4model.com/diagrams
- Structurizr DSL — documentação oficial — https://docs.structurizr.com/dsl
