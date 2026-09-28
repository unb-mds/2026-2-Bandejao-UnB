# Django

**Integrante:** Cristiano
**Semana:** 0
**Data:** 2026-09-08
**Tags:** backend, python, framework, api

## Resumo

Django é um framework web escrito em Python — uma espécie de caixa de ferramentas com estruturas prontas (conexão com banco de dados, sistema de usuários, roteamento de URLs, entre outras) que o desenvolvedor só precisa encaixar, em vez de programar do zero. Ele é conhecido por já vir com proteções de segurança padrão contra ataques comuns, e por ser usado por grandes plataformas, como o Instagram. Por ser baseado em Python — uma linguagem considerada simples e legível — também costuma ser mais acessível para quem está começando.

## Aplicação no projeto

O Django funciona como o backend central do projeto, servindo mais de uma funcionalidade do site: ele processa e armazena os dados extraídos dos PDFs de cardápio do RU (a extração em si é feita por uma biblioteca Python auxiliar; o Django entra guardando o resultado já tratado em um model e expondo esse cardápio para o frontend consumir) e também é responsável por calcular a média ponderada dos horários de pico, usada na previsão de pico de movimento do RU.

## Principais conceitos / como usar

- **Estrutura do projeto:** um projeto Django é dividido em vários *apps*, cada um responsável por uma parte específica da funcionalidade (ex: um app pra fila, um pra cardápio) — isso facilita manutenção e reduz o risco de um problema afetar o sistema inteiro. O `settings.py` concentra as configurações gerais do projeto (banco de dados, apps ativos, segurança); o `urls.py` direciona cada endereço acessado para a view correta.
- **Models e migrations:** um *model* descreve, em Python, os dados que o sistema guarda (ex: um `Relato` de fila). Alterações no model não mudam o banco de dados sozinhas — é preciso rodar `python manage.py makemigrations` (gera um arquivo registrando a mudança, que é commitado no Git) e depois `python manage.py migrate` (aplica de fato a mudança no banco). Essa separação existe tanto para revisar a mudança antes de aplicá-la quanto para manter o banco de dados sincronizado entre todos do grupo.
- **Django Admin:** painel de administração gerado automaticamente pelo framework, que permite visualizar, criar, editar e apagar registros do banco por uma interface visual, sem escrever código — útil para testar e simular dados durante o desenvolvimento (não é destinado ao usuário final do site).
- **Django REST Framework (DRF):** como o frontend do projeto é separado (Vue), o Django sozinho devolveria HTML, que o frontend não consegue aproveitar diretamente. O DRF expõe os dados como JSON puro através de endpoints, usando *serializers* para traduzir os models em JSON.

## Fontes / materiais usados

- Django Crash Course (YouTube, em inglês): https://www.youtube.com/watch?v=0roB7wZMLqI
