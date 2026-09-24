from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])
def cadastro_view(request):
    resposta_falsa = {
        "status": "sucesso",
        "mensagem": "Estrutura de cadastro simulada com sucesso!"
    }
    return Response(resposta_falsa, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def login_view(request):
    resposta_falsa = {
        "status": "sucesso",
        "token": "token-falso-de-teste-12345",
        "mensagem": "Estrutura de login simulada com sucesso!"
    }
    return Response(resposta_falsa, status=status.HTTP_200_OK)

