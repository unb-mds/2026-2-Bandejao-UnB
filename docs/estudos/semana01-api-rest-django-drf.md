# API REST, Django e Django REST Framework

**Integrante:** Álvaro Bento
**Semana:** 01
**Data:** 05/09/2026
**Tags:** api-rest, django, drf, backend

## Resumo

Uma API é um contrato entre dois sistemas: um conjunto de regras que define como eles trocam informação sem que um precise saber como o outro funciona por dentro. Uma API REST usa o protocolo HTTP para isso — o cliente faz uma requisição a um endereço (endpoint), o verbo HTTP (GET, POST, PUT/PATCH, DELETE) indica a intenção, e o servidor responde com um status code e dados em JSON.

Django é um framework web em Python que resolve as partes repetitivas de qualquer sistema (banco de dados, autenticação, roteamento, segurança), organizado no padrão MTV (Model-Template-View). Por padrão ele é feito para gerar páginas HTML prontas, não para servir uma API.

Django REST Framework (DRF) é uma biblioteca construída em cima do Django que adiciona exatamente as peças que faltam para transformar um projeto Django numa API REST: serializers (que substituem os templates, convertendo models em JSON e vice-versa), views/viewsets (lógica de request/response por verbo HTTP) e routers (geração automática de URLs a partir dos viewsets).

## Aplicação no projeto

No backend do RU, a API é a porta de entrada que o frontend usa para pedir e enviar dados — fila atual, cardápio, previsão de pico — sem precisar saber como isso está guardado no banco ou como foi calculado. Cada um desses conceitos vira um **recurso** REST próprio: `/fila/`, `/cardapio/`, `/previsao/`, cada um com seus endpoints e verbos.

Na prática de setup (testada com um app de exemplo, `Task`, mas que segue o mesmo padrão a ser usado em `Cardapio`, `Fila` etc.):

- **Model**: define a estrutura do dado no banco (ex: campos do cardápio).
- **Serializer**: converte esse model em JSON para o frontend consumir, e valida o JSON recebido antes de gravar.
- **View**: decide o que fazer a cada requisição (buscar fila, calcular previsão de pico, etc.) e devolve a resposta.
- **URL**: conecta um endpoint (`/api/cardapio/`) à view correspondente.

Esse fluxo (Model → Serializer → View → URL) é a base que vai ser replicada para os três recursos principais do projeto. O próximo passo natural (Viewsets + Routers, ver Observações) é o que vai deixar `/api/cardapio/`, `/api/cardapio/1/`, `/api/fila/` com um padrão consistente e fácil de consumir pelo frontend.

## Principais conceitos / como usar

**Fluxo de uma API REST:**
1. Cliente faz uma requisição HTTP para um endpoint (ex: `GET /api/cardapio`).
2. O verbo HTTP indica a intenção: `GET` busca, `POST` cria, `PUT`/`PATCH` atualiza, `DELETE` remove.
3. O servidor (Django) processa: busca/grava no banco, aplica lógica (ex: calcular previsão de pico).
4. O servidor responde com um status code + dados:
   - `200 OK` — deu certo.
   - `201 Created` — criou com sucesso.
   - `404 Not Found` — recurso não encontrado.
   - `400/401/403` — erro do cliente (dado inválido, sem permissão).
   - `500` — erro do servidor.
5. Os dados trafegam em JSON, formato que o DRF serializa a partir dos models Django.

**Padrão MTV do Django:** Model (estrutura dos dados) → Template (HTML mostrado ao usuário) → View (lógica que decide o que retornar). O DRF reaproveita Model e View, mas troca Template por Serializer.

**Setup do ambiente (testado):**
```bash
sudo apt install python3-venv        # necessário no Ubuntu/Debian
python3 -m venv .venv
source .venv/bin/activate
pip install django djangorestframework
```

**Criação do projeto:**
```bash
django-admin startproject tutorial .   # o ponto evita subpasta duplicada
python manage.py startapp snippets
```
Registrar `rest_framework` e o app criado em `INSTALLED_APPS` (`settings.py`), depois rodar `python manage.py migrate`.

**As 4 peças de uma API DRF, na ordem:**

1. Model (`models.py`):
```python
from django.db import models

class Task(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```
```bash
python manage.py makemigrations
python manage.py migrate
```

2. Serializer (`serializers.py`) — `ModelSerializer` gera os campos automaticamente a partir do model, sem precisar declarar campo por campo:
```python
from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'done', 'created_at']
```

3. View (`views.py`) — lógica que responde a cada verbo HTTP:
```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Task
from .serializers import TaskSerializer

@api_view(['GET', 'POST'])
def task_list(request):
    if request.method == 'GET':
        tasks = Task.objects.all()
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
```

4. URL (`urls.py`) — conecta um endereço à view:
```python
from snippets.views import task_list

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/tasks/', task_list),
]
```

**Validação:** testado via `python manage.py shell` (serialização isolada) e depois na Browsable API do DRF (`http://127.0.0.1:8000/api/tasks/`), confirmando GET e POST funcionando de ponta a ponta.

**Conceitos relacionados revisados junto:**
- **DNS**: tradução de nomes de domínio para IP — relevante para o deploy futuro da API.
- **Cache**: guardar o resultado de um cálculo/consulta custoso para evitar refazer o trabalho a cada requisição (ex: usar Redis para a previsão de pico).

**Erros comuns encontrados (vale para o grupo todo):**
- Digitar o código manualmente gera erros sutis de sintaxe (`Task Serializer` com espaço, `serialiter` em vez de `serializer`) — copiar/colar o bloco inteiro evita isso.
- `runserver` ocupa o terminal; comandos como `makemigrations` precisam ser rodados em outra aba ou depois de `Ctrl+C`.
- Acessar `/` em vez de `/api/tasks/` retorna 404 depois que `urls.py` é reescrito, pois a rota raiz padrão do Django deixa de existir.

## Fontes / materiais usados

- Documentação oficial do DRF — django-rest-framework.org/tutorial, Parte 1 (Serialization) e Partes 2 a 6 (Class-based Views, Generic Views, Authentication e Permissions, Relationships e Hyperlinked APIs, Viewsets e Routers).
- MDN Web Docs (conceitos gerais de API).
- freeCodeCamp — "What is an API".
- Repositório oficial de exemplo: `encode/rest-framework-tutorial` (GitHub).

## Observações / próximos passos

Próximos tópicos do tutorial oficial do DRF, em ordem de prioridade para o projeto:

1. **Class-based Views e Generic Views** (Partes 2 e 3) — reescreve a lógica de função (`@api_view`) como classe, reduzindo código repetido de CRUD. Base para o próximo item.
2. **Viewsets e Routers** (Parte 6) — prioridade alta. Um `ViewSet` agrupa toda a lógica de CRUD de um recurso (ex: `CardapioViewSet`) numa única classe, e um `Router` gera as URLs automaticamente, deixando `/api/cardapio/`, `/api/cardapio/1/`, `/api/fila/` com um padrão consistente para o frontend consumir.
3. **Authentication e Permissions** (Parte 4) — relevante assim que o projeto tiver login (aluno, servidor do RU, admin). Define quem pode acessar cada endpoint e como o frontend envia credenciais (token/JWT).
4. **Relationships e Hyperlinked APIs** (Parte 5) — importante quando os recursos se relacionarem entre si (ex: item do cardápio pertencer a uma categoria, ou previsão de pico referenciar uma fila específica).

Ferramentas complementares recomendadas para depois do tutorial:
- `drf-spectacular` ou `drf-yasg` — geram documentação automática (Swagger/OpenAPI) dos endpoints, essencial para o frontend saber o que existe sem perguntar direto ao backend.
- `djangorestframework-simplejwt` — implementação de autenticação via JWT.
