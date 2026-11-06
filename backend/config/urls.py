from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.cadastro.urls')),
    path('api/', include('apps.cardapio.urls')),
    path('api/', include('apps.avaliacao.urls')),
    path('api/', include('apps.fila.urls')),
    path('api/', include('apps.gamificacao.urls')),
]
