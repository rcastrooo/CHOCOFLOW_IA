from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import Usuario


class SmokeSupervisorTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="supervisor",
            password="123456"
        )

        self.supervisor = Usuario.objects.create(
            nombre="Supervisor Test",
            email="supervisor@test.com",
            direccion="Bogota",
            contrasena="123456",
            rol="Supervisor",
            estado="Activo"
        )

        self.client.login(
            username="supervisor",
            password="123456"
        )

        session = self.client.session
        session["usuario_id"] = self.supervisor.id
        session["rol"] = "Supervisor"
        session.save()

    # ==========================
    # DASHBOARD SUPERVISOR
    # ==========================

    def test_dashboard_supervisor_carga(self):

        response = self.client.get(
            reverse("dashboard_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_api_stats_supervisor_carga(self):

        response = self.client.get(
            reverse("api_stats_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    # ==========================
    # EMPLEADOS
    # ==========================

    def test_empleados_supervisor_carga(self):

        response = self.client.get(
            reverse("empleados_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    # ==========================
    # TURNOS
    # ==========================

    def test_turnos_supervisor_carga(self):

        response = self.client.get(
            reverse("turnos_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    # ==========================
    # ASIGNACIONES
    # ==========================

    def test_asignaciones_supervisor_carga(self):

        response = self.client.get(
            reverse("asignaciones_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    # ==========================
    # PRODUCCIONES
    # ==========================

    def test_producciones_supervisor_carga(self):

        response = self.client.get(
            reverse("producciones_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    # ==========================
    # EXPORTACIONES
    # ==========================

    def test_exportaciones_supervisor_carga(self):

        response = self.client.get(
            reverse("exportaciones_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    # ==========================
    # LOTES
    # ==========================

    def test_lotes_supervisor_carga(self):

        response = self.client.get(
            reverse("lotes_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    # ==========================
    # BITÁCORA
    # ==========================

    def test_bitacora_supervisor_carga(self):

        response = self.client.get(
            reverse("bitacora_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_listar_bitacoras_supervisor_carga(self):

        response = self.client.get(
            reverse("listar_bitacoras_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )