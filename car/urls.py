from django.urls import path
from .import views


urlpatterns = [
    #path('', views.panel_principal, name='panel_principal'),
    path('componentes/', views.componente_list, name='componente_list'),
    path('componentes/nuevo/', views.componente_create, name='componente_create'),
    path('componentes/<int:pk>/editar/', views.componente_update, name='componente_update'),
    path('componentes/<int:pk>/eliminar/', views.componente_delete, name='componente_delete'),
    path('ingreso/', views.ingreso_view, name='ingreso'),
    path('ingreso/exito/', views.ingreso_exitoso_view, name='ingreso_exitoso'),
    path('ingreso/editar/<int:pk>/', views.editar_diagnostico, name='editar_diagnostico'),
    path('ingreso/eliminar/<int:pk>/', views.eliminar_diagnostico, name='eliminar_diagnostico'),
    #path('api/vehiculos/<int:cliente_id>/', views.get_vehiculos_por_cliente, name='api_vehiculos_por_cliente'),
    path('componentes-lookup/', views.componentes_lookup, name='componentes_lookup'),
    path('componentes/seleccionar/<str:codigo>/', views.seleccionar_componente, name='seleccionar_componente'),
    path('plano/', views.mostrar_plano, name='plano_interactivo'),

]   


