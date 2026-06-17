from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import (
    Usuario,
    Empleado,
    Turno,
    RotacionTurno,
    Asignacion,
    HistorialCorreo,
)


class CorreosMasivosTests(TestCase):

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
        session["rol"] = "Administrador"
        session.save()

        self.turno = Turno.objects.create(
            horario="Mañana 6:00am - 2:00pm"
        )

        self.empleado = Empleado.objects.create(
            cedula="123",
            nombre="Empleado Test",
            email="empleado@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.admin
        )

        hoy = date.today()
        lunes = hoy - timedelta(days=hoy.weekday())
        domingo = lunes + timedelta(days=6)

        RotacionTurno.objects.create(
            empleado=self.empleado,
            turno=self.turno,
            fecha_inicio=lunes,
            fecha_fin=domingo,
            semana=hoy.isocalendar()[1]
        )

        Asignacion.objects.create(
            tarea="Empacar",
            fecha_asignacion=hoy,
            empleado=self.empleado,
            turno=self.turno,
            asignado_por=self.admin
        )

    # ==========================
    # VISTA PRINCIPAL
    # ==========================

    def test_correos_vista_responde_200(self):

        response = self.client.get(
            reverse("correos_vista")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_correos_vista_usa_template_correcto(self):

        response = self.client.get(
            reverse("correos_vista")
        )

        self.assertTemplateUsed(
            response,
            "modulos/correos/correos.html"
        )

    # ==========================
    # ENVIO EXITOSO
    # ==========================

    @patch("myApp.views.send_mail")
    def test_enviar_correo_exitosamente(
        self,
        mock_send_mail
    ):

        mock_send_mail.return_value = 1

        response = self.client.post(
            reverse("enviar_correos_masivos"),
            {
                "empleados_ids": [self.empleado.id]
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertEqual(
            HistorialCorreo.objects.count(),
            1
        )

        historial = HistorialCorreo.objects.first()

        self.assertEqual(
            historial.estado,
            "Enviado"
        )

    # ==========================
    # HISTORIAL
    # ==========================

    @patch("myApp.views.send_mail")
    def test_crea_historial_correo(
        self,
        mock_send_mail
    ):

        mock_send_mail.return_value = 1

        self.client.post(
            reverse("enviar_correos_masivos"),
            {
                "empleados_ids": [self.empleado.id]
            }
        )

        historial = HistorialCorreo.objects.first()

        self.assertIsNotNone(
            historial
        )

        self.assertEqual(
            historial.empleado,
            self.empleado
        )

    # ==========================
    # SIN EMPLEADOS
    # ==========================

    def test_no_seleccionar_empleados(self):

        response = self.client.post(
            reverse("enviar_correos_masivos"),
            {}
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertEqual(
            HistorialCorreo.objects.count(),
            0
        )

    # ==========================
    # ERROR DE ENVIO
    # ==========================

    @patch("myApp.views.send_mail")
    def test_error_envio_correo(
        self,
        mock_send_mail
    ):

        mock_send_mail.side_effect = Exception(
            "SMTP Error"
        )

        self.client.post(
            reverse("enviar_correos_masivos"),
            {
                "empleados_ids": [self.empleado.id]
            }
        )

        self.assertEqual(
            HistorialCorreo.objects.count(),
            1
        )

        historial = HistorialCorreo.objects.first()

        self.assertEqual(
            historial.estado,
            "Error"
        )

    # ==========================
    # MULTIPLES EMPLEADOS
    # ==========================

    @patch("myApp.views.send_mail")
    def test_envio_multiple_empleados(
        self,
        mock_send_mail
    ):

        mock_send_mail.return_value = 1

        empleado2 = Empleado.objects.create(
            cedula="456",
            nombre="Empleado 2",
            email="empleado2@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.admin
        )

        self.client.post(
            reverse("enviar_correos_masivos"),
            {
                "empleados_ids": [
                    self.empleado.id,
                    empleado2.id
                ]
            }
        )

        self.assertEqual(
            HistorialCorreo.objects.filter(
                estado="Enviado"
            ).count(),
            2
        )

    # ==========================
    # SOLO ACTIVOS
    # ==========================

    @patch("myApp.views.send_mail")
    def test_no_envia_a_empleado_inactivo(
        self,
        mock_send_mail
    ):

        self.empleado.estado = "Inactivo"
        self.empleado.save()

        self.client.post(
            reverse("enviar_correos_masivos"),
            {
                "empleados_ids": [self.empleado.id]
            }
        )

        self.assertEqual(
            HistorialCorreo.objects.count(),
            0
        )