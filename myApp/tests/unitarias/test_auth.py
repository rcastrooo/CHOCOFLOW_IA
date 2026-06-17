from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import Usuario


class AuthTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="10001",
            email="admin@test.com",
            password="Admin123"
        )

        self.usuario = Usuario.objects.create(
            nombre="Administrador",
            email="admin@test.com",
            direccion="Bogota",
            contrasena="Admin123",
            rol="Administrador",
            estado="Activo"
        )

    # ==========================
    # LOGIN
    # ==========================

    def test_login_correcto(self):

        response = self.client.post(
            reverse("login"),
            {
                "username": "admin@test.com",
                "password": "Admin123"
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

    def test_login_correo_vacio(self):

        self.client.post(
            reverse("login"),
            {
                "username": "",
                "password": "Admin123"
            }
        )

        self.assertFalse(
            "_auth_user_id" in self.client.session
        )

    def test_login_password_vacio(self):

        self.client.post(
            reverse("login"),
            {
                "username": "admin@test.com",
                "password": ""
            }
        )

        self.assertFalse(
            "_auth_user_id" in self.client.session
        )

    def test_login_correo_invalido(self):

        self.client.post(
            reverse("login"),
            {
                "username": "correo-invalido",
                "password": "Admin123"
            }
        )

        self.assertFalse(
            "_auth_user_id" in self.client.session
        )

    def test_login_credenciales_invalidas(self):

        self.client.post(
            reverse("login"),
            {
                "username": "admin@test.com",
                "password": "Incorrecta123"
            }
        )

        self.assertFalse(
            "_auth_user_id" in self.client.session
        )

    # ==========================
    # REGISTRO
    # ==========================

    def test_registro_correcto(self):

        self.client.post(
            reverse("registro"),
            {
                "identificacion": "20002",
                "nombre": "Juan Perez",
                "correo": "juan@test.com",
                "telefono": "3001234567",
                "direccion": "Bogota",
                "password": "Password123",
                "rol": "Administrador",
                "estado": "Activo"
            }
        )

        self.assertEqual(
            Usuario.objects.count(),
            2
        )

    def test_no_permitir_identificacion_duplicada(self):

        self.client.post(
            reverse("registro"),
            {
                "identificacion": "10001",
                "nombre": "Juan Perez",
                "correo": "nuevo@test.com",
                "telefono": "3001234567",
                "direccion": "Bogota",
                "password": "Password123",
                "rol": "Administrador",
                "estado": "Activo"
            }
        )

        self.assertEqual(
            Usuario.objects.count(),
            1
        )

    def test_no_permitir_correo_duplicado(self):

        self.client.post(
            reverse("registro"),
            {
                "identificacion": "20002",
                "nombre": "Juan Perez",
                "correo": "admin@test.com",
                "telefono": "3001234567",
                "direccion": "Bogota",
                "password": "Password123",
                "rol": "Administrador",
                "estado": "Activo"
            }
        )

        self.assertEqual(
            Usuario.objects.count(),
            1
        )

    def test_no_permitir_password_corta(self):

        self.client.post(
            reverse("registro"),
            {
                "identificacion": "20002",
                "nombre": "Juan Perez",
                "correo": "juan@test.com",
                "telefono": "3001234567",
                "direccion": "Bogota",
                "password": "Abc12",
                "rol": "Administrador",
                "estado": "Activo"
            }
        )

        self.assertEqual(
            Usuario.objects.count(),
            1
        )

    def test_no_permitir_password_sin_mayuscula(self):

        self.client.post(
            reverse("registro"),
            {
                "identificacion": "20002",
                "nombre": "Juan Perez",
                "correo": "juan@test.com",
                "telefono": "3001234567",
                "direccion": "Bogota",
                "password": "password123",
                "rol": "Administrador",
                "estado": "Activo"
            }
        )

        self.assertEqual(
            Usuario.objects.count(),
            1
        )

    def test_no_permitir_password_sin_numero(self):

        self.client.post(
            reverse("registro"),
            {
                "identificacion": "20002",
                "nombre": "Juan Perez",
                "correo": "juan@test.com",
                "telefono": "3001234567",
                "direccion": "Bogota",
                "password": "PasswordABC",
                "rol": "Administrador",
                "estado": "Activo"
            }
        )

        self.assertEqual(
            Usuario.objects.count(),
            1
        )

    def test_no_permitir_nombre_con_numeros(self):

        self.client.post(
            reverse("registro"),
            {
                "identificacion": "20002",
                "nombre": "Juan123",
                "correo": "juan@test.com",
                "telefono": "3001234567",
                "direccion": "Bogota",
                "password": "Password123",
                "rol": "Administrador",
                "estado": "Activo"
            }
        )

        self.assertEqual(
            Usuario.objects.count(),
            1
        )

    def test_no_permitir_supervisor_sin_turno(self):

        self.client.post(
            reverse("registro"),
            {
                "identificacion": "30003",
                "nombre": "Supervisor Test",
                "correo": "super@test.com",
                "telefono": "3001234567",
                "direccion": "Bogota",
                "password": "Password123",
                "rol": "Supervisor",
                "estado": "Activo",
                "turno": ""
            }
        )

        self.assertEqual(
            Usuario.objects.count(),
            1
        )