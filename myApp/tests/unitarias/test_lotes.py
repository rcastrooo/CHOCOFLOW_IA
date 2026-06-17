from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import (
    Usuario,
    Empleado,
    Produccion,
    Lote
)


class LoteTests(TestCase):

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

        self.fecha_produccion = date.today() + timedelta(days=10)

        self.produccion = Produccion.objects.create(
            producto="Chocolate Premium",
            ingredientes="Cacao",
            cantidad_requerida="100",
            fecha_entrega=self.fecha_produccion,
            fecha_limite=date.today() + timedelta(days=5),
            estado="Pendiente",
            empleado_responsable=self.empleado,
            creado_por=self.admin
        )

    def test_crear_lote_correctamente(self):

        self.client.post(
            reverse("guardar_lote"),
            {
                "codigo_lote": "CH-001",
                "origen_cacao": "Tumaco",
                "cantidad": "500",
                "unidad": "Kilogramos",
                "nombre_producto": "Chocolate Premium",
                "fecha_produccion": self.fecha_produccion.isoformat(),
                "fecha_vencimiento": (
                    self.fecha_produccion + timedelta(days=365)
                ).isoformat(),
                "produccion_id": self.produccion.id
            }
        )

        self.assertEqual(
            Lote.objects.count(),
            1
        )

    def test_no_permitir_codigo_duplicado(self):

        Lote.objects.create(
            codigo_lote="CH-001",
            cantidad="500",
            fecha_produccion=self.fecha_produccion,
            fecha_vencimiento=self.fecha_produccion + timedelta(days=365),
            produccion=self.produccion
        )

        self.client.post(
            reverse("guardar_lote"),
            {
                "codigo_lote": "CH-001",
                "cantidad": "600",
                "fecha_produccion": self.fecha_produccion.isoformat(),
                "fecha_vencimiento": (
                    self.fecha_produccion + timedelta(days=365)
                ).isoformat(),
                "produccion_id": self.produccion.id
            }
        )

        self.assertEqual(
            Lote.objects.count(),
            1
        )

    def test_no_permitir_codigo_invalido(self):

        self.client.post(
            reverse("guardar_lote"),
            {
                "codigo_lote": "CH001",
                "cantidad": "500",
                "fecha_produccion": self.fecha_produccion.isoformat(),
                "fecha_vencimiento": (
                    self.fecha_produccion + timedelta(days=365)
                ).isoformat(),
                "produccion_id": self.produccion.id
            }
        )

        self.assertEqual(
            Lote.objects.count(),
            0
        )

    def test_no_permitir_cantidad_no_numerica(self):

        self.client.post(
            reverse("guardar_lote"),
            {
                "codigo_lote": "CH-001",
                "cantidad": "ABC",
                "fecha_produccion": self.fecha_produccion.isoformat(),
                "fecha_vencimiento": (
                    self.fecha_produccion + timedelta(days=365)
                ).isoformat(),
                "produccion_id": self.produccion.id
            }
        )

        self.assertEqual(
            Lote.objects.count(),
            0
        )

    def test_no_permitir_fecha_vencimiento_anterior(self):

        self.client.post(
            reverse("guardar_lote"),
            {
                "codigo_lote": "CH-001",
                "cantidad": "500",
                "fecha_produccion": self.fecha_produccion.isoformat(),
                "fecha_vencimiento": (
                    self.fecha_produccion - timedelta(days=1)
                ).isoformat(),
                "produccion_id": self.produccion.id
            }
        )

        self.assertEqual(
            Lote.objects.count(),
            0
        )

    def test_no_permitir_fecha_produccion_distinta(self):

        self.client.post(
            reverse("guardar_lote"),
            {
                "codigo_lote": "CH-001",
                "cantidad": "500",
                "fecha_produccion": (
                    self.fecha_produccion + timedelta(days=1)
                ).isoformat(),
                "fecha_vencimiento": (
                    self.fecha_produccion + timedelta(days=365)
                ).isoformat(),
                "produccion_id": self.produccion.id
            }
        )

        self.assertEqual(
            Lote.objects.count(),
            0
        )

    def test_eliminar_lote(self):

        lote = Lote.objects.create(
            codigo_lote="CH-001",
            cantidad="500",
            fecha_produccion=self.fecha_produccion,
            fecha_vencimiento=self.fecha_produccion + timedelta(days=365),
            produccion=self.produccion
        )

        self.client.get(
            reverse(
                "eliminar_lote",
                args=[lote.id]
            )
        )

        self.assertEqual(
            Lote.objects.count(),
            0
        )