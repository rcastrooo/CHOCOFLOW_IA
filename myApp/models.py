from django.db import models
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

    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True, max_length=255)
    telefono = models.IntegerField()
    direccion = models.CharField(max_length=255)
    contrasena = models.CharField(max_length=255)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)

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
    telefono = models.IntegerField()
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

    fecha = models.DateField()
    horario = models.CharField(max_length=50, choices=HORARIO_CHOICES)

    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column='creado_por'
    )

    def __str__(self):
        return f"{self.fecha} - {self.horario}"


# -------------------------
# Emp_Turno
# -------------------------
class EmpTurno(models.Model):

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, db_column='empleado_id')
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, db_column='turno_id')

    def __str__(self):
        return f"{self.empleado} - {self.turno}"

# -------------------------
# Asignacion
# -------------------------
class Asignacion(models.Model):
    tarea = models.CharField(max_length=255)
    fecha_asignacion = models.DateField()

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, db_column='empleado_id')
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, db_column='turno_id')
    asignado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='asignado_por')

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

    producto = models.CharField(max_length=255)
    ingredientes = models.CharField(max_length=255)
    cantidad_planificada = models.CharField(max_length=255)
    cantidad_producida = models.CharField(max_length=255)
    fecha_entrega = models.DateField()
    fecha_limite = models.DateField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
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
    pais = models.CharField(max_length=255)
    fecha_envio = models.DateField()
    fecha_entrega = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)

    creado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='creado_por')

    def __str__(self):
        return f"{self.destino} - {self.estado}"

# -------------------------
# Lote
# -------------------------
class Lote(models.Model):
    codigo_lote = models.CharField(max_length=100, unique=True)
    cantidad = models.IntegerField()
    fecha_produccion = models.DateField()
    fecha_vencimiento = models.DateField()
    

    produccion = models.ForeignKey(Produccion, on_delete=models.CASCADE, db_column='produccion_id')
    exportacion = models.ForeignKey(Exportacion, on_delete=models.CASCADE, db_column='exportacion_id')
    
    def __str__(self):
        return self.codigo_lote
    
# -------------------------
# BitacoraProduccion
# -------------------------
# Modelo que permite al supervisor registrar novedades y seguimiento
# de los procesos de producción sin modificar el modelo Produccion directamente.
class BitacoraProduccion(models.Model):

    # Opciones de tipo de novedad que el supervisor puede registrar
    TIPO_CHOICES = [
        ('Observación general', 'Observación general'),     # Nota informativa sin urgencia
        ('Incidencia en proceso', 'Incidencia en proceso'), # Problema o fallo durante la producción
        ('Ajuste de cantidad', 'Ajuste de cantidad'),       # Cambio en cantidad planificada o producida
        ('Cambio de estado', 'Cambio de estado'),           # Modificación en el estado del proceso
        ('Nota de calidad', 'Nota de calidad'),             # Observación relacionada con estándares de calidad
    ]

    # Tipo de novedad seleccionado de las opciones anteriores
    tipo_novedad = models.CharField(max_length=50, choices=TIPO_CHOICES)

    # Descripción detallada de la novedad o seguimiento registrado
    descripcion = models.TextField()

    # Fecha y hora en que se creó la entrada; se llena automáticamente al guardar
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Relación con el proceso de producción al que pertenece esta entrada.
    # Si se elimina la producción, se eliminan también todas sus entradas de bitácora.
    # related_name='bitacora' permite acceder desde Produccion con: produccion.bitacora.all()
    produccion = models.ForeignKey(
        Produccion,
        on_delete=models.CASCADE,
        db_column='produccion_id',
        related_name='bitacora'
    )

    # Supervisor que registró la entrada.
    # Si se elimina el usuario, se eliminan también sus entradas.
    # related_name='bitacora_entries' permite acceder desde Usuario con: usuario.bitacora_entries.all()
    registrado_por = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column='registrado_por',
        related_name='bitacora_entries'
    )

    class Meta:
        # Las entradas se ordenan de más reciente a más antigua por defecto
        ordering = ['-fecha_registro']

        # Nombres legibles para el panel de administración de Django
        verbose_name = 'Entrada de bitácora'
        verbose_name_plural = 'Bitácora de producción'

    # Representación en texto del objeto: muestra producción, tipo y fecha de la entrada
    def __str__(self):
        return f"{self.produccion} - {self.tipo_novedad} - {self.fecha_registro:%Y-%m-%d %H:%M}"