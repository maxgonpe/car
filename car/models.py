from django.db import models
from django.db import models
from django.conf import settings
from decimal import Decimal
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.contrib.auth.models import User
from django.db import transaction
from django.utils.timezone import now

class Mecanico(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="mecanico")
    especialidad = models.CharField(max_length=100, blank=True, null=True)
    fecha_ingreso = models.DateField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"



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
    
    
    #def __str__(self):
    #    return self.cliente.nombre

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
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("aprobado", "Aprobado"),
        ("rechazado", "Rechazado"),
    ]

    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    componentes = models.ManyToManyField(Componente, related_name='diagnosticos')
    descripcion_problema = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    subcomponentes_sugeridos = models.JSONField(blank=True, null=True)
    aceptado_por = models.CharField(max_length=100, blank=True, null=True)
    fecha_aceptacion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente") 

    def __str__(self):
        return self.vehiculo.marca
    

    def aprobar_y_clonar(self):
        """
        Convierte un diagnóstico en un trabajo, clonando también
        sus acciones y repuestos asociados.
        """
        with transaction.atomic():
            # 🚗 Crear el trabajo
            trabajo = Trabajo.objects.create(
                diagnostico=self,
                vehiculo=self.vehiculo,
                estado="iniciado",
                observaciones=self.descripcion_problema,
            )

            # 🔹 Clonar componentes (M2M)
            trabajo.componentes.set(self.componentes.all())

            # 🔹 Clonar Acciones asociadas
            for dca in self.acciones_componentes.all():
                TrabajoAccion.objects.create(
                    trabajo=trabajo,
                    componente=dca.componente,
                    accion=dca.accion,
                    precio_mano_obra=dca.precio_mano_obra,
                    completado=False  # arranca pendiente
                )

            # 🔹 Clonar Repuestos asociados
            for dr in self.repuestos.all():
                TrabajoRepuesto.objects.create(
                    trabajo=trabajo,
                    #componente=dr.componente if hasattr(dr, "componente") else None,
                    componente=getattr(dr, "componente", None),  # si no existe, queda None
                    repuesto=dr.repuesto,
                    #repuesto_stock=dr.repuesto_stock,
                    cantidad=dr.cantidad,
                    precio_unitario=dr.precio_unitario or 0,
                    subtotal=dr.subtotal or 0,
                    #estado="pendiente",  # nuevo campo sugerido en TrabajoRepuesto
                    #componente=dr.componente if hasattr(dr, "componente") else None
                )

            # Cambiar estado del diagnóstico
            self.estado = "aprobado"
            self.save()

        return trabajo


    
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


class Repuesto(models.Model):
    sku = models.CharField(max_length=64, unique=True, blank=True, null=True)  # código interno
    oem = models.CharField(max_length=64, blank=True, null=True)               # OEM / fabricante
    referencia = models.CharField(max_length=128, blank=True, null=True)       # ref proveedor
    nombre = models.CharField(max_length=250)
    marca = models.CharField(max_length=120, blank=True)
    descripcion = models.TextField(blank=True)
    medida = models.CharField(max_length=80, blank=True)   # ej. "258x22mm"
    posicion = models.CharField(max_length=80, blank=True) # ej. "freno delantero"
    unidad = models.CharField(max_length=20, default='pieza')
    precio_costo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.sku or self.oem or 'sin-cod'})"

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self.generate_sku()
        super().save(*args, **kwargs)

    def generate_sku(self):
        # === Diccionario opcional de prefijos conocidos ===
        prefijos = {
            "freno": "FRE",
            "filtro": "FIL",
            "aceite": "OIL",
            "bujía": "BUJ",
            "batería": "BAT",
            "amortiguador": "AMO",
            "correa": "COR",
            "embrague": "EMB",
        }

        # === Detectar prefijo ===
        base_text = f"{self.nombre} {self.posicion}".lower()
        tipo = None
        for k, v in prefijos.items():
            if k in base_text:
                tipo = v
                break

        if not tipo:
            # Si no hay prefijo definido, tomar primeras letras del nombre
            tipo = (self.nombre[:3].upper() if self.nombre else "GEN")

        # === Marca abreviada ===
        marca = (self.marca[:3].upper() if self.marca else "GEN")

        # === Posición o componente abreviado ===
        comp = (self.posicion[:3].upper() if self.posicion else "REP")

        # === Secuencia aleatoria numérica (4 dígitos) ===
        referencia = get_random_string(length=4, allowed_chars="0123456789")

        return f"{tipo}-{marca}-{comp}-{referencia}"

class VehiculoVersion(models.Model):
    marca = models.CharField(max_length=80)
    modelo = models.CharField(max_length=120)
    anio_desde = models.IntegerField()
    anio_hasta = models.IntegerField()
    # opcionales: engine_code, trim, etc.

    class Meta:
        unique_together = ("marca", "modelo", "anio_desde", "anio_hasta")

    def __str__(self):
        return f"{self.marca} {self.modelo} {self.anio_desde}-{self.anio_hasta}"

class ComponenteRepuesto(models.Model):
    componente = models.ForeignKey('Componente', on_delete=models.CASCADE)  # tu modelo de componente
    repuesto = models.ForeignKey(Repuesto, on_delete=models.CASCADE)
    nota = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("componente", "repuesto")

class RepuestoAplicacion(models.Model):
    repuesto = models.ForeignKey(Repuesto, on_delete=models.CASCADE, related_name="aplicaciones")
    version = models.ForeignKey(VehiculoVersion, on_delete=models.CASCADE)
    posicion = models.CharField(max_length=80, blank=True)  # opcional, sinon usar repuesto.posicion

    class Meta:
        unique_together = ("repuesto", "version")

class RepuestoEnStock(models.Model):
    repuesto = models.ForeignKey(Repuesto, on_delete=models.CASCADE, related_name='stocks')
    deposito = models.CharField(max_length=80, default='bodega-principal')  # o FK a un modelo Deposito
    proveedor = models.CharField(max_length=120, blank=True)  # info del proveedor
    stock = models.IntegerField(default=0)
    reservado = models.IntegerField(default=0)  # cantidad reservada por diagnósticos pendientes
    precio_compra = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # en este sitio
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("repuesto", "deposito", "proveedor")

    @property
    def disponible(self):
        return self.stock - (self.reservado or 0)

class StockMovimiento(models.Model):
    repuesto_stock = models.ForeignKey(RepuestoEnStock, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=20, choices=(('ingreso','ingreso'),('salida','salida'),('reserva','reserva'),('liberacion','liberacion')))
    cantidad = models.IntegerField()
    motivo = models.CharField(max_length=200, blank=True)
    referencia = models.CharField(max_length=120, blank=True)  # ej ODT/DIAG id
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    fecha = models.DateTimeField(auto_now_add=True)

class DiagnosticoRepuesto(models.Model):
    diagnostico = models.ForeignKey('Diagnostico', on_delete=models.CASCADE, related_name='repuestos')
    repuesto = models.ForeignKey(Repuesto, on_delete=models.PROTECT)
    repuesto_stock = models.ForeignKey(RepuestoEnStock, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    reservado = models.BooleanField(default=False)  # si fue reservado en stock
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.repuesto} (x{self.cantidad})"

# ========================
# Trabajo (clonado desde Diagnóstico aprobado)
# ========================

class Trabajo(models.Model):
    ESTADOS = [
        ("iniciado", "Iniciado"),
        ("trabajando", "Trabajando"),
        ("completado", "Completado"),
        ("entregado", "Entregado"),
    ]

    diagnostico = models.OneToOneField(Diagnostico, on_delete=models.CASCADE, related_name="trabajo")
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="en_proceso")
    observaciones = models.TextField(blank=True, null=True)
    mecanicos = models.ManyToManyField("Mecanico", related_name="trabajos", blank=True)

    # 🔹 Nuevo: relacionar con componentes (igual que Diagnostico)
    componentes = models.ManyToManyField("Componente", related_name="trabajos", blank=True)

    def __str__(self):
        return f"Trabajo #{self.id} - {self.vehiculo}"

    @property
    def total_mano_obra(self):
        return sum(a.precio_mano_obra for a in self.acciones.all())

    @property
    def total_repuestos(self):
        return sum(r.subtotal or 0 for r in self.repuestos.all())

    @property
    def total_general(self):
        return self.total_mano_obra + self.total_repuestos

    @property
    def porcentaje_avance(self):
        acciones_total = self.acciones.count()
        repuestos_total = self.repuestos.count()
        total_items = acciones_total + repuestos_total

        if total_items == 0:
            return 0  # nada registrado

        acciones_completadas = self.acciones.filter(completado=True).count()
        repuestos_instalados = self.repuestos.filter(completado=True).count()
        completados = acciones_completadas + repuestos_instalados

        return int((completados / total_items) * 100)

class TrabajoFoto(models.Model):
    trabajo = models.ForeignKey(Trabajo, on_delete=models.CASCADE, related_name="fotos")
    imagen = models.ImageField(upload_to="trabajos/fotos/%Y/%m/%d")
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foto {self.id} de {self.trabajo}"


class TrabajoAccion(models.Model):
    trabajo = models.ForeignKey(Trabajo, on_delete=models.CASCADE, related_name="acciones")
    componente = models.ForeignKey("Componente", on_delete=models.CASCADE)
    accion = models.ForeignKey("Accion", on_delete=models.CASCADE)
    precio_mano_obra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    completado = models.BooleanField(default=False)
    fecha = models.DateTimeField(null=True, blank=True)

    #def __str__(self):
    #    return f"{self.trabajo} - {self.accion.nombre} {self.componente.nombre}"
    @property
    def costo(self):
        return self.accion.costo if self.completado else 0

    def __str__(self):
        return f"{self.accion} ({'✔️' if self.completado else 'pendiente'})"


class TrabajoRepuesto(models.Model):
    trabajo = models.ForeignKey(Trabajo, on_delete=models.CASCADE, related_name="repuestos")
    componente = models.ForeignKey(Componente, on_delete=models.CASCADE, null=True, blank=True)
    repuesto = models.ForeignKey("Repuesto", on_delete=models.PROTECT)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    completado = models.BooleanField(default=False)
    fecha = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.repuesto} (x{self.cantidad})"

