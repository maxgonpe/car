from django.db import models
from django.db import models
from django.utils.text import slugify

# Create your models here.
class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)

    def __str__(self):
        return self.nombre


class Vehiculo(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    anio = models.PositiveIntegerField()
    vin = models.CharField(max_length=50, blank=True, null=True)
    placa = models.CharField(max_length=10)

    # Motor predefinido (opcional pero útil para IA)
    descripcion_motor = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return self.cliente.nombre

    #def __str__(self):
    #    # Acceder al anio
    #    return f"{self.marca} {self.modelo} {self.anio}"

    
    def __str__(self):
        return f"{self.placa} • {self.marca} {self.modelo} ({self.anio})"


    

class Componente(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=255, unique=True, editable=False)  # se autogenera
    activo = models.BooleanField(default=True)
    padre = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,            # <- eliminará el subárbol completo
        null=True, blank=True,
        related_name='hijos'
    )

    class Meta:
        # evita duplicar el mismo nombre dentro del mismo padre
        constraints = [
            models.UniqueConstraint(
                fields=['padre', 'nombre'], name='unique_nombre_por_padre'
            )
        ]
        indexes = [
            models.Index(fields=['codigo']),
        ]

    def __str__(self):
        return self.nombre

    # ───────── helpers ─────────
    def build_codigo(self) -> str:
        """Construye el código jerárquico legible."""
        slug = slugify(self.nombre).replace('_', '-')
        if self.padre:
            return f"{self.padre.codigo}-{slug}"
        return slug

    def _update_descendant_codes(self):
        """Propaga el nuevo código a toda la descendencia."""
        for hijo in self.hijos.all():
            # recalcular usando el nuevo self.codigo como base
            hijo.codigo = f"{self.codigo}-{slugify(hijo.nombre).replace('_','-')}"
            super(Componente, hijo).save(update_fields=['codigo'])  # guarda sin recursión extra
            hijo._update_descendant_codes()

    def save(self, *args, **kwargs):
        # Detectar si cambia padre o nombre (para decidir si propagamos)
        old_parent_id = None
        old_nombre = None
        if self.pk:
            prev = type(self).objects.get(pk=self.pk)
            old_parent_id = prev.padre_id
            old_nombre = prev.nombre

        # Siempre recalculamos el código antes de guardar
        self.codigo = self.build_codigo()
        if self.nombre:
            self.nombre = self.nombre.lower()
        super().save(*args, **kwargs)

        # Si cambió el nombre o el padre, hay que propagar a los hijos
        if self.pk and (old_parent_id != self.padre_id or old_nombre != self.nombre):
            self._update_descendant_codes()


class Diagnostico(models.Model):
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    componentes = models.ManyToManyField(Componente, related_name='diagnosticos')
    descripcion_problema = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    subcomponentes_sugeridos = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.vehiculo.marca


class Reparacion(models.Model):
    diagnostico = models.ForeignKey(Diagnostico, on_delete=models.CASCADE)
    subcomponente = models.CharField(max_length=100)
    accion = models.CharField(max_length=200)
    tiempo_estimado_minutos = models.PositiveIntegerField()



class Accion(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class ComponenteAccion(models.Model):
    componente = models.ForeignKey("Componente", on_delete=models.CASCADE)
    accion = models.ForeignKey("Accion", on_delete=models.CASCADE)
    precio_mano_obra = models.DecimalField(max_digits=10,decimal_places=2,default=0)

    class Meta:
        unique_together = ('componente','accion')

        def __str__(self):
            return f"{self.accion.nombre} {self.componente.nombre} - ${self.precio_mano_obra}"
            
class DiagnosticoComponenteAccion(models.Model):
    diagnostico = models.ForeignKey("Diagnostico", on_delete=models.CASCADE, related_name="acciones_componentes")
    componente = models.ForeignKey("Componente", on_delete=models.CASCADE)
    accion = models.ForeignKey("Accion", on_delete=models.CASCADE)
    precio_mano_obra = models.DecimalField(max_digits=10, decimal_places=2,default=0)

    def __str__(self):
        return f"{self.diagnostico.vehiculo} - {self.accion.nombre} {self.componente.nombre}"


    # --- Solo para mostrar en el admin como referencia ---
    def precio_base_sugerido(self):
        try:
            base = ComponenteAccion.objects.get(componente=self.componente, accion=self.accion)
            return base.precio_mano_obra
        except ComponenteAccion.DoesNotExist:
            return None
    precio_base_sugerido.short_description = "Precio base (catálogo)"

    # --- Validación opcional: exigir que exista el precio base en catálogo ---
    def clean(self):
        # si quieres forzar que exista esa combinación en el catálogo, descomenta:
        # if not ComponenteAccion.objects.filter(componente=self.componente, accion=self.accion).exists():
        #     raise ValidationError("No existe precio base en el catálogo para esta combinación Componente + Acción.")

        super().clean()

    # --- Autocompletar si no se ingresó precio explícito ---
    def save(self, *args, **kwargs):
        if (self.precio_mano_obra is None or self.precio_mano_obra == 0) and self.componente_id and self.accion_id:
            try:
                base = ComponenteAccion.objects.get(componente=self.componente, accion=self.accion)
                self.precio_mano_obra = base.precio_mano_obra
            except ComponenteAccion.DoesNotExist:
                # Si no existe en catálogo, lo dejamos en 0 para que el admin lo note
                pass
        super().save(*args, **kwargs)



