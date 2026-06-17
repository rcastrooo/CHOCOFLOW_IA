from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import (
    Usuario,
    Empleado,
    Produccion,
    Lote,
    Exportacion
)


class ExportacionTests(TestCase):

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

        self.lote = Lote.objects.create(
            codigo_lote="CH-001",
            cantidad="500",
            fecha_produccion=self.fecha_produccion,
            fecha_vencimiento=self.fecha_produccion + timedelta(days=365),
            produccion=self.produccion
        )

    def test_crear_exportacion_correctamente(self):

        self.client.post(
            reverse("guardar_exportacion"),
            {
                "destino": "Madrid",
                "pais": "Espana",
                "nombre_producto": "Chocolate",
                "fecha_envio": self.fecha_produccion.isoformat(),
                "fecha_entrega": (
                    self.fecha_produccion + timedelta(days=30)
                ).isoformat(),
                "estado": "Pendiente",
                "produccion_id": self.produccion.id,
                "lote_id": self.lote.id,
                "cantidad_cajas": "10",
                "unidades_por_caja": "20",
                "peso_caja": "5.5",
                "peso_total": "55.0"
            }
        )

        self.assertEqual(
            Exportacion.objects.count(),
            1
        )

    def test_no_permitir_destino_numerico(self):

        self.client.post(
            reverse("guardar_exportacion"),
            {
                "destino": "Madrid123",
                "pais": "Espana",
                "fecha_envio": self.fecha_produccion.isoformat(),
                "fecha_entrega": (
                    self.fecha_produccion + timedelta(days=30)
                ).isoformat(),
                "estado": "Pendiente",
                "produccion_id": self.produccion.id,
                "lote_id": self.lote.id
            }
        )

        self.assertEqual(
            Exportacion.objects.count(),
            0
        )

    def test_no_permitir_fecha_entrega_anterior_envio(self):

        self.client.post(
            reverse("guardar_exportacion"),
            {
                "destino": "Madrid",
                "pais": "Espana",
                "fecha_envio": self.fecha_produccion.isoformat(),
                "fecha_entrega": (
                    self.fecha_produccion - timedelta(days=1)
                ).isoformat(),
                "estado": "Pendiente",
                "produccion_id": self.produccion.id,
                "lote_id": self.lote.id
            }
        )

        self.assertEqual(
            Exportacion.objects.count(),
            0
        )

    def test_no_permitir_exportacion_sin_lote(self):

        self.client.post(
            reverse("guardar_exportacion"),
            {
                "destino": "Madrid",
                "pais": "Espana",
                "fecha_envio": self.fecha_produccion.isoformat(),
                "fecha_entrega": (
                    self.fecha_produccion + timedelta(days=20)
                ).isoformat(),
                "estado": "Pendiente",
                "produccion_id": self.produccion.id,
                "lote_id": ""
            }
        )

        self.assertEqual(
            Exportacion.objects.count(),
            0
        )

    def test_no_permitir_exportacion_sin_produccion(self):

        self.client.post(
            reverse("guardar_exportacion"),
            {
                "destino": "Madrid",
                "pais": "Espana",
                "fecha_envio": self.fecha_produccion.isoformat(),
                "fecha_entrega": (
                    self.fecha_produccion + timedelta(days=20)
                ).isoformat(),
                "estado": "Pendiente",
                "produccion_id": "",
                "lote_id": self.lote.id
            }
        )

        self.assertEqual(
            Exportacion.objects.count(),
            0
        )

    def test_no_permitir_fecha_envio_antes_produccion(self):

        self.client.post(
            reverse("guardar_exportacion"),
            {
                "destino": "Madrid",
                "pais": "Espana",
                "fecha_envio": (
                    self.fecha_produccion - timedelta(days=1)
                ).isoformat(),
                "fecha_entrega": (
                    self.fecha_produccion + timedelta(days=20)
                ).isoformat(),
                "estado": "Pendiente",
                "produccion_id": self.produccion.id,
                "lote_id": self.lote.id
            }
        )

        self.assertEqual(
            Exportacion.objects.count(),
            0
        )

    def test_cancelar_exportacion(self):

        exportacion = Exportacion.objects.create(
            destino="Madrid",
            pais="Espana",
            fecha_envio=self.fecha_produccion,
            fecha_entrega=self.fecha_produccion + timedelta(days=20),
            estado="Pendiente",
            produccion=self.produccion,
            lote=self.lote
        )

        self.client.get(
            reverse(
                "inactivar_exportacion",
                args=[exportacion.id]
            )
        )

        exportacion.refresh_from_db()

        self.assertEqual(
            exportacion.estado,
            "Cancelado"
        )