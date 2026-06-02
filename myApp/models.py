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

    nombre    = models.CharField(max_length=100)
    email     = models.EmailField(unique=True, max_length=255)
    telefono  = models.CharField(max_length=10, blank=True, null=True)
    direccion = models.CharField(max_length=255)
    contrasena = models.CharField(max_length=255)
    rol       = models.CharField(max_length=20, choices=ROL_CHOICES)
    estado    = models.CharField(max_length=20, choices=ESTADO_CHOICES)

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

    cedula    = models.CharField(max_length=20, null=True, blank=True)
    nombre    = models.CharField(max_length=100)
    email     = models.EmailField(unique=True, max_length=255)
    telefono  = models.CharField(max_length=10, blank=True, null=True)
    direccion = models.CharField(max_length=255)
    estado    = models.CharField(max_length=20, choices=ESTADO_CHOICES)
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

    # SQL solo tiene: horario, activo
    horario = models.CharField(max_length=50, choices=HORARIO_CHOICES)
    activo  = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.horario}"


# -------------------------
# RotacionTurno
# -------------------------
class RotacionTurno(models.Model):
    ESTADO_CHOICES = [
        ('Asignado', 'Asignado'),
        ('Completado', 'Completado'),
        ('Pendiente', 'Pendiente'),
    ]
    HORARIO_SABADO_CHOICES = [
        ('Mañana 6:00am - 12:00pm', 'Mañana 6:00am - 12:00pm'),
        ('Tarde 12:00pm - 6:00pm', 'Tarde 12:00pm - 6:00pm'),
    ]

    fecha_inicio     = models.DateField()
    fecha_fin        = models.DateField()
    semana           = models.IntegerField()
    estado           = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')
    sabado_asignado  = models.BooleanField(default=False)
    horario_sabado   = models.CharField(max_length=50, choices=HORARIO_SABADO_CHOICES, null=True, blank=True)
    empleado         = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    turno            = models.ForeignKey(Turno, on_delete=models.CASCADE)

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
# Solicitud
# -------------------------
class Solicitud(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Aprobado', 'Aprobado'),
        ('Rechazado', 'Rechazado'),
    ]

    turno_actual      = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='turno_actual')
    turno_solicitado  = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='turno_solicitado')
    motivo            = models.TextField()
    fecha_solicitud   = models.DateField(auto_now_add=True)
    estado            = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')
    empleado          = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    observacion_admin = models.TextField(null=True, blank=True)

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
    TAREA_CHOICES = [
        ('Temperar', 'Temperar'),
        ('Mezclado', 'Mezclado'),
        ('Moldear', 'Moldear'),
        ('Desmoldear', 'Desmoldear'),
        ('Picar', 'Picar'),
        ('Triturado', 'Triturado'),
        ('Molienda', 'Molienda'),
        ('Paletear', 'Paletear'),
        ('Empacar', 'Empacar'),
        ('Sellado', 'Sellado'),
        ('Etiquetado', 'Etiquetado'),
        ('Limpieza General', 'Limpieza General'),
        ('Limpieza de Maquinaria', 'Limpieza de Maquinaria'),
    ]

    tarea             = models.CharField(max_length=255, choices=TAREA_CHOICES)
    descripcion_tarea = models.TextField(null=True, blank=True)
    fecha_asignacion  = models.DateField()
    estado            = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')
    empleado          = models.ForeignKey(Empleado, on_delete=models.CASCADE, db_column='empleado_id')
    turno             = models.ForeignKey(Turno, on_delete=models.CASCADE, db_column='turno_id')
    asignado_por      = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='asignado_por')

    # ✅ Se eliminó clean() y save() con el límite duro.
    # El límite de 2 tareas ahora se maneja en la view del supervisor (duro)
    # y en la view del admin (advertencia con confirmación).

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

    producto           = models.CharField(max_length=255, null=True, blank=True)
    ingredientes       = models.CharField(max_length=255)
    cantidad_requerida = models.CharField(max_length=255, null=True, blank=True)
    fecha_entrega      = models.DateField()
    fecha_limite       = models.DateField()
    estado             = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    empleado_responsable = models.ForeignKey(Empleado, on_delete=models.CASCADE, db_column='empleado_responsable')
    creado_por         = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='creado_por')

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
    
    destino              = models.CharField(max_length=255)
    pais                 = models.CharField(max_length=255, default='Sin producto')
    fecha_envio          = models.DateField()
    fecha_entrega        = models.DateField()
    estado               = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    produccion           = models.ForeignKey(Produccion, on_delete=models.CASCADE, db_column='produccion_id', null=True, blank=True)
    nombre_producto      = models.CharField(max_length=100, null=True, blank=True)  # era 'producto' en versión anterior
    cantidad_cajas       = models.IntegerField(null=True, blank=True)
    unidades_por_caja    = models.IntegerField(null=True, blank=True)
    peso_caja            = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    peso_total           = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    empresa_exportadora  = models.CharField(max_length=100, null=True, blank=True)
    numero_contenedor    = models.CharField(max_length=100, null=True, blank=True)
    observaciones        = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.destino} - {self.estado}"


# -------------------------
# Lote
# -------------------------
class Lote(models.Model):
    UNIDAD_CHOICES = [
        ('Kilogramos', 'Kilogramos'),
        ('Gramos', 'Gramos'),
    ]

    codigo_lote      = models.CharField(max_length=100, unique=True)
    origen_cacao     = models.CharField(max_length=100, null=True, blank=True)
    cantidad         = models.CharField(max_length=255)
    unidad           = models.CharField(max_length=20, choices=UNIDAD_CHOICES, null=True, blank=True)
    fecha_produccion  = models.DateField()
    fecha_vencimiento = models.DateField()
    nombre_producto  = models.CharField(max_length=100, null=True, blank=True)
    produccion       = models.ForeignKey(Produccion, on_delete=models.CASCADE, db_column='produccion_id')
    exportacion      = models.ForeignKey(Exportacion, on_delete=models.CASCADE, db_column='exportacion_id')

    def __str__(self):
        return self.codigo_lote


# -------------------------
# Bitacora
# -------------------------
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
    supervisor          = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='supervisor_id', related_name='bitacoras_creadas')
    produccion          = models.ForeignKey(Produccion, on_delete=models.CASCADE, db_column='produccion_id', null=True, blank=True)
    fecha_revision      = models.DateField(null=True, blank=True)
    observacion_admin   = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.titulo} - {self.fecha_registro}"