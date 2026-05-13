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