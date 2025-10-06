from django.contrib import admin
from .models import (
    Cliente, Vehiculo, Mecanico,
    Diagnostico, DiagnosticoComponenteAccion, DiagnosticoRepuesto,
    Trabajo, TrabajoAccion, TrabajoRepuesto,TrabajoFoto,
    Componente, Accion, ComponenteAccion,
    Repuesto, RepuestoEnStock, StockMovimiento,
    VehiculoVersion, ComponenteRepuesto, RepuestoAplicacion,
    Venta, VentaItem, PrefijoRepuesto
)

@admin.register(Mecanico)
class MecanicoAdmin(admin.ModelAdmin):
    list_display = ('id', 'especialidad', 'fecha_ingreso','activo')
    search_fields = ('especialidad', 'fecha_ingreso')

# ======================
# Clientes y Vehículos
# ======================
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'telefono')
    search_fields = ('nombre', 'telefono')


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('id', 'placa', 'marca', 'modelo', 'anio')
    search_fields = ('placa', 'marca', 'modelo')


# ======================
# Catálogo de Componentes y Acciones
# ======================
class ComponenteAccionInline(admin.TabularInline):
    model = ComponenteAccion
    extra = 1
    autocomplete_fields = ['accion']


@admin.register(Componente)
class ComponenteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    inlines = [ComponenteAccionInline]


@admin.register(Accion)
class AccionAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(ComponenteAccion)
class ComponenteAccionAdmin(admin.ModelAdmin):
    list_display = ('componente', 'accion', 'precio_mano_obra')
    list_filter = ('componente', 'accion')
    search_fields = ('componente__nombre', 'accion__nombre')


# ======================
# Diagnóstico
# ======================
class DiagnosticoComponenteAccionInline(admin.TabularInline):
    model = DiagnosticoComponenteAccion
    extra = 1
    autocomplete_fields = ['componente', 'accion']


class DiagnosticoRepuestoInline(admin.TabularInline):
    model = DiagnosticoRepuesto
    extra = 1
    autocomplete_fields = ['repuesto']


@admin.register(Diagnostico)
class DiagnosticoAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehiculo', 'descripcion_problema', 'estado', 'fecha')
    list_filter = ('estado', 'fecha')
    search_fields = ('vehiculo__placa', 'vehiculo__marca', 'componentes__nombre')
    inlines = [DiagnosticoComponenteAccionInline, DiagnosticoRepuestoInline]


# ======================
# Trabajo (clonado desde Diagnóstico aprobado)
# ======================
class TrabajoAccionInline(admin.TabularInline):
    model = TrabajoAccion
    extra = 1
    autocomplete_fields = ['componente', 'accion']


class TrabajoRepuestoInline(admin.TabularInline):
    model = TrabajoRepuesto
    extra = 1
    autocomplete_fields = ['repuesto']


@admin.register(Trabajo)
class TrabajoAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehiculo', 'estado', 'fecha_inicio', 'fecha_fin')
    list_filter = ('estado', 'fecha_inicio', 'fecha_fin')
    search_fields = ('vehiculo__placa', 'vehiculo__marca')
    inlines = [TrabajoAccionInline, TrabajoRepuestoInline]


# ======================
# Repuestos y Stock
# ======================

@admin.register(PrefijoRepuesto)
class PrefijoRepuestoAdmin(admin.ModelAdmin):
    list_display = ("palabra", "abreviatura")
    search_fields = ("palabra", "abreviatura")

@admin.register(Repuesto)
class RepuestoAdmin(admin.ModelAdmin):
    list_display = ('id', 'sku', 'oem', 'referencia', 'nombre', 'precio_costo', 'precio_venta')
    search_fields = ('nombre', 'oem', 'sku','codigo_barra')
    list_filter = ("marca", "posicion")

@admin.register(ComponenteRepuesto)
class ComponenteRepuestoAdmin(admin.ModelAdmin):
    list_display = ('id', 'componente', 'repuesto', 'nota')

@admin.register(TrabajoAccion)
class TrabajoAccionAdmin(admin.ModelAdmin):
    list_display = ('id', 'trabajo','componente', 'accion', 'precio_mano_obra')


admin.site.register(RepuestoEnStock)
admin.site.register(StockMovimiento)
admin.site.register(VehiculoVersion)
admin.site.register(RepuestoAplicacion)
#admin.site.register(TrabajoAccion)
admin.site.register(TrabajoFoto)
admin.site.register(TrabajoRepuesto)
admin.site.register(Venta)
admin.site.register(VentaItem)