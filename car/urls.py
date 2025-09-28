from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.utils.timezone import now
from django.shortcuts import redirect
from .import views
from .views_api import vehiculo_lookup
from .views import ClienteListView,VehiculoListView,\
                   VehiculoCreateView,VehiculoUpdateView,\
                   VehiculoDeleteView,MecanicoListView,\
                   MecanicoDeleteView,MecanicoCreateView,\
                   MecanicoUpdateView 

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # === Componentes ===
    path('componentes/', views.componente_list, name='componente_list'),
    path('componentes/nuevo/', views.componente_create, name='componente_create'),
    path('componentes/<int:pk>/editar/', views.componente_update, name='componente_update'),
    path('componentes/<int:pk>/eliminar/', views.componente_delete, name='componente_delete'),
    path('componentes-lookup/', views.componentes_lookup, name='componentes_lookup'),
    path('componentes/seleccionar/<str:codigo>/', views.seleccionar_componente, name='seleccionar_componente'),

    # === Ingreso / Diagnóstico ===
    path('ingreso/', views.ingreso_view, name='ingreso'),
    path('ingreso/exito/', views.ingreso_exitoso_view, name='ingreso_exitoso'),
    path('ingreso/editar/<int:pk>/', views.editar_diagnostico, name='editar_diagnostico'),
    path('ingreso/eliminar/<int:pk>/', views.eliminar_diagnostico, name='eliminar_diagnostico'),
    path('diagnosticos/', views.lista_diagnosticos, name='lista_diagnosticos'),

    # === Plano interactivo ===
    path('plano/', views.mostrar_plano, name='plano_interactivo'),

    # === Acciones ===
    path('acciones/', views.accion_list, name='accion_list'),
    path('acciones/nueva/', views.accion_create, name='accion_create'),
    path('acciones/<int:pk>/editar/', views.accion_update, name='accion_update'),
    path('acciones/<int:pk>/eliminar/', views.accion_delete, name='accion_delete'),
    path('car/acciones-lookup/<int:componente_id>/', views.acciones_por_componente, name='acciones_por_componente'),
    path("vehiculo_lookup/", vehiculo_lookup, name="vehiculo_lookup"),

    # === Componente + Acción (precios) ===
    path('componente-acciones/', views.comp_accion_list, name='comp_accion_list'),
    path('componente-acciones/nuevo/', views.comp_accion_create, name='comp_accion_create'),
    path('componente-acciones/<int:pk>/editar/', views.comp_accion_update, name='comp_accion_update'),
    path('componente-acciones/<int:pk>/eliminar/', views.comp_accion_delete, name='comp_accion_delete'),

    # === Repuestos sugeridos ===
    path('diagnostico/sugerir-repuestos/', views.sugerir_repuestos, name='sugerir_repuestos_preview'),
    path('diagnostico/<int:diagnostico_id>/sugerir-repuestos/', views.sugerir_repuestos, name='sugerir_repuestos'),
    path("diagnosticos/excel/", views.exportar_diagnosticos_excel, name="diagnosticos_excel"),
    path("diagnosticos/pdf/", views.exportar_diagnosticos_pdf, name="diagnosticos_pdf"),
    path("diagnosticos/<int:pk>/excel/", views.exportar_diagnostico_excel, name="diagnostico_excel"),
    path("diagnosticos/<int:pk>/pdf/", views.exportar_diagnostico_pdf, name="diagnostico_pdf"),
    path("diagnostico/<int:pk>/aprobar/", views.aprobar_diagnostico, name="aprobar_diagnostico"),
    # === CRUD de repuestos en diagnóstico ===
    path('diagnostico/<int:diagnostico_id>/agregar-repuesto/', views.agregar_repuesto, name='agregar_repuesto'),
    path('diagnostico/<int:diagnostico_id>/repuestos/', views.listar_repuestos_diagnostico, name='listar_repuestos_diagnostico'),
    # Mecanicos
    path("mecanicos/", MecanicoListView.as_view(), name="mecanico_list"),
    path("mecanicos/nuevo/", views.MecanicoCreateView.as_view(), name="mecanico_create"),
    path("mecanicos/<int:pk>/editar/", views.MecanicoUpdateView.as_view(), name="mecanico_update"),
    path("mecanicos/<int:pk>/eliminar/", views.MecanicoDeleteView.as_view(), name="mecanico_delete"),
    # Clientes
    path("clientes/", ClienteListView.as_view(), name="cliente_list"),
    path("clientes/nuevo/", views.ClienteCreateView.as_view(), name="cliente_create"),
    path("clientes/<int:pk>/editar/", views.ClienteUpdateView.as_view(), name="cliente_update"),
    path("clientes/<int:pk>/eliminar/", views.ClienteDeleteView.as_view(), name="cliente_delete"),
    # Vehículos
    path("vehiculos/", VehiculoListView.as_view(), name="vehiculo_list"),
    path("vehiculos/nuevo/", VehiculoCreateView.as_view(), name="vehiculo_create"),
    path("vehiculos/<int:pk>/editar/", VehiculoUpdateView.as_view(), name="vehiculo_update"),
    path("vehiculos/<int:pk>/eliminar/", VehiculoDeleteView.as_view(), name="vehiculo_delete"),
    # Trabajos
    path("trabajos/", views.lista_trabajos, name="lista_trabajos"),
    path("trabajos/<int:pk>/", views.trabajo_detalle, name="trabajo_detalle"),
    # Pizarra
    path("pizarra/", views.pizarra_view, name="pizarra"),
    # Ventas
    path("crear/", views.venta_crear, name="venta_crear"),
    path("<int:pk>/", views.venta_detalle, name="venta_detalle"),
    path("historial/", views.ventas_historial, name="ventas_historial"),
    path("repuesto-lookup/", views.repuesto_lookup, name="repuesto_lookup"),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#if settings.DEBUG:
#    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


