from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import (
    Usuario,
    Empleado,
    Turno,
    RotacionTurno
)


class TurnosTests(TestCase):

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

        self.turno = Turno.objects.create(
            horario="Mañana 6:00am - 2:00pm",
            activo=True
        )

        hoy = date.today()

        dias_hasta_lunes = (7 - hoy.weekday()) % 7
        if dias_hasta_lunes == 0:
            dias_hasta_lunes = 7

        self.fecha_inicio = hoy + timedelta(days=dias_hasta_lunes)
        self.fecha_fin = self.fecha_inicio + timedelta(days=6)
        self.semana = self.fecha_inicio.isocalendar()[1]

    def test_crear_rotacion_correctamente(self):

        self.client.post(
            reverse("guardar_rotacion"),
            {
                "empleado_id": self.empleado.id,
                "turno_id": self.turno.id,
                "fecha_inicio": self.fecha_inicio.isoformat(),
                "fecha_fin": self.fecha_fin.isoformat(),
                "semana": self.semana,
                "estado": "Pendiente"
            }
        )

        self.assertEqual(
            RotacionTurno.objects.count(),
            1
        )

    def test_no_permitir_rotacion_duplicada(self):

        RotacionTurno.objects.create(
            empleado=self.empleado,
            turno=self.turno,
            fecha_inicio=self.fecha_inicio,
            fecha_fin=self.fecha_fin,
            semana=self.semana,
            estado="Pendiente"
        )

        self.client.post(
            reverse("guardar_rotacion"),
            {
                "empleado_id": self.empleado.id,
                "turno_id": self.turno.id,
                "fecha_inicio": self.fecha_inicio.isoformat(),
                "fecha_fin": self.fecha_fin.isoformat(),
                "semana": self.semana,
                "estado": "Pendiente"
            }
        )

        self.assertEqual(
            RotacionTurno.objects.count(),
            1
        )

    def test_no_permitir_semana_invalida(self):

        self.client.post(
            reverse("guardar_rotacion"),
            {
                "empleado_id": self.empleado.id,
                "turno_id": self.turno.id,
                "fecha_inicio": self.fecha_inicio.isoformat(),
                "fecha_fin": self.fecha_fin.isoformat(),
                "semana": 60,
                "estado": "Pendiente"
            }
        )

        self.assertEqual(
            RotacionTurno.objects.count(),
            0
        )

    def test_no_permitir_fecha_fin_menor_inicio(self):

        self.client.post(
            reverse("guardar_rotacion"),
            {
                "empleado_id": self.empleado.id,
                "turno_id": self.turno.id,
                "fecha_inicio": self.fecha_inicio.isoformat(),
                "fecha_fin": (
                    self.fecha_inicio - timedelta(days=1)
                ).isoformat(),
                "semana": self.semana,
                "estado": "Pendiente"
            }
        )

        self.assertEqual(
            RotacionTurno.objects.count(),
            0
        )

    def test_eliminar_rotacion(self):

        rotacion = RotacionTurno.objects.create(
            empleado=self.empleado,
            turno=self.turno,
            fecha_inicio=self.fecha_inicio,
            fecha_fin=self.fecha_fin,
            semana=self.semana,
            estado="Pendiente"
        )

        self.client.get(
            reverse(
                "eliminar_rotacion",
                args=[rotacion.id]
            )
        )

        self.assertEqual(
            RotacionTurno.objects.count(),
            0
        )