from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import (
    Usuario,
    Empleado,
    Produccion,
    Exportacion,
    Lote,
    Bitacora,
    Solicitud,
    Turno,
)


class DashboardAdminTests(TestCase):

    def setUp(self):

        # Usuario Django
        self.user = User.objects.create_user(
            username="admin",
            password="123456"
        )

        self.client.login(
            username="admin",
            password="123456"
        )

        # Perfil administrador
        self.admin = Usuario.objects.create(
            nombre="Administrador",
            email="admin@test.com",
            direccion="Bogota",
            contrasena="123456",
            rol="Administrador",
            estado="Activo"
        )

        session = self.client.session
        session["usuario_id"] = self.admin.id
        session["rol"] = "Administrador"
        session.save()

        # Turnos
        self.turno_manana = Turno.objects.create(
            horario="Mañana 6:00am - 2:00pm",
            activo=True
        )

        self.turno_tarde = Turno.objects.create(
            horario="Tarde 2:00pm - 10:00pm",
            activo=True
        )

    def test_dashboard_carga_correctamente(self):

        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_dashboard_requiere_login(self):

        self.client.logout()

        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(
            response.status_code,
            302
        )

    def test_contar_usuarios(self):

        Usuario.objects.create(
            nombre="Supervisor",
            email="super@test.com",
            direccion="Bogota",
            contrasena="123456",
            rol="Supervisor",
            estado="Activo"
        )

        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(
            response.context["total_usuarios"],
            2
        )

    def test_contar_empleados_activos_y_suspendidos(self):

        Empleado.objects.create(
            cedula="111",
            nombre="Empleado Activo",
            email="activo@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.admin
        )

        Empleado.objects.create(
            cedula="222",
            nombre="Empleado Suspendido",
            email="suspendido@test.com",
            direccion="Bogota",
            estado="Suspendido",
            creado_por=self.admin
        )

        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(
            response.context["total_empleados"],
            2
        )

        self.assertEqual(
            response.context["empleados_activos"],
            1
        )

        self.assertEqual(
            response.context["empleados_suspendidos"],
            1
        )

    def test_contar_producciones_exportaciones_lotes(self):

        empleado = Empleado.objects.create(
            cedula="333",
            nombre="Juan",
            email="juan@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.admin
        )

        produccion = Produccion.objects.create(
            producto="Chocolate Premium",
            ingredientes="Cacao",
            cantidad_requerida="100",
            fecha_entrega=date.today() + timedelta(days=10),
            fecha_limite=date.today() + timedelta(days=5),
            estado="En Proceso",
            empleado_responsable=empleado,
            creado_por=self.admin
        )

        lote = Lote.objects.create(
            codigo_lote="CH-001",
            cantidad="100",
            fecha_produccion=produccion.fecha_entrega,
            fecha_vencimiento=produccion.fecha_entrega + timedelta(days=180),
            produccion=produccion
        )

        Exportacion.objects.create(
            destino="Mexico",
            pais="Mexico",
            fecha_envio=date.today(),
            fecha_entrega=date.today() + timedelta(days=5),
            estado="Pendiente",
            produccion=produccion,
            lote=lote
        )

        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(
            response.context["total_producciones"],
            1
        )

        self.assertEqual(
            response.context["producciones_proceso"],
            1
        )

        self.assertEqual(
            response.context["total_exportaciones"],
            1
        )

        self.assertEqual(
            response.context["exportaciones_pendientes"],
            1
        )

        self.assertEqual(
            response.context["total_lotes"],
            1
        )

    def test_contar_bitacoras_y_solicitudes_pendientes(self):

        empleado = Empleado.objects.create(
            cedula="444",
            nombre="Carlos",
            email="carlos@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.admin
        )

        Bitacora.objects.create(
            titulo="Reporte Diario",
            descripcion="Prueba",
            tipo_reporte="Diario",
            estado="Enviado",
            supervisor=self.admin
        )

        Solicitud.objects.create(
            empleado=empleado,
            turno_actual=self.turno_manana,
            turno_solicitado=self.turno_tarde,
            motivo="Cambio",
            estado="Pendiente"
        )

        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(
            response.context["bitacoras_pendientes"],
            1
        )

        self.assertEqual(
            response.context["solicitudes_pendientes"],
            1
        )