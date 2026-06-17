from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from myApp.models import (
    Usuario,
    Empleado,
    Turno,
    RotacionTurno,
    Asignacion
)


class AsignacionTests(TestCase):

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

        self.turno_manana = Turno.objects.create(
            horario="Mañana 6:00am - 2:00pm",
            activo=True
        )

        self.turno_tarde = Turno.objects.create(
            horario="Tarde 2:00pm - 10:00pm",
            activo=True
        )

        self.fecha = date.today() + timedelta(days=1)

        RotacionTurno.objects.create(
            empleado=self.empleado,
            turno=self.turno_manana,
            fecha_inicio=self.fecha - timedelta(days=1),
            fecha_fin=self.fecha + timedelta(days=5),
            semana=self.fecha.isocalendar()[1],
            estado="Asignado"
        )

    def test_crear_asignacion_correctamente(self):

        self.client.post(
            reverse("guardar_asignacion"),
            {
                "tarea": "Empacar",
                "fecha_asignacion": self.fecha.isoformat(),
                "empleado_id": self.empleado.id,
                "turno_id": self.turno_manana.id,
                "estado": "Pendiente"
            }
        )

        self.assertEqual(
            Asignacion.objects.count(),
            1
        )

    def test_no_permitir_fecha_pasada(self):

        self.client.post(
            reverse("guardar_asignacion"),
            {
                "tarea": "Empacar",
                "fecha_asignacion": (
                    date.today() - timedelta(days=1)
                ).isoformat(),
                "empleado_id": self.empleado.id,
                "turno_id": self.turno_manana.id,
                "estado": "Pendiente"
            }
        )

        self.assertEqual(
            Asignacion.objects.count(),
            0
        )

    def test_no_permitir_turno_diferente_al_asignado(self):

        self.client.post(
            reverse("guardar_asignacion"),
            {
                "tarea": "Empacar",
                "fecha_asignacion": self.fecha.isoformat(),
                "empleado_id": self.empleado.id,
                "turno_id": self.turno_tarde.id,
                "estado": "Pendiente"
            }
        )

        self.assertEqual(
            Asignacion.objects.count(),
            0
        )

    def test_permitir_maximo_dos_tareas_sin_forzar(self):

        Asignacion.objects.create(
            tarea="Empacar",
            fecha_asignacion=self.fecha,
            empleado=self.empleado,
            turno=self.turno_manana,
            asignado_por=self.admin
        )

        Asignacion.objects.create(
            tarea="Etiquetado",
            fecha_asignacion=self.fecha,
            empleado=self.empleado,
            turno=self.turno_manana,
            asignado_por=self.admin
        )

        self.client.post(
            reverse("guardar_asignacion"),
            {
                "tarea": "Sellado",
                "fecha_asignacion": self.fecha.isoformat(),
                "empleado_id": self.empleado.id,
                "turno_id": self.turno_manana.id,
                "estado": "Pendiente"
            }
        )

        self.assertEqual(
            Asignacion.objects.count(),
            2
        )

    def test_crear_tercera_tarea_con_forzar(self):

        Asignacion.objects.create(
            tarea="Empacar",
            fecha_asignacion=self.fecha,
            empleado=self.empleado,
            turno=self.turno_manana,
            asignado_por=self.admin
        )

        Asignacion.objects.create(
            tarea="Etiquetado",
            fecha_asignacion=self.fecha,
            empleado=self.empleado,
            turno=self.turno_manana,
            asignado_por=self.admin
        )

        self.client.post(
            reverse("guardar_asignacion"),
            {
                "tarea": "Sellado",
                "fecha_asignacion": self.fecha.isoformat(),
                "empleado_id": self.empleado.id,
                "turno_id": self.turno_manana.id,
                "estado": "Pendiente",
                "forzar": "1"
            }
        )

        self.assertEqual(
            Asignacion.objects.count(),
            3
        )

    def test_finalizar_asignacion(self):

        asignacion = Asignacion.objects.create(
            tarea="Empacar",
            fecha_asignacion=self.fecha,
            empleado=self.empleado,
            turno=self.turno_manana,
            asignado_por=self.admin,
            estado="Pendiente"
        )

        self.client.get(
            reverse(
                "inactivar_asignacion",
                args=[asignacion.id]
            )
        )

        asignacion.refresh_from_db()

        self.assertEqual(
            asignacion.estado,
            "Finalizado"
        )