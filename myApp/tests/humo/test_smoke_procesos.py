from datetime import date

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


class SmokeProcesosTests(TestCase):

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

        self.empleado = Empleado.objects.create(
            cedula="123456",
            nombre="Empleado Test",
            email="empleado@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.admin
        )

        self.produccion = Produccion.objects.create(
            producto="Chocolate Oscuro",
            ingredientes="Cacao",
            cantidad_requerida="100",
            fecha_entrega=date.today(),
            fecha_limite=date.today(),
            estado="En Proceso",
            empleado_responsable=self.empleado,
            creado_por=self.admin
        )

        self.lote = Lote.objects.create(
            codigo_lote="LOTE001",
            cantidad="100",
            fecha_produccion=date.today(),
            fecha_vencimiento=date.today(),
            produccion=self.produccion
        )

        self.exportacion = Exportacion.objects.create(
            destino="España",
            pais="España",
            fecha_envio=date.today(),
            fecha_entrega=date.today(),
            estado="Pendiente",
            produccion=self.produccion,
            lote=self.lote
        )

    def test_produccion_existe(self):
        self.assertTrue(
            Produccion.objects.filter(
                id=self.produccion.id
            ).exists()
        )

    def test_lote_existe(self):
        self.assertTrue(
            Lote.objects.filter(
                id=self.lote.id
            ).exists()
        )

    def test_exportacion_existe(self):
        self.assertTrue(
            Exportacion.objects.filter(
                id=self.exportacion.id
            ).exists()
        )

    def test_relacion_produccion_lote(self):
        self.assertEqual(
            self.lote.produccion,
            self.produccion
        )

    def test_relacion_exportacion(self):
        self.assertEqual(
            self.exportacion.produccion,
            self.produccion
        )

        self.assertEqual(
            self.exportacion.lote,
            self.lote
        )