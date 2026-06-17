from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import (
    Usuario,
    Empleado,
    Turno,
    Solicitud
)


class SolicitudTests(TestCase):

    def setUp(self):

        # Usuario Django (para @login_required)
        self.user = User.objects.create_user(
            username="admin",
            password="123456"
        )

        self.client.login(
            username="admin",
            password="123456"
        )

        # Usuario del sistema
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

        self.turno_manana = Turno.objects.create(
            horario="Mañana 6:00am - 2:00pm",
            activo=True
        )

        self.turno_tarde = Turno.objects.create(
            horario="Tarde 2:00pm - 10:00pm",
            activo=True
        )

    def test_crear_solicitud_correctamente(self):

        self.client.post(
            reverse("guardar_solicitud"),
            {
                "empleado_id": self.empleado.id,
                "turno_actual_id": self.turno_manana.id,
                "turno_solicitado_id": self.turno_tarde.id,
                "motivo": "Necesito cambio por asuntos familiares"
            }
        )

        self.assertEqual(
            Solicitud.objects.count(),
            1
        )

        solicitud = Solicitud.objects.first()

        self.assertEqual(
            solicitud.estado,
            "Pendiente"
        )

    def test_no_permitir_mismo_turno(self):

        self.client.post(
            reverse("guardar_solicitud"),
            {
                "empleado_id": self.empleado.id,
                "turno_actual_id": self.turno_manana.id,
                "turno_solicitado_id": self.turno_manana.id,
                "motivo": "Necesito cambiar de horario"
            }
        )

        self.assertEqual(
            Solicitud.objects.count(),
            0
        )

    def test_no_permitir_motivo_muy_corto(self):

        self.client.post(
            reverse("guardar_solicitud"),
            {
                "empleado_id": self.empleado.id,
                "turno_actual_id": self.turno_manana.id,
                "turno_solicitado_id": self.turno_tarde.id,
                "motivo": "Muy corto"
            }
        )

        self.assertEqual(
            Solicitud.objects.count(),
            0
        )

    def test_aprobar_solicitud(self):

        solicitud = Solicitud.objects.create(
            empleado=self.empleado,
            turno_actual=self.turno_manana,
            turno_solicitado=self.turno_tarde,
            motivo="Necesito cambio por estudios",
            estado="Pendiente"
        )

        self.client.post(
            reverse(
                "revisar_solicitud",
                args=[solicitud.id]
            ),
            {
                "estado": "Aprobado"
            }
        )

        solicitud.refresh_from_db()

        self.assertEqual(
            solicitud.estado,
            "Aprobado"
        )

    def test_rechazar_solicitud(self):

        solicitud = Solicitud.objects.create(
            empleado=self.empleado,
            turno_actual=self.turno_manana,
            turno_solicitado=self.turno_tarde,
            motivo="Necesito cambio por estudios",
            estado="Pendiente"
        )

        self.client.post(
            reverse(
                "revisar_solicitud",
                args=[solicitud.id]
            ),
            {
                "estado": "Rechazado"
            }
        )

        solicitud.refresh_from_db()

        self.assertEqual(
            solicitud.estado,
            "Rechazado"
        )