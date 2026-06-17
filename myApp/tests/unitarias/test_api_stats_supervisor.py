from datetime import date, timedelta
from django.utils import timezone

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import (
    Usuario,
    Empleado,
    Turno,
    RotacionTurno,
    Asignacion,
    Produccion,
    Lote,
    Exportacion,
    Bitacora
)


class ApiStatsSupervisorTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="supervisor",
            password="123456"
        )

        self.client.login(
            username="supervisor",
            password="123456"
        )

        self.supervisor = Usuario.objects.create(
            nombre="Supervisor Test",
            email="supervisor@test.com",
            direccion="Bogota",
            contrasena="123456",
            rol="Supervisor",
            turno="Mañana 6:00am - 2:00pm",
            estado="Activo"
        )

        session = self.client.session
        session["usuario_id"] = self.supervisor.id
        session["rol"] = "Supervisor"
        session.save()

        self.turno = Turno.objects.create(
            horario="Mañana 6:00am - 2:00pm"
        )

        self.empleado_turno = Empleado.objects.create(
            cedula="111",
            nombre="Empleado Turno",
            email="empleado1@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.supervisor
        )

        self.empleado_sin_turno = Empleado.objects.create(
            cedula="222",
            nombre="Empleado Sin Turno",
            email="empleado2@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.supervisor
        )

        hoy = timezone.now().date()

        RotacionTurno.objects.create(
            empleado=self.empleado_turno,
            turno=self.turno,
            fecha_inicio=hoy - timedelta(days=hoy.weekday()),
            fecha_fin=(hoy - timedelta(days=hoy.weekday())) + timedelta(days=6),
            semana=hoy.isocalendar()[1]
        )

        self.produccion = Produccion.objects.create(
            producto="Chocolate",
            ingredientes="Cacao",
            cantidad_requerida="100",
            fecha_entrega=hoy + timedelta(days=5),
            fecha_limite=hoy + timedelta(days=3),
            estado="En Proceso",
            empleado_responsable=self.empleado_turno,
            creado_por=self.supervisor
        )

        self.lote = Lote.objects.create(
            codigo_lote="CH-001",
            cantidad="100",
            unidad="Kilogramos",
            fecha_produccion=hoy,
            fecha_vencimiento=hoy + timedelta(days=365),
            produccion=self.produccion
        )

        Exportacion.objects.create(
            destino="Mexico",
            pais="Mexico",
            fecha_envio=hoy,
            fecha_entrega=hoy + timedelta(days=10),
            estado="Pendiente",
            produccion=self.produccion,
            lote=self.lote
        )

        Exportacion.objects.create(
            destino="Chile",
            pais="Chile",
            fecha_envio=hoy,
            fecha_entrega=hoy + timedelta(days=10),
            estado="Enviado",
            produccion=self.produccion,
            lote=self.lote
        )

        Asignacion.objects.create(
            tarea="Empacar",
            fecha_asignacion=hoy,
            empleado=self.empleado_turno,
            turno=self.turno,
            asignado_por=self.supervisor
        )

        bitacora1 = Bitacora.objects.create(
            titulo="Bitacora Borrador",
            descripcion="Prueba",
            tipo_reporte="Diario",
            estado="Borrador",
            supervisor=self.supervisor,
            produccion=self.produccion
        )

        bitacora2 = Bitacora.objects.create(
            titulo="Bitacora Enviada",
            descripcion="Prueba",
            tipo_reporte="Diario",
            estado="Enviado",
            supervisor=self.supervisor,
            produccion=self.produccion
        )

        # Forzar fecha actual para coincidir con el filtro de la vista
        Bitacora.objects.filter(id=bitacora1.id).update(
            fecha_registro=hoy
        )

        Bitacora.objects.filter(id=bitacora2.id).update(
            fecha_registro=hoy
        )
    def test_api_stats_supervisor_responde_200(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_api_stats_supervisor_retorna_json(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        self.assertEqual(
            response["Content-Type"],
            "application/json"
        )

    def test_total_empleados_turno(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        data = response.json()

        self.assertEqual(
            data["total_empleados"],
            1
        )

    def test_empleados_activos_turno(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        data = response.json()

        self.assertEqual(
            data["empleados_activos"],
            1
        )

    def test_asignaciones_hoy(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        data = response.json()

        self.assertEqual(
            data["asignaciones_hoy"],
            1
        )

    def test_empleados_sin_turno(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        data = response.json()

        self.assertEqual(
            data["sin_turno"],
            1
        )

    def test_lotes_totales(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        data = response.json()

        self.assertEqual(
            data["lotes_totales"],
            1
        )

    def test_exportaciones_pendientes(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        data = response.json()

        self.assertEqual(
            data["exportaciones_pendientes"],
            1
        )

    def test_exportaciones_enviadas(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        data = response.json()

        self.assertEqual(
            data["exportaciones_enviadas"],
            1
        )

    def test_bitacoras_hoy(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        data = response.json()

        self.assertEqual(
            data["bitacora_hoy"],
            2
        )

    def test_bitacoras_pendientes(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        data = response.json()

        self.assertEqual(
            data["bitacora_pendientes"],
            1
        )

    def test_bitacoras_enviadas(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        data = response.json()

        self.assertEqual(
            data["bitacora_enviados"],
            1
        )

    def test_nombre_turno(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        data = response.json()

        self.assertEqual(
            data["turno_nombre"],
            "Mañana 6:00am - 2:00pm"
        )