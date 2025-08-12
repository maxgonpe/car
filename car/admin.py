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

class DiagnosticoAdmin(admin.ModelAdmin):
    list_display = ('id','vehiculo', 'componente','descripcion_problema','subcomponentes_sugeridos')


admin.site.register(Cliente,ClienteAdmin)
admin.site.register(Vehiculo,VehiculoAdmin)
admin.site.register(Componente,ComponenteAdmin)
admin.site.register(Diagnostico,DiagnosticoAdmin)
admin.site.register(Reparacion)
admin.site.register(RepuestoRecomendado)
admin.site.register(Presupuesto)


