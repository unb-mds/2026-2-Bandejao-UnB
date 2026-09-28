# Docker

**Integrante:** Alvaro
**Semana:** 00
**Data:** 2026-08-31
**Tags:** docker, containers, infraestrutura, devops

## Resumo

Docker é um projeto de software livre para automatizar a implantação de aplicações como contêineres portáteis e autossuficientes, que podem rodar tanto na nuvem quanto localmente. A ideia de contêiner se apoia em recursos já existentes do kernel (inicialmente do Linux) para isolar a execução de processos. O Docker permite empacotar a aplicação junto com todas as dependências necessárias para sua execução, e resolve o clássico problema do "na minha máquina funciona": como todas as configurações do ambiente ficam salvas dentro do contêiner, ele roda da mesma forma em qualquer ambiente onde for executado.

## Aplicação no projeto

O Docker se aplica principalmente à infraestrutura do projeto, mas beneficia todas as frentes (fila, cardápio, previsão de pico) indiretamente:

- **Elimina o "na minha máquina funciona":** cada integrante do grupo pode ter SO, versão de Node/Python e configurações diferentes. Com Docker, todo mundo roda o mesmo ambiente (mesma versão de linguagem, mesmas libs), evitando que bugs de ambiente virem horas de debug.
- **Orquestra os serviços com um comando:** com `docker-compose`, back-end, banco de dados e outros serviços (cache, fila de mensagens) sobem juntos com `docker-compose up`, sem precisar instalar Postgres manualmente na máquina de cada um.
- **Onboarding rápido:** um novo integrante (ou a própria professora, para avaliar o projeto) clona o repositório, roda `docker-compose up` e já tem o sistema completo funcionando.
- **Aproxima dev de produção:** se o deploy for feito num servidor da disciplina, VPS ou serviço cloud, a mesma configuração Docker que roda local é a que sobe em produção, reduzindo surpresas na entrega.
- **CI mais simples:** se o GitHub Actions rodar testes automaticamente a cada commit, é fácil subir um container de banco de dados real para os testes, em vez de mockar tudo.

## Principais conceitos / como usar

- **Container:** unidade padrão de software que empacota código e todas as dependências de uma aplicação, permitindo execução rápida e confiável independente do ambiente computacional. É uma instância de execução de uma imagem — ou seja, o que a imagem se torna quando é executada.

- **Docker Image:** pacote leve, independente e executável que inclui tudo o necessário para rodar um software (código, runtime, bibliotecas, variáveis de ambiente e arquivos de configuração). Imagens são imutáveis: uma vez criadas, não mudam.

- **Dockerfile:** script de texto simples com uma série de comandos que o Docker usa para montar uma imagem. Automatiza o processo de criação de imagens, garantindo que seja repetível e consistente.

- **Docker Hub (Registry):** serviço de registro baseado em nuvem do Docker, que permite compartilhar imagens próprias ou acessar imagens compartilhadas por outros desenvolvedores e organizações. Fornece uma vasta biblioteca de imagens contribuídas pelo próprio Docker e por sua comunidade, facilitando distribuição e controle de versão.

- **Volumes:** forma como o Docker persiste dados fora do container. Por padrão, tudo que acontece dentro de um container é temporário — se o container é apagado, os dados vão junto. Um volume é um espaço de armazenamento gerenciado pelo Docker que fica fora do ciclo de vida do container, garantindo que os dados sobrevivam mesmo se o container for recriado. No projeto do RU, o container do Postgres/MySQL (dados de fila e cardápio) precisa de um volume, senão a cada `docker-compose down` e novo `up` o banco volta zerado.

- **Redes (networks):** como os containers se comunicam entre si. Por padrão o Docker isola cada container — eles não se enxergam automaticamente. Uma rede Docker conecta os containers que precisam conversar, e eles passam a se encontrar pelo nome do serviço, como um DNS interno (sem precisar de `localhost` ou IP fixo). No projeto, o container do back-end "fala" com o do banco usando `db` (nome do serviço) como hostname, em vez de descobrir o IP.

- **Docker Compose:** ferramenta que junta serviços, volumes e redes num único arquivo `docker-compose.yml`, evitando rodar vários `docker run` gigantes com flags separadas. Com um único comando (`docker-compose up`), sobe todo o ambiente — back-end e banco já conectados na mesma rede, com volume garantindo persistência — de forma idêntica para qualquer pessoa do grupo.

## Fontes / materiais usados

- https://www.green.com.br/blog/docker/
- https://www.youtube.com/watch?v=DdoncfOdru8
- https://www.youtube.com/watch?v=ntbpIfS44Gw
- https://www.youtube.com/watch?v=74RfAbJWDHs
