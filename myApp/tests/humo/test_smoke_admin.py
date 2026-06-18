from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import Usuario


class SmokeAdminTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="admin",
            password="123456"
        )

        self.admin = Usuario.objects.create(
            nombre="Administrador Test",
            email="admin@test.com",
            direccion="Bogota",
            contrasena="123456",
            rol="Administrador",
            estado="Activo"
        )

        self.client.login(
            username="admin",
            password="123456"
        )

        session = self.client.session
        session["usuario_id"] = self.admin.id
        session["rol"] = "Administrador"
        session.save()

    def test_dashboard_carga(self):

        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(response.status_code, 200)

    def test_empleados_carga(self):

        response = self.client.get(
            reverse("empleados")
        )

        self.assertEqual(response.status_code, 200)

    def test_turnos_carga(self):

        response = self.client.get(
            reverse("turnos")
        )

        self.assertEqual(response.status_code, 200)

    def test_rotacion_turnos_carga(self):

        response = self.client.get(
            reverse("rotacion_turnos")
        )

        self.assertEqual(response.status_code, 200)

    def test_solicitudes_carga(self):

        response = self.client.get(
            reverse("solicitudes")
        )

        self.assertEqual(response.status_code, 200)

    def test_asignaciones_carga(self):

        response = self.client.get(
            reverse("asignaciones")
        )

        self.assertEqual(response.status_code, 200)

    def test_producciones_carga(self):

        response = self.client.get(
            reverse("producciones")
        )

        self.assertEqual(response.status_code, 200)

    def test_lotes_carga(self):

        response = self.client.get(
            reverse("gestionar_lotes")
        )

        self.assertEqual(response.status_code, 200)

    def test_exportaciones_carga(self):

        response = self.client.get(
            reverse("gestionar_exportaciones")
        )

        self.assertEqual(response.status_code, 200)

    def test_bitacoras_admin_carga(self):

        response = self.client.get(
            reverse("listar_bitacoras")
        )

        self.assertEqual(response.status_code, 200)

    def test_correos_carga(self):

        response = self.client.get(
            reverse("correos_vista")
        )

        self.assertEqual(response.status_code, 200)