# Gitflow

**Integrante:** Alana
**Semana:** 00
**Data:** 2026-08-30
**Tags:** git, gitflow, branching, versionamento, workflow

## Resumo

O Gitflow é um modelo alternativo de branching no Git, que define papéis específicos para diferentes branches e regras claras de quando e como elas interagem. O fluxo usa duas branches principais: `main`, que guarda a versão final de cada release do software, e `develop`, que funciona como branch de integração armazenando o histórico completo do desenvolvimento. Além dessas, existem branches auxiliares: *feature branches* (uma por funcionalidade, nascem e se integram de volta à `develop`), *release branches* (criadas a partir da `develop` quando o software está pronto para lançamento, usadas só para ajustes finais) e *hotfix branches* (baseadas direto na `main`, para corrigir bugs urgentes em produção).

## Aplicação no projeto

Há a pretensão de adotar o Gitflow como fluxo de branches no repositório do projeto Bandejão (RU-UnB), organizando o trabalho do grupo (6 pessoas, 2 por área: backend, frontend, database). A ideia é que a `develop` concentre a integração contínua das features de cada área (cardápio, avaliação, fila, previsão de pico), enquanto a `main` só receba código já validado e pronto para "lançamento" de cada release da Scrum (sprints semanais). Branches de hotfix ficam reservadas para bugs críticos identificados após alguma entrega já estar em uso.

## Principais conceitos / como usar

- **Feature branches**: partem da `develop`, nunca interagem direto com a `main`; ao terminar a implementação, fazem merge de volta pra `develop`.
- **Release branches**: criadas a partir da `develop` quando há funcionalidades suficientes ou a data da release se aproxima; a partir daí só se aceita correção de bugs, documentação e tarefas de preparação — nenhuma feature nova. Ao ficar pronta, faz merge com a `main` (marcando o número da versão) e também com a `develop`, e depois é excluída.
- **Hotfix branches**: únicas baseadas direto na `main`; usadas para bugs urgentes em produção; ao resolver, merge na `main` (atualizando versão) e na `develop`.
- Vantagem: permite que parte do time foque em polir a release enquanto outra parte já avança nas próximas funcionalidades.

## Fontes / materiais usados

- Atlassian Git Tutorial — Comparing Workflows: Gitflow Workflow (https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow)
