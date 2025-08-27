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
    path('diagnosticos/', views.lista_diagnosticos, name='lista_diagnosticos'),
    path('eliminar/diagnosticos/', views.eliminar_diagnostico, name='eliminar_diagnostico'),
    path("car/acciones-lookup/<int:componente_id>/", views.acciones_por_componente, name="acciones_por_componente"),
    # Acciones
    path("acciones/", views.accion_list, name="accion_list"),
    path("acciones/nueva/", views.accion_create, name="accion_create"),
    path("acciones/<int:pk>/editar/", views.accion_update, name="accion_update"),
    path("acciones/<int:pk>/eliminar/", views.accion_delete, name="accion_delete"),

    # Componente + Acción (precios)
    path("componente-acciones/", views.comp_accion_list, name="comp_accion_list"),
    path("componente-acciones/nuevo/", views.comp_accion_create, name="comp_accion_create"),
    path("componente-acciones/<int:pk>/editar/", views.comp_accion_update, name="comp_accion_update"),
    path("componente-acciones/<int:pk>/eliminar/", views.comp_accion_delete, name="comp_accion_delete"),

]   


