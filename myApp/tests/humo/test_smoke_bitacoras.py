from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import date
from myApp.models import (
    Usuario,
    Empleado,
    Produccion,
    Bitacora
)


class SmokeBitacorasTests(TestCase):

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

        self.supervisor = Usuario.objects.create(
            nombre="Supervisor",
            email="super@test.com",
            direccion="Bogota",
            contrasena="123456",
            rol="Supervisor",
            estado="Activo"
        )

        session = self.client.session
        session["usuario_id"] = self.supervisor.id
        session["rol"] = "Supervisor"
        session.save()

        self.empleado = Empleado.objects.create(
            cedula="123",
            nombre="Empleado Test",
            email="empleado@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.supervisor
        )

        self.produccion = Produccion.objects.create(
            producto="Chocolate",
            ingredientes="Cacao",
            cantidad_requerida="100",
            fecha_entrega=date.today(),
            fecha_limite=date.today(),
            estado="En Proceso",
            empleado_responsable=self.empleado,
            creado_por=self.supervisor
        )

        self.bitacora = Bitacora.objects.create(
            titulo="Bitacora Test",
            descripcion="Descripcion suficientemente larga para prueba",
            tipo_reporte="Diario",
            estado="Borrador",
            supervisor=self.supervisor,
            produccion=self.produccion
        )

    def test_crear_bitacora_carga(self):

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

    def test_enviar_bitacora_funciona(self):

        response = self.client.get(
            reverse(
                "enviar_bitacora",
                args=[self.bitacora.id]
            )
        )

        self.assertEqual(
            response.status_code,
            302
        )

    def test_listar_bitacoras_admin_carga(self):

        session = self.client.session
        session["usuario_id"] = self.admin.id
        session["rol"] = "Administrador"
        session.save()

        response = self.client.get(
            reverse("listar_bitacoras")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_revisar_bitacora_funciona(self):

        self.bitacora.estado = "Enviado"
        self.bitacora.save()

        session = self.client.session
        session["usuario_id"] = self.admin.id
        session["rol"] = "Administrador"
        session.save()

        response = self.client.post(
            reverse(
                "revisar_bitacora",
                args=[self.bitacora.id]
            ),
            {
                "estado": "Aprobado",
                "observacion_admin": "Correcto"
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )