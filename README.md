# G6-2026-2
Grupo G6 - Metodos de Desenvolvimento de Software 2026/2

# Bandejão

> PWA que reúne cardápio, avaliações das refeições e previsão de fila dos Restaurantes Universitários (RU) da Universidade de Brasília.

Projeto do **Grupo 6 (G6)** na disciplina **Métodos de Desenvolvimento de Software (MDS)**, do curso de Engenharia de Software da Faculdade de Ciências e Tecnologias em Engenharia (FCTE/UnB), semestre 2026/2, com orientação da Profa. Carla Silva Rocha Aguiar.

---

## Sobre o projeto

O cardápio oficial do RU da UnB é publicado em formato de planilha/PDF, o que dificulta a leitura. Além disso, a lotação do RU não segue um padrão fixo e não existe um canal para os frequentadores darem feedback sobre as refeições. O resultado é tempo perdido em filas, dificuldade de quem tem restrição alimentar ou alergia para saber o que pode comer e falta de previsibilidade para quem tem a agenda apertada.

O **Bandejão** centraliza essas informações em um único lugar:

- cardápio diário e semanal por campus, com apresentação dinâmica e filtros de marcadores alimentares e de dieta;
- avaliações das refeições feitas pelos próprios usuários;
- previsão do horário de pico da fila, calculada a partir dos check-ins da comunidade.

O cardápio pode ser consultado por qualquer pessoa, sem cadastro. A conta, criada com matrícula ou SIAPE/matrícula funcional, é necessária para avaliar refeições e, a partir da Release 2, para fazer check-in.

## Funcionalidades

| Release | Funcionalidades |
|---|---|
| **MVP** | Cadastro e login por matrícula ou SIAPE, com confirmação de e-mail · Recuperação de senha · Consulta ao cardápio sem login · Leitura automatizada do PDF do cardápio · Exibição por campus, refeição e dia · Filtros de marcadores alimentares e de dieta · Avaliação de refeições por estrelas (1 a 5) e comentário · Identidade visual do site |
| **Release 2** | Check-in no RU · Confirmação do check-in por GPS · Previsão de horário de pico em quatro níveis (vazia, curta, moderada e longa) · Histórico de refeições anteriores |
| **Backlog** | Nível da fila em tempo real ("agora") · Ícones de marcadores nos pratos |

## Quem pode usar

| Perfil | Como acessa | O que pode fazer |
|---|---|---|
| **Visitante** | Sem login | Consultar o cardápio e, na Release 2, a previsão de pico |
| **Estudante** | Conta com matrícula | Tudo do visitante, avaliar refeições e, na Release 2, fazer check-in |
| **Professor/Servidor** | Conta com SIAPE/matrícula funcional | Tudo do visitante, avaliar refeições e, na Release 2, fazer check-in |

Terceirizados e demais frequentadores sem matrícula ou SIAPE usam o Bandejão como visitantes.

## Campi atendidos

Darcy Ribeiro, Ceilândia, Gama, Planaltina e Fazenda Água Limpa. O Restaurante Executivo do Campus Darcy Ribeiro está fora do escopo do projeto.

## Documentação

- [Documento de Requisitos](docs/requisitos/documento-de-requisitos-bandejao.md): requisitos funcionais, não funcionais e inversos, com critérios de aceite, limitações e riscos conhecidos e matriz de rastreabilidade.
- [Documento de Visão](docs/requisitos/documento-de-visao-bandejao.md): proposta, partes interessadas, recursos do produto, restrições e priorização por release, no modelo do IBM DOORS Next.
- [Double Diamond](https://www.figma.com/board/acRlPdHQYnCuHXr8dEDaF7/Template-MDS--c%C3%B3pia-limpa---c%C3%B3pia-): board do projeto no Figma com o processo de descoberta e definição.

## Status do projeto

O projeto está em fase inicial. Os Documentos de Visão e de Requisitos estão elaborados e definem o escopo do MVP. Stack, hospedagem e licenciamento ainda estão a definir.

## Equipe

**Grupo 6 — Estudantes de Engenharia de Software (FCTE/UnB)**

- Alana Cristyna Feitosa Dias
- Álvaro Bento Moura da Silva
- Corina Xavier Carneiro
- Cristiano Monteiro Coelho Lacerda Póvoas
- Josué Xavier Carneiro
- Luís Felipe Albuquerque Fernandes

**Orientadora:** Profa. Carla Silva Rocha Aguiar
