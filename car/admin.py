from django.contrib import admin
from .models import (
    Cliente, Vehiculo, Componente,
    Diagnostico, Accion, ComponenteAccion, DiagnosticoComponenteAccion,
    Repuesto, RepuestoEnStock, DiagnosticoRepuesto,StockMovimiento,
    VehiculoVersion, ComponenteRepuesto,
    RepuestoAplicacion

    )

# --- Inline para ComponenteAccion dentro de Componente ---
class ComponenteAccionInline(admin.TabularInline):
    model = ComponenteAccion
    extra = 1
    autocomplete_fields = ['accion']

# --- Admin de Componente ---
@admin.register(Componente)
class ComponenteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre',)
    search_fields = ('nombre',)
    inlines = [ComponenteAccionInline]

# --- Admin de Accion ---
@admin.register(Accion)
class AccionAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre',)
    search_fields = ('nombre',)

# --- Admin de ComponenteAccion ---
@admin.register(ComponenteAccion)
class ComponenteAccionAdmin(admin.ModelAdmin):
    list_display = ('componente', 'accion', 'precio_mano_obra')
    list_filter = ('componente', 'accion')
    search_fields = ('componente__nombre', 'accion__nombre')

# --- Inline para DiagnosticoComponenteAccion dentro de Diagnostico ---
class DiagnosticoComponenteAccionInline(admin.TabularInline):
    model = DiagnosticoComponenteAccion
    extra = 1
    autocomplete_fields = ['componente', 'accion']

# --- Admin de Diagnostico ---
@admin.register(Diagnostico)
class DiagnosticoAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'descripcion_problema', 'fecha')
    list_filter = ('fecha',)
    search_fields = (
        'vehiculo__placa',
        'vehiculo__marca',
        'componentes__nombre',
    )
    inlines = [DiagnosticoComponenteAccionInline]

# --- Admin de Vehiculo ---
@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('id', 'marca', 'modelo', 'anio', 'placa')
    search_fields = ('marca', 'modelo', 'placa')

# --- Admin de Cliente ---
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'telefono')
    search_fields = ('nombre', 'telefono')

admin.site.register(DiagnosticoComponenteAccion)
admin.site.register(Repuesto)
admin.site.register(RepuestoEnStock)
admin.site.register(DiagnosticoRepuesto)
admin.site.register(StockMovimiento)
admin.site.register(VehiculoVersion)
admin.site.register(ComponenteRepuesto)
admin.site.register(RepuestoAplicacion)