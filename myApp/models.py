from django.db import models
from django.core.exceptions import ValidationError
# -------------------------
# Usuario
# -------------------------
class Usuario(models.Model):
    ROL_CHOICES = [
        ('Administrador', 'Administrador'),
        ('Supervisor', 'Supervisor'),
    ]

    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
        ('Incapacitado', 'Incapacitado'),
        ('Suspendido', 'Suspendido'),
    ]

    HORARIO_CHOICES = [
        ('Mañana 6:00am - 2:00pm', 'Mañana 6:00am - 2:00pm'),
        ('Tarde 2:00pm - 10:00pm', 'Tarde 2:00pm - 10:00pm'),
    ]

    nombre       = models.CharField(max_length=100)
    email        = models.EmailField(unique=True, max_length=255)
    ttelefono    = models.CharField(max_length=10, blank=True, null=True)
    direccion    = models.CharField(max_length=255)
    contrasena   = models.CharField(max_length=255)
    rol          = models.CharField(max_length=20, choices=ROL_CHOICES)
    estado       = models.CharField(max_length=20, choices=ESTADO_CHOICES)
   
    def __str__(self):
        return self.nombre
# -------------------------
# Empleado
# -------------------------
class Empleado(models.Model):
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
        ('Incapacitado', 'Incapacitado'),
        ('Suspendido', 'Suspendido'),
    ]

    cedula = models.CharField(max_length=20, null=True, blank=True)
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True, max_length=255)
    telefono = models.CharField(max_length=10, blank=True, null=True)
    direccion = models.CharField(max_length=255)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)

    creado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='creado_por')

    def __str__(self):
        return self.nombre


# -------------------------
# Turno
# -------------------------
class Turno(models.Model):
    HORARIO_CHOICES = [
        ('Mañana 6:00am - 2:00pm', 'Mañana 6:00am - 2:00pm'),
        ('Tarde 2:00pm - 10:00pm', 'Tarde 2:00pm - 10:00pm'),
    ]

    horario  = models.CharField(max_length=50, choices=HORARIO_CHOICES)
    activo   = models.BooleanField(default=True)
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column='creado_por',
        related_name='turnos_creados'  # ← esto resuelve el conflicto E303
    )

    def __str__(self):
        return f"{self.horario}"


# -------------------------
# Rotacion Turno
# -------------------------
class RotacionTurno(models.Model):
    ESTADO_CHOICES = [
        ('Asignado', 'Asignado'),
        ('Completado', 'Completado'),
        ('Pendiente', 'Pendiente'),
    ]

    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    semana = models.IntegerField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')
    sabado_asignado = models.BooleanField(default=False)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)
    
    # Esto es lo que evita que los empleados tengan doble turno en la misma semana
    class Meta:
        constraints = [
        models.UniqueConstraint(
            fields=['empleado', 'fecha_inicio', 'fecha_fin'],
            name='unique_turno_semanal'
        )
    ]

    def __str__(self):
        return f"{self.empleado} - {self.turno} - Semana {self.semana}"

# -------------------------
# Solicitud Cambio de Turno
# -------------------------
class Solicitud(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Aprobado', 'Aprobado'),
        ('Rechazado', 'Rechazado'),
    ]

    turno_actual = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='turno_actual')
    turno_solicitado = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='turno_solicitado')
    motivo = models.TextField()
    fecha_solicitud = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    revisado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.empleado} - {self.estado}"

# -------------------------
# Asignacion
# -------------------------
class Asignacion(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('En Proceso', 'En Proceso'),
        ('Finalizado', 'Finalizado'),

    ]
    
    tarea = models.CharField(max_length=255)
    fecha_asignacion = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, db_column='empleado_id')
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, db_column='turno_id')
    asignado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='asignado_por')
    
      # VALIDACIÓN
    def clean(self):

        tareas_diarias = Asignacion.objects.filter(
            empleado=self.empleado,
            fecha_asignacion=self.fecha_asignacion
        ).exclude(id=self.id).count()

        if tareas_diarias >= 2:
            raise ValidationError(
                "El empleado ya tiene el máximo de 2 tareas diarias."
            )

    # GUARDA VALIDANDO
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tarea} - {self.empleado}"

# -------------------------
# Produccion
# -------------------------
class Produccion(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('En Proceso', 'En Proceso'),
        ('Cancelado', 'Cancelado'),
        ('Finalizado', 'Finalizado'),
    ]

    producto = models.CharField(max_length=255, null=True, blank=True)
    ingredientes = models.CharField(max_length=255)
    cantidad_requerida = models.CharField(max_length=255, null=True, blank=True)
    fecha_entrega = models.DateField()
    fecha_limite = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)

    empleado_responsable = models.ForeignKey(Empleado, on_delete=models.CASCADE, db_column='empleado_responsable')
    creado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='creado_por')

    def __str__(self):
        return f"{self.producto} - {self.estado}"

# -------------------------
# Exportacion
# -------------------------
class Exportacion(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Enviado', 'Enviado'),
        ('Entregado', 'Entregado'),
        ('Cancelado', 'Cancelado'),
    ]

    destino = models.CharField(max_length=255)
    pais = models.CharField(max_length=255, default='Sin producto')
    fecha_envio = models.DateField()
    fecha_entrega = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)

    produccion = models.ForeignKey(Produccion, on_delete=models.CASCADE, db_column='produccion_id', null=True,      # ← permite nulo
        blank=True)
    producto = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.destino} - {self.estado}"

# -------------------------
# Lote
# -------------------------
class Lote(models.Model):
    codigo_lote = models.CharField(max_length=100, unique=True)
    cantidad = models.CharField(max_length=255)
    fecha_produccion = models.DateField()
    fecha_vencimiento = models.DateField()

    produccion = models.ForeignKey(Produccion, on_delete=models.CASCADE, db_column='produccion_id')
    exportacion = models.ForeignKey(Exportacion, on_delete=models.CASCADE, db_column='exportacion_id')
    
    def __str__(self):
        return self.codigo_lote
    
# ---------------------
# Bitacora
# ---------------------
class Bitacora(models.Model):

    TIPO_CHOICES = [
        ('Diario', 'Diario'),
        ('Semanal', 'Semanal'),
    ]

    ESTADO_CHOICES = [
        ('Borrador', 'Borrador'),
        ('Enviado', 'Enviado'),
        ('Aprobado', 'Aprobado'),
        ('Rechazado', 'Rechazado'),
    ]

    titulo              = models.CharField(max_length=255)
    descripcion         = models.TextField()
    tipo_reporte        = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha_registro      = models.DateField(auto_now_add=True)
    estado              = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Borrador')
    observaciones       = models.TextField(blank=True, null=True)
    unidades_producidas = models.CharField(max_length=255, null=True, blank=True)
    unidades_pendientes = models.CharField(max_length=255, null=True, blank=True)

    supervisor = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column='supervisor_id',
        related_name='bitacoras_creadas'
    )

    produccion = models.ForeignKey(
        Produccion,
        on_delete=models.CASCADE,
        db_column='produccion_id',
        null=True,
        blank=True
    )

    revisado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        db_column='revisado_por',
        null=True,
        blank=True,
        related_name='bitacoras_revisadas'
    )

    fecha_revision = models.DateField(
        null=True,
        blank=True
    )

    observacion_admin = models.TextField(
        blank=True,
        null=True
    )

    def clean(self):

        if not self.titulo:
            raise ValidationError(
                {'titulo': 'El título es obligatorio.'}
            )

        if len(self.titulo.strip()) < 5:
            raise ValidationError(
                {'titulo': 'El título debe tener mínimo 5 caracteres.'}
            )

        if not self.descripcion:
            raise ValidationError(
                {'descripcion': 'La descripción es obligatoria.'}
            )

        if len(self.descripcion.strip()) < 20:
            raise ValidationError(
                {'descripcion': 'La descripción debe tener mínimo 20 caracteres.'}
            )

        if not self.tipo_reporte:
            raise ValidationError(
                {'tipo_reporte': 'Seleccione un tipo de reporte.'}
            )

    def __str__(self):
        return f"{self.titulo} - {self.fecha_registro}"