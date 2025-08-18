from django.contrib import admin
from .models import (Cliente, Vehiculo, Componente,
					 Diagnostico, Reparacion, 
					 RepuestoRecomendado, Presupuesto)


class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('id','cliente', 'marca', 'modelo','anio','placa','descripcion_motor')

class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id','nombre', 'telefono')

class ComponenteAdmin(admin.ModelAdmin):
    list_display = ('id','nombre', 'padre','activo')

class DiagnosticoAdmin2(admin.ModelAdmin):
    list_display = ('id','vehiculo', 'descripcion_problema','subcomponentes_sugeridos')

class DiagnosticoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'vehiculo',
        'nombre_cliente',
        'descripcion_problema',
        'listar_componentes',
        'subcomponentes_sugeridos',
        'fecha',
    )

    def nombre_cliente(self, obj):
        return obj.vehiculo.cliente.nombre  # Acceder al nombre del cliente

    nombre_cliente.short_description = 'Cliente'

    #def listar_componentes(self, obj):
    #    return ", ".join([c.nombre for c in obj.componentes.all()])
    #listar_componentes.short_description = "Componentes"

    def listar_componentes(self, obj):
        return ", ".join([c.nombre for c in obj.componentes.order_by('padre__nombre', 'nombre')])


admin.site.register(Cliente,ClienteAdmin)
admin.site.register(Vehiculo,VehiculoAdmin)
admin.site.register(Componente,ComponenteAdmin)
admin.site.register(Diagnostico,DiagnosticoAdmin)
admin.site.register(Reparacion)
admin.site.register(RepuestoRecomendado)
admin.site.register(Presupuesto)


