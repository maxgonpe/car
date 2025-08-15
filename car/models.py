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

    def __str__(self):
        # Acceder al anio
        return f"{self.marca} {self.modelo} {self.anio}"

    

    

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
    #componente = models.ForeignKey(Componente, on_delete=models.PROTECT, related_name='diagnosticos')
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

class RepuestoRecomendado(models.Model):
    reparacion = models.ForeignKey(Reparacion, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=[
        ('pendiente', 'Pendiente'),
        ('en_stock', 'En stock'),
        ('pedido', 'Solicitado'),
        ('instalado', 'Instalado'),
    ], default='pendiente')


class Presupuesto(models.Model):
    diagnostico = models.OneToOneField(Diagnostico, on_delete=models.CASCADE)
    costo_repuestos = models.DecimalField(max_digits=10, decimal_places=2)
    costo_mano_obra = models.DecimalField(max_digits=10, decimal_places=2)
    ganancia = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_entrega = models.DateField()



