from datetime import date

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import (
    Usuario,
    Empleado,
    Turno,
    RotacionTurno,
    Asignacion,
    HistorialCorreo
)


class SmokeCorreosTests(TestCase):

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

        self.empleado = Empleado.objects.create(
            cedula="123456",
            nombre="Empleado Test",
            email="empleado@test.com",
            direccion="Bogota",
            estado="Activo",
            creado_por=self.admin
        )

        self.turno = Turno.objects.create(
            horario="Mañana 6:00am - 2:00pm",
            activo=True
        )

        self.rotacion = RotacionTurno.objects.create(
            empleado=self.empleado,
            turno=self.turno,
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
            semana=date.today().isocalendar()[1],
            estado="Asignado"
        )

        self.asignacion = Asignacion.objects.create(
            tarea="Empacar",
            descripcion_tarea="Prueba humo",
            fecha_asignacion=date.today(),
            estado="Pendiente",
            empleado=self.empleado,
            turno=self.turno,
            asignado_por=self.admin
        )

    def test_correos_vista_carga(self):

        response = self.client.get(
            reverse("correos_vista")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_enviar_correos_masivos_funciona(self):

        response = self.client.post(
            reverse("enviar_correos_masivos"),
            {
                "empleados_ids": [self.empleado.id]
            },
            follow=True
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            HistorialCorreo.objects.count(),
            1
        )

        self.assertEqual(
            len(mail.outbox),
            1
        )

    def test_redireccion_si_no_hay_empleados(self):

        response = self.client.post(
            reverse("enviar_correos_masivos"),
            {},
            follow=True
        )

        self.assertEqual(
            response.status_code,
            200
        )