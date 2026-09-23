from django.contrib import admin
from django.urls import path, include
from apps.usuarios import views as usuarios_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.status.urls')), 
    
    # Minhas rotas da Sprint 2:
    path('api/cadastro/', usuarios_views.cadastro_view, name='api-cadastro'),
    path('api/login/', usuarios_views.login_view, name='api-login'),
]
