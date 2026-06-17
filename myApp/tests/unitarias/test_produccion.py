from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import (
    Usuario,
    Empleado,
    Produccion
)


class ProduccionTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="admin",
            password="123456"
        )

        self.client.login(
            username="admin",
            password="123456"
        )

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

        self.empleado = Empleado.objects.create(
            cedula="123456789",
            nombre="Juan Perez",
            email="juan@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.admin
        )

        self.fecha_entrega = date.today() + timedelta(days=5)
        self.fecha_limite = date.today() + timedelta(days=10)

    def test_crear_produccion_correctamente(self):

        self.client.post(
            reverse("guardar_produccion"),
            {
                "producto": "Chocolate Premium",
                "ingredientes": "Cacao, Azucar",
                "cantidad_requerida": "100",
                "fecha_entrega": self.fecha_entrega.isoformat(),
                "fecha_limite": self.fecha_limite.isoformat(),
                "estado": "Pendiente",
                "empleado_responsable": self.empleado.id
            }
        )

        self.assertEqual(
            Produccion.objects.count(),
            1
        )

    def test_no_permitir_producto_vacio(self):

        self.client.post(
            reverse("guardar_produccion"),
            {
                "producto": "",
                "ingredientes": "Cacao",
                "cantidad_requerida": "100",
                "fecha_entrega": self.fecha_entrega.isoformat(),
                "fecha_limite": self.fecha_limite.isoformat(),
                "estado": "Pendiente",
                "empleado_responsable": self.empleado.id
            }
        )

        self.assertEqual(
            Produccion.objects.count(),
            0
        )

    def test_no_permitir_ingredientes_vacios(self):

        self.client.post(
            reverse("guardar_produccion"),
            {
                "producto": "Chocolate",
                "ingredientes": "",
                "cantidad_requerida": "100",
                "fecha_entrega": self.fecha_entrega.isoformat(),
                "fecha_limite": self.fecha_limite.isoformat(),
                "estado": "Pendiente",
                "empleado_responsable": self.empleado.id
            }
        )

        self.assertEqual(
            Produccion.objects.count(),
            0
        )

    def test_no_permitir_fecha_limite_mayor_entrega(self):
        """
        La vista valida:
        fecha_limite < fecha_entrega
        """

        self.client.post(
            reverse("guardar_produccion"),
            {
                "producto": "Chocolate",
                "ingredientes": "Cacao",
                "cantidad_requerida": "100",
                "fecha_entrega": "2026-06-20",
                "fecha_limite": "2026-06-10",
                "estado": "Pendiente",
                "empleado_responsable": self.empleado.id
            }
        )

        self.assertEqual(
            Produccion.objects.count(),
            0
        )

    def test_cancelar_produccion(self):

        produccion = Produccion.objects.create(
            producto="Chocolate",
            ingredientes="Cacao",
            cantidad_requerida="100",
            fecha_entrega=self.fecha_entrega,
            fecha_limite=self.fecha_limite,
            estado="Pendiente",
            empleado_responsable=self.empleado,
            creado_por=self.admin
        )

        self.client.get(
            reverse(
                "inactivar_produccion",
                args=[produccion.id]
            )
        )

        produccion.refresh_from_db()

        self.assertEqual(
            produccion.estado,
            "Cancelado"
        )

    def test_no_cancelar_produccion_finalizada(self):

        produccion = Produccion.objects.create(
            producto="Chocolate",
            ingredientes="Cacao",
            cantidad_requerida="100",
            fecha_entrega=self.fecha_entrega,
            fecha_limite=self.fecha_limite,
            estado="Finalizado",
            empleado_responsable=self.empleado,
            creado_por=self.admin
        )

        self.client.get(
            reverse(
                "inactivar_produccion",
                args=[produccion.id]
            )
        )

        produccion.refresh_from_db()

        self.assertEqual(
            produccion.estado,
            "Finalizado"
        )