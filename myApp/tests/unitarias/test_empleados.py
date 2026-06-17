from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import Usuario, Empleado


class EmpleadoTests(TestCase):

    def setUp(self):
        """
        Se ejecuta antes de cada prueba.
        """

        # Usuario de Django para pasar @login_required
        self.user = User.objects.create_user(
            username="admin",
            password="123456"
        )

        self.client.login(
            username="admin",
            password="123456"
        )

        # Usuario de tu sistema
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
        session.save()

    def test_crear_empleado_correctamente(self):

        response = self.client.post(
            reverse("guardar_empleado"),
            {
                "cedula": "123456789",
                "nombre": "Juan Perez",
                "email": "juan@test.com",
                "telefono": "3001234567",
                "direccion": "Bogota",
                "estado": "Activo"
            }
        )

        self.assertEqual(
            Empleado.objects.count(),
            1
        )

        empleado = Empleado.objects.first()

        self.assertEqual(
            empleado.nombre,
            "Juan Perez"
        )

    def test_no_permitir_correo_duplicado(self):

        Empleado.objects.create(
            cedula="111111111",
            nombre="Pedro",
            email="correo@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.admin
        )

        self.client.post(
            reverse("guardar_empleado"),
            {
                "cedula": "222222222",
                "nombre": "Juan",
                "email": "correo@test.com",
                "telefono": "3001234567",
                "direccion": "Bogota",
                "estado": "Activo"
            }
        )

        self.assertEqual(
            Empleado.objects.count(),
            1
        )

    def test_no_permitir_cedula_duplicada(self):

        Empleado.objects.create(
            cedula="123456789",
            nombre="Pedro",
            email="pedro@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.admin
        )

        self.client.post(
            reverse("guardar_empleado"),
            {
                "cedula": "123456789",
                "nombre": "Juan",
                "email": "juan@test.com",
                "telefono": "3001234567",
                "direccion": "Bogota",
                "estado": "Activo"
            }
        )

        self.assertEqual(
            Empleado.objects.count(),
            1
        )