from django.contrib import admin
from django.urls import path, include
from car.views import panel_principal,get_vehiculos_por_cliente

urlpatterns = [
    path('', panel_principal, name='panel_principal'),
    path('admin/', admin.site.urls),
    path('car/', include('car.urls')),
    path('api/vehiculos/<int:cliente_id>/', get_vehiculos_por_cliente, name='api_vehiculos_por_cliente'),
]
