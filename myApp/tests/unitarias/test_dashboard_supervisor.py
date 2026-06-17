from datetime import date, timedelta

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


class DashboardSupervisorTests(TestCase):

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

        self.empleado_activo = Empleado.objects.create(
            cedula="111",
            nombre="Empleado Activo",
            email="activo@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.supervisor
        )

        self.empleado_suspendido = Empleado.objects.create(
            cedula="222",
            nombre="Empleado Suspendido",
            email="suspendido@test.com",
            direccion="Bogota",
            estado="Suspendido",
            creado_por=self.supervisor
        )

        hoy = date.today()
        lunes = hoy - timedelta(days=hoy.weekday())
        domingo = lunes + timedelta(days=6)

        RotacionTurno.objects.create(
            empleado=self.empleado_activo,
            turno=self.turno,
            fecha_inicio=lunes,
            fecha_fin=domingo,
            semana=hoy.isocalendar()[1]
        )

        self.produccion_proceso = Produccion.objects.create(
            producto="Chocolate A",
            ingredientes="Cacao",
            cantidad_requerida="100",
            fecha_entrega=hoy + timedelta(days=5),
            fecha_limite=hoy + timedelta(days=3),
            estado="En Proceso",
            empleado_responsable=self.empleado_activo,
            creado_por=self.supervisor
        )

        self.produccion_pendiente = Produccion.objects.create(
            producto="Chocolate B",
            ingredientes="Cacao",
            cantidad_requerida="50",
            fecha_entrega=hoy + timedelta(days=8),
            fecha_limite=hoy + timedelta(days=4),
            estado="Pendiente",
            empleado_responsable=self.empleado_activo,
            creado_por=self.supervisor
        )

        self.lote = Lote.objects.create(
            codigo_lote="CH-001",
            cantidad="100",
            unidad="Kilogramos",
            fecha_produccion=hoy,
            fecha_vencimiento=hoy + timedelta(days=365),
            produccion=self.produccion_proceso
        )

        Exportacion.objects.create(
            destino="Mexico",
            pais="Mexico",
            fecha_envio=hoy,
            fecha_entrega=hoy + timedelta(days=10),
            estado="Pendiente",
            produccion=self.produccion_proceso,
            lote=self.lote
        )

        Asignacion.objects.create(
            tarea="Empacar",
            fecha_asignacion=hoy,
            empleado=self.empleado_activo,
            turno=self.turno,
            asignado_por=self.supervisor
        )

        Bitacora.objects.create(
            titulo="Bitacora Test",
            descripcion="Prueba",
            tipo_reporte="Diario",
            estado="Borrador",
            supervisor=self.supervisor,
            produccion=self.produccion_proceso
        )

    def test_dashboard_supervisor_responde_200(self):

        response = self.client.get(
            reverse("dashboard_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_dashboard_supervisor_usa_template_correcto(self):

        response = self.client.get(
            reverse("dashboard_supervisor")
        )

        self.assertTemplateUsed(
            response,
            "dashboard_supervisor.html"
        )

    def test_dashboard_supervisor_muestra_turno(self):

        response = self.client.get(
            reverse("dashboard_supervisor")
        )

        self.assertEqual(
            response.context["mi_turno"],
            "Mañana 6:00am - 2:00pm"
        )

    def test_dashboard_supervisor_cuenta_empleados_activos(self):

        response = self.client.get(
            reverse("dashboard_supervisor")
        )

        self.assertEqual(
            response.context["empleados_activos"],
            1
        )

    def test_dashboard_supervisor_cuenta_producciones(self):

        response = self.client.get(
            reverse("dashboard_supervisor")
        )

        self.assertEqual(
            response.context["producciones_proceso"],
            1
        )

        self.assertEqual(
            response.context["producciones_pendientes"],
            1
        )

    def test_dashboard_supervisor_cuenta_recursos(self):

        response = self.client.get(
            reverse("dashboard_supervisor")
        )

        self.assertEqual(
            response.context["exportaciones_pendientes"],
            1
        )

        self.assertEqual(
            response.context["total_lotes"],
            1
        )

        self.assertEqual(
            response.context["total_asignaciones"],
            1
        )

        self.assertEqual(
            response.context["total_bitacora"],
            1
        )