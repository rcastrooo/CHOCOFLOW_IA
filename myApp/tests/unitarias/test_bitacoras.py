from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import (
    Usuario,
    Produccion,
    Empleado,
    Bitacora
)


class BitacoraTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="supervisor",
            password="123456"
        )

        self.client.login(
            username="supervisor",
            password="123456"
        )

        self.supervisor = Usuario.objects.create(
            nombre="Supervisor Test",
            email="supervisor@test.com",
            direccion="Bogota",
            contrasena="123456",
            rol="Supervisor",
            estado="Activo",
            turno="Mañana 6:00am - 2:00pm"
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
            fecha_entrega=date.today() + timedelta(days=5),
            fecha_limite=date.today() + timedelta(days=3),
            estado="En Proceso",
            empleado_responsable=self.empleado,
            creado_por=self.supervisor
        )

    # ==================================
    # CREAR BITACORA
    # ==================================

    def test_bitacora_supervisor_get_200(self):

        response = self.client.get(
            reverse("bitacora_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_crear_bitacora_borrador(self):

        response = self.client.post(
            reverse("bitacora_supervisor"),
            {
                "titulo": "Bitacora prueba",
                "descripcion": "Descripcion suficientemente larga para la prueba",
                "tipo_reporte": "Diario",
                "produccion": self.produccion.id,
                "unidades_producidas": "50",
                "unidades_pendientes": "10",
                "observaciones": "Ninguna",
                "estado": "Borrador"
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertTrue(
            Bitacora.objects.filter(
                titulo="Bitacora prueba",
                estado="Borrador"
            ).exists()
        )

    def test_crear_bitacora_enviada(self):

        response = self.client.post(
            reverse("bitacora_supervisor"),
            {
                "titulo": "Bitacora enviada",
                "descripcion": "Descripcion suficientemente larga para la prueba",
                "tipo_reporte": "Diario",
                "produccion": self.produccion.id,
                "unidades_producidas": "50",
                "unidades_pendientes": "10",
                "estado": "Enviado"
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertTrue(
            Bitacora.objects.filter(
                titulo="Bitacora enviada",
                estado="Enviado"
            ).exists()
        )

    def test_no_crear_bitacora_titulo_corto(self):

        response = self.client.post(
            reverse("bitacora_supervisor"),
            {
                "titulo": "abc",
                "descripcion": "Descripcion suficientemente larga para la prueba",
                "tipo_reporte": "Diario",
                "produccion": self.produccion.id,
                "unidades_producidas": "50",
                "unidades_pendientes": "10",
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_no_crear_bitacora_descripcion_corta(self):

        response = self.client.post(
            reverse("bitacora_supervisor"),
            {
                "titulo": "Titulo valido",
                "descripcion": "Muy corta",
                "tipo_reporte": "Diario",
                "produccion": self.produccion.id,
                "unidades_producidas": "50",
                "unidades_pendientes": "10",
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

    # ==================================
    # ENVIAR BITACORA
    # ==================================

    def test_enviar_bitacora_borrador(self):

        bitacora = Bitacora.objects.create(
            titulo="Borrador",
            descripcion="Descripcion larga para pruebas",
            tipo_reporte="Diario",
            estado="Borrador",
            supervisor=self.supervisor,
            produccion=self.produccion
        )

        response = self.client.get(
            reverse(
                "enviar_bitacora",
                args=[bitacora.id]
            )
        )

        self.assertEqual(
            response.status_code,
            302
        )

        bitacora.refresh_from_db()

        self.assertEqual(
            bitacora.estado,
            "Enviado"
        )

    def test_no_enviar_bitacora_ya_enviada(self):

        bitacora = Bitacora.objects.create(
            titulo="Enviada",
            descripcion="Descripcion larga para pruebas",
            tipo_reporte="Diario",
            estado="Enviado",
            supervisor=self.supervisor,
            produccion=self.produccion
        )

        self.client.get(
            reverse(
                "enviar_bitacora",
                args=[bitacora.id]
            )
        )

        bitacora.refresh_from_db()

        self.assertEqual(
            bitacora.estado,
            "Enviado"
        )

    # ==================================
    # LISTADOS
    # ==================================

    def test_listar_bitacoras_supervisor(self):

        response = self.client.get(
            reverse("listar_bitacoras_supervisor")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_listar_bitacoras_admin(self):

        response = self.client.get(
            reverse("listar_bitacoras")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    # ==================================
    # REVISAR BITACORA
    # ==================================

    def test_aprobar_bitacora(self):

        bitacora = Bitacora.objects.create(
            titulo="Revision",
            descripcion="Descripcion larga",
            tipo_reporte="Diario",
            estado="Enviado",
            supervisor=self.supervisor,
            produccion=self.produccion
        )

        response = self.client.post(
            reverse(
                "revisar_bitacora",
                args=[bitacora.id]
            ),
            {
                "estado": "Aprobado",
                "observacion_admin": "Todo correcto"
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        bitacora.refresh_from_db()

        self.assertEqual(
            bitacora.estado,
            "Aprobado"
        )

    def test_rechazar_bitacora(self):

        bitacora = Bitacora.objects.create(
            titulo="Revision",
            descripcion="Descripcion larga",
            tipo_reporte="Diario",
            estado="Enviado",
            supervisor=self.supervisor,
            produccion=self.produccion
        )

        self.client.post(
            reverse(
                "revisar_bitacora",
                args=[bitacora.id]
            ),
            {
                "estado": "Rechazado",
                "observacion_admin": "Faltan datos"
            }
        )

        bitacora.refresh_from_db()

        self.assertEqual(
            bitacora.estado,
            "Rechazado"
        )

    def test_estado_revision_invalido(self):

        bitacora = Bitacora.objects.create(
            titulo="Revision",
            descripcion="Descripcion larga",
            tipo_reporte="Diario",
            estado="Enviado",
            supervisor=self.supervisor,
            produccion=self.produccion
        )

        self.client.post(
            reverse(
                "revisar_bitacora",
                args=[bitacora.id]
            ),
            {
                "estado": "EstadoInvalido"
            }
        )

        bitacora.refresh_from_db()

        self.assertEqual(
            bitacora.estado,
            "Enviado"
        )