from django.contrib import admin
from django.urls import path, include
from car.views import panel_principal

urlpatterns = [
    path('', panel_principal, name='panel_principal'),
    path('admin/', admin.site.urls),
    path('car/', include('car.urls')),
]
