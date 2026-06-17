"""
========================================================
  PRUEBAS INTEGRALES — CHOCOFLOW
  Sistema de Gestión de Producción de Chocolate

Cómo ejecutar:
    python manage.py test myApp.tests --verbosity=2

Módulos cubiertos:
    ✅ Auth          — login, logout, registro
    ✅ Supervisores  — gestión, turno, edición, inactivar
    ✅ Empleados     — crear, editar, validaciones, inactivar
    ✅ Turnos        — crear rotación, validaciones, eliminar
    ✅ Solicitudes   — crear, revisar (aprobar/rechazar)
    ✅ Asignaciones  — crear admin y supervisor, límite 2 tareas, turno inválido
    ✅ Producción    — crear, cancelar, validaciones de fecha
    ✅ Lotes         — crear, código inválido, fecha inválida
    ✅ Exportaciones — crear, validaciones fecha/lote
    ✅ Bitácora      — crear borrador, enviar, revisar
"""

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from myApp.models import (
    Asignacion,
    Bitacora,
    Empleado,
    Exportacion,
    Lote,
    Produccion,
    RotacionTurno,
    Solicitud,
    Turno,
    Usuario,
)


# ============================================================
# HELPER — crea toda la estructura base reutilizable
# ============================================================

class ChocoFlowTestBase(TestCase):
    """
    Base compartida: crea un admin y un supervisor Django + perfil
    Usuario, un Turno, un Empleado y una RotacionTurno para la
    semana actual, lista para usar en cualquier suite de pruebas.
    """

    def setUp(self):
        self.client = Client()

        # ── Turno base ────────────────────────────────────────────
        self.turno_mañana = Turno.objects.create(
            horario='Mañana 6:00am - 2:00pm',
            activo=True,
        )
        self.turno_tarde = Turno.objects.create(
            horario='Tarde 2:00pm - 10:00pm',
            activo=True,
        )

        # ── Admin Django + perfil ─────────────────────────────────
        self.admin_django = User.objects.create_user(
            username='11111111',
            email='admin@chocoflow.com',
            password='Admin1234',
        )
        self.admin_perfil = Usuario.objects.create(
            nombre='Admin Test',
            email='admin@chocoflow.com',
            direccion='Calle 1',
            contrasena='Admin1234',
            rol='Administrador',
            estado='Activo',
        )

        # ── Supervisor Django + perfil ────────────────────────────
        self.sup_django = User.objects.create_user(
            username='22222222',
            email='supervisor@chocoflow.com',
            password='Sup12345',
        )
        self.sup_perfil = Usuario.objects.create(
            nombre='Supervisor Test',
            email='supervisor@chocoflow.com',
            direccion='Calle 2',
            contrasena='Sup12345',
            rol='Supervisor',
            estado='Activo',
            turno='Mañana 6:00am - 2:00pm',
        )

        # ── Empleado activo ───────────────────────────────────────
        self.empleado = Empleado.objects.create(
            cedula='123456789',
            nombre='Juan Pérez',
            email='juan@chocoflow.com',
            direccion='Calle 3',
            estado='Activo',
            creado_por=self.admin_perfil,
        )

        # ── RotacionTurno semana actual ───────────────────────────
        hoy   = date.today()
        lunes = hoy - timedelta(days=hoy.weekday())   # lunes de esta semana
        dom   = lunes + timedelta(days=6)             # domingo
        self.semana_actual = hoy.isocalendar()[1]

        self.rotacion = RotacionTurno.objects.create(
            empleado     = self.empleado,
            turno        = self.turno_mañana,
            fecha_inicio = lunes,
            fecha_fin    = dom,
            semana       = self.semana_actual,
            estado       = 'Asignado',
        )

        # ── Producción base (para lotes, exportaciones…) ──────────
        self.produccion = Produccion.objects.create(
            producto              = 'Chocolate negro',
            ingredientes          = 'Cacao, azúcar',
            cantidad_requerida    = '100',
            fecha_entrega         = hoy + timedelta(days=7),
            fecha_limite          = hoy + timedelta(days=14),
            estado                = 'En Proceso',
            empleado_responsable  = self.empleado,
            creado_por            = self.admin_perfil,
        )

    # ── Helpers de login ──────────────────────────────────────────

    def login_admin(self):
        self.client.post(reverse('login'), {
            'username': 'admin@chocoflow.com',
            'password': 'Admin1234',
        })
        session = self.client.session
        session['usuario_id'] = self.admin_perfil.id
        session['rol']        = 'Administrador'
        session.save()

    def login_supervisor(self):
        self.client.post(reverse('login'), {
            'username': 'supervisor@chocoflow.com',
            'password': 'Sup12345',
        })
        session = self.client.session
        session['usuario_id'] = self.sup_perfil.id
        session['rol']        = 'Supervisor'
        session.save()


# ============================================================
# 1. AUTENTICACIÓN
# ============================================================

class AuthTests(ChocoFlowTestBase):
    """Login, logout y registro de usuarios."""

    # ── Login exitoso ─────────────────────────────────────────────
    def test_login_admin_exitoso(self):
        resp = self.client.post(reverse('login'), {
            'username': 'admin@chocoflow.com',
            'password': 'Admin1234',
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_login_supervisor_exitoso(self):
        resp = self.client.post(reverse('login'), {
            'username': 'supervisor@chocoflow.com',
            'password': 'Sup12345',
        })
        self.assertIn(resp.status_code, [200, 302])

    # ── Login fallido ─────────────────────────────────────────────
    def test_login_credenciales_incorrectas(self):
        resp = self.client.post(reverse('login'), {
            'username': 'admin@chocoflow.com',
            'password': 'Wrongpass1',
        })
        self.assertEqual(resp.status_code, 200)

    def test_login_correo_invalido(self):
        resp = self.client.post(reverse('login'), {
            'username': 'no-es-correo',
            'password': 'Admin1234',
        })
        self.assertEqual(resp.status_code, 200)

    def test_login_campos_vacios(self):
        resp = self.client.post(reverse('login'), {
            'username': '',
            'password': '',
        })
        self.assertEqual(resp.status_code, 200)

    # ── Logout ────────────────────────────────────────────────────
    def test_logout(self):
        self.login_admin()
        resp = self.client.get(reverse('logout'))
        self.assertRedirects(resp, reverse('index'))

    # ── Registro exitoso ──────────────────────────────────────────
    def test_registro_supervisor_exitoso(self):
        resp = self.client.post(reverse('registro'), {
            'identificacion': '99999999',
            'nombre'        : 'Carlos López',
            'correo'        : 'carlos@chocoflow.com',
            'telefono'      : '3001234567',
            'direccion'     : 'Calle 5',
            'password'      : 'Carlos123',
            'rol'           : 'Supervisor',
            'estado'        : 'Activo',
            'turno'         : 'Mañana 6:00am - 2:00pm',
        })
        self.assertIn(resp.status_code, [200, 302])
        self.assertTrue(
            User.objects.filter(email='carlos@chocoflow.com').exists()
        )

    def test_registro_admin_exitoso(self):
        resp = self.client.post(reverse('registro'), {
            'identificacion': '88888888',
            'nombre'        : 'Maria García',
            'correo'        : 'maria@chocoflow.com',
            'telefono'      : '3109876543',
            'direccion'     : 'Calle 6',
            'password'      : 'Maria1234',
            'rol'           : 'Administrador',
            'estado'        : 'Activo',
            'turno'         : '',
        })
        self.assertIn(resp.status_code, [200, 302])

    # ── Validaciones de registro ──────────────────────────────────
    def test_registro_password_corta(self):
        resp = self.client.post(reverse('registro'), {
            'identificacion': '77777777',
            'nombre'        : 'Pedro Ruiz',
            'correo'        : 'pedro@chocoflow.com',
            'password'      : 'Ab1',        # muy corta
            'rol'           : 'Supervisor',
            'estado'        : 'Activo',
            'turno'         : 'Mañana 6:00am - 2:00pm',
        })
        self.assertEqual(resp.status_code, 302)   # redirect con error

    def test_registro_password_sin_mayuscula(self):
        resp = self.client.post(reverse('registro'), {
            'identificacion': '77777776',
            'nombre'        : 'Pedro Ruiz',
            'correo'        : 'pedrov@chocoflow.com',
            'password'      : 'sinmayus1',  # sin mayúscula
            'rol'           : 'Supervisor',
            'estado'        : 'Activo',
            'turno'         : 'Mañana 6:00am - 2:00pm',
        })
        self.assertEqual(resp.status_code, 302)

    def test_registro_password_sin_numero(self):
        resp = self.client.post(reverse('registro'), {
            'identificacion': '77777775',
            'nombre'        : 'Pedro Ruiz',
            'correo'        : 'pedron@chocoflow.com',
            'password'      : 'SinNumero',  # sin número
            'rol'           : 'Supervisor',
            'estado'        : 'Activo',
            'turno'         : 'Mañana 6:00am - 2:00pm',
        })
        self.assertEqual(resp.status_code, 302)

    def test_registro_correo_duplicado(self):
        self.client.post(reverse('registro'), {
            'identificacion': '66666661',
            'nombre'        : 'Nuevo User',
            'correo'        : 'admin@chocoflow.com',   # ya existe
            'password'      : 'Admin1234',
            'rol'           : 'Administrador',
            'estado'        : 'Activo',
            'turno'         : '',
        })
        self.assertEqual(User.objects.filter(email='admin@chocoflow.com').count(), 1)

    def test_registro_supervisor_sin_turno(self):
        resp = self.client.post(reverse('registro'), {
            'identificacion': '55555555',
            'nombre'        : 'Sin Turno',
            'correo'        : 'sinturno@chocoflow.com',
            'password'      : 'Turno1234',
            'rol'           : 'Supervisor',
            'estado'        : 'Activo',
            'turno'         : '',    # obligatorio para supervisor
        })
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(User.objects.filter(email='sinturno@chocoflow.com').exists())

    # ── Protección de rutas ───────────────────────────────────────
    def test_dashboard_requiere_login(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertRedirects(resp, '/login/?next=/dashboard/')

    def test_dashboard_supervisor_requiere_login(self):
        resp = self.client.get(reverse('dashboard_supervisor'))
        self.assertRedirects(resp, '/login/?next=/supervisor/')


# ============================================================
# 2. GESTIÓN DE SUPERVISORES
# ============================================================

class SupervisorTests(ChocoFlowTestBase):

    def test_listar_supervisores(self):
        self.login_admin()
        resp = self.client.get(reverse('gestionar_supervisores'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.sup_perfil, resp.context['supervisores'])

    def test_filtrar_supervisores_por_nombre(self):
        self.login_admin()
        resp = self.client.get(reverse('gestionar_supervisores'), {'q': 'Supervisor Test'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.sup_perfil, resp.context['supervisores'])

    def test_asignar_turno_supervisor(self):
        self.login_admin()
        resp = self.client.post(
            reverse('asignar_turno_supervisor', args=[self.sup_perfil.id]),
            {'turno': 'Tarde 2:00pm - 10:00pm'},
        )
        self.assertRedirects(resp, reverse('gestionar_supervisores'))
        self.sup_perfil.refresh_from_db()
        self.assertEqual(self.sup_perfil.turno, 'Tarde 2:00pm - 10:00pm')

    def test_asignar_turno_invalido(self):
        self.login_admin()
        turno_original = self.sup_perfil.turno
        self.client.post(
            reverse('asignar_turno_supervisor', args=[self.sup_perfil.id]),
            {'turno': 'Turno Falso'},
        )
        self.sup_perfil.refresh_from_db()
        self.assertEqual(self.sup_perfil.turno, turno_original)

    def test_editar_supervisor(self):
        self.login_admin()
        resp = self.client.post(reverse('editar_supervisor'), {
            'id'      : self.sup_perfil.id,
            'nombre'  : 'Supervisor Editado',
            'email'   : 'supervisor@chocoflow.com',
            'telefono': '3001112233',
            'estado'  : 'Activo',
            'turno'   : 'Mañana 6:00am - 2:00pm',
        })
        self.assertRedirects(resp, reverse('gestionar_supervisores'))
        self.sup_perfil.refresh_from_db()
        self.assertEqual(self.sup_perfil.nombre, 'Supervisor Editado')

    def test_editar_supervisor_correo_invalido(self):
        self.login_admin()
        self.client.post(reverse('editar_supervisor'), {
            'id'    : self.sup_perfil.id,
            'nombre': 'Supervisor Test',
            'email' : 'correo-malo',
            'estado': 'Activo',
        })
        self.sup_perfil.refresh_from_db()
        # El correo no debe haber cambiado
        self.assertNotEqual(self.sup_perfil.email, 'correo-malo')

    def test_inactivar_supervisor(self):
        self.login_admin()
        resp = self.client.get(
            reverse('inactivar_supervisor', args=[self.sup_perfil.id])
        )
        self.assertRedirects(resp, reverse('gestionar_supervisores'))
        self.sup_perfil.refresh_from_db()
        self.assertEqual(self.sup_perfil.estado, 'Inactivo')


# ============================================================
# 3. EMPLEADOS
# ============================================================

class EmpleadoTests(ChocoFlowTestBase):

    def test_listar_empleados(self):
        self.login_admin()
        resp = self.client.get(reverse('empleados'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.empleado, resp.context['empleados'])

    def test_crear_empleado_exitoso(self):
        self.login_admin()
        resp = self.client.post(reverse('guardar_empleado'), {
            'cedula'   : '987654321',
            'nombre'   : 'Ana Martínez',
            'email'    : 'ana@chocoflow.com',
            'telefono' : '3107654321',
            'direccion': 'Calle 10',
            'estado'   : 'Activo',
        })
        self.assertRedirects(resp, reverse('empleados'))
        self.assertTrue(Empleado.objects.filter(email='ana@chocoflow.com').exists())

    def test_crear_empleado_cedula_duplicada(self):
        self.login_admin()
        self.client.post(reverse('guardar_empleado'), {
            'cedula'   : '123456789',   # ya existe
            'nombre'   : 'Otro Empleado',
            'email'    : 'otro@chocoflow.com',
            'estado'   : 'Activo',
        })
        self.assertFalse(Empleado.objects.filter(email='otro@chocoflow.com').exists())

    def test_crear_empleado_cedula_invalida(self):
        self.login_admin()
        self.client.post(reverse('guardar_empleado'), {
            'cedula'   : 'ABC123',     # letras no permitidas
            'nombre'   : 'Empleado Invalido',
            'email'    : 'inv@chocoflow.com',
            'estado'   : 'Activo',
        })
        self.assertFalse(Empleado.objects.filter(email='inv@chocoflow.com').exists())

    def test_crear_empleado_email_invalido(self):
        self.login_admin()
        self.client.post(reverse('guardar_empleado'), {
            'cedula'   : '111222333',
            'nombre'   : 'Bad Email',
            'email'    : 'no-es-email',
            'estado'   : 'Activo',
        })
        self.assertFalse(Empleado.objects.filter(cedula='111222333').exists())

    def test_editar_empleado(self):
        self.login_admin()
        self.client.post(reverse('guardar_empleado'), {
            'id'       : self.empleado.id,
            'cedula'   : '123456789',
            'nombre'   : 'Juan Editado',
            'email'    : 'juan@chocoflow.com',
            'estado'   : 'Activo',
        })
        self.empleado.refresh_from_db()
        self.assertEqual(self.empleado.nombre, 'Juan Editado')

    def test_inactivar_empleado(self):
        self.login_admin()
        resp = self.client.get(reverse('inactivar_empleado', args=[self.empleado.id]))
        self.assertRedirects(resp, reverse('empleados'))
        self.empleado.refresh_from_db()
        self.assertEqual(self.empleado.estado, 'Inactivo')

    def test_buscar_empleado(self):
        self.login_admin()
        resp = self.client.get(reverse('empleados'), {'q': 'Juan'})
        self.assertIn(self.empleado, resp.context['empleados'])

    def test_filtrar_empleados_por_estado(self):
        self.login_admin()
        resp = self.client.get(reverse('empleados'), {'estado': 'Activo'})
        for emp in resp.context['empleados']:
            self.assertEqual(emp.estado, 'Activo')


# ============================================================
# 4. TURNOS Y ROTACIÓN
# ============================================================

class TurnoTests(ChocoFlowTestBase):

    def test_listar_turnos(self):
        self.login_admin()
        resp = self.client.get(reverse('turnos'))
        self.assertEqual(resp.status_code, 200)

    def test_crear_rotacion_exitosa(self):
        """Crear rotación para la próxima semana (siempre futura)."""
        self.login_admin()
        hoy          = date.today()
        prox_lunes   = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=1)
        prox_domingo = prox_lunes + timedelta(days=6)
        prox_semana  = prox_lunes.isocalendar()[1]

        # Crear un empleado nuevo sin rotación esta semana
        emp2 = Empleado.objects.create(
            cedula='555555555', nombre='Pedro Nuevo',
            email='pedro@chocoflow.com', direccion='Calle 7',
            estado='Activo', creado_por=self.admin_perfil,
        )

        resp = self.client.post(reverse('guardar_rotacion'), {
            'empleado_id'  : emp2.id,
            'turno_id'     : self.turno_tarde.id,
            'fecha_inicio' : prox_lunes.isoformat(),
            'fecha_fin'    : prox_domingo.isoformat(),
            'semana'       : prox_semana,
            'estado'       : 'Pendiente',
        })
        self.assertRedirects(resp, reverse('turnos'))
        self.assertTrue(
            RotacionTurno.objects.filter(empleado=emp2, semana=prox_semana).exists()
        )

    def test_crear_rotacion_semana_pasada_rechazada(self):
        """No se puede crear rotación en semana anterior."""
        self.login_admin()
        hoy          = date.today()
        ant_lunes    = hoy - timedelta(days=hoy.weekday()) - timedelta(weeks=1)
        ant_domingo  = ant_lunes + timedelta(days=6)
        ant_semana   = ant_lunes.isocalendar()[1]

        emp3 = Empleado.objects.create(
            cedula='444444444', nombre='Luis Pasado',
            email='luis@chocoflow.com', direccion='Calle 8',
            estado='Activo', creado_por=self.admin_perfil,
        )

        self.client.post(reverse('guardar_rotacion'), {
            'empleado_id': emp3.id,
            'turno_id'   : self.turno_tarde.id,
            'fecha_inicio': ant_lunes.isoformat(),
            'fecha_fin'  : ant_domingo.isoformat(),
            'semana'     : ant_semana,
            'estado'     : 'Pendiente',
        })
        self.assertFalse(
            RotacionTurno.objects.filter(empleado=emp3).exists()
        )

    def test_crear_rotacion_duplicada_rechazada(self):
        """No puede existir dos rotaciones para el mismo empleado/período."""
        self.login_admin()
        rot_existente = self.rotacion

        self.client.post(reverse('guardar_rotacion'), {
            'empleado_id': self.empleado.id,
            'turno_id'   : self.turno_tarde.id,
            'fecha_inicio': rot_existente.fecha_inicio.isoformat(),
            'fecha_fin'  : rot_existente.fecha_fin.isoformat(),
            'semana'     : rot_existente.semana,
            'estado'     : 'Pendiente',
        })
        self.assertEqual(
            RotacionTurno.objects.filter(empleado=self.empleado).count(), 1
        )

    def test_eliminar_rotacion(self):
        self.login_admin()
        resp = self.client.get(reverse('eliminar_rotacion', args=[self.rotacion.id]))
        self.assertRedirects(resp, reverse('turnos'))
        self.assertFalse(RotacionTurno.objects.filter(id=self.rotacion.id).exists())


# ============================================================
# 5. SOLICITUDES
# ============================================================

class SolicitudTests(ChocoFlowTestBase):

    def test_listar_solicitudes(self):
        self.login_admin()
        resp = self.client.get(reverse('solicitudes'))
        self.assertEqual(resp.status_code, 200)

    def test_crear_solicitud_exitosa(self):
        self.login_admin()
        resp = self.client.post(reverse('guardar_solicitud'), {
            'empleado_id'        : self.empleado.id,
            'turno_actual_id'    : self.turno_mañana.id,
            'turno_solicitado_id': self.turno_tarde.id,
            'motivo'             : 'Necesito cambiar turno por cita médica urgente.',
        })
        self.assertRedirects(resp, reverse('solicitudes'))
        self.assertEqual(Solicitud.objects.count(), 1)

    def test_crear_solicitud_mismo_turno_rechazada(self):
        self.login_admin()
        self.client.post(reverse('guardar_solicitud'), {
            'empleado_id'        : self.empleado.id,
            'turno_actual_id'    : self.turno_mañana.id,
            'turno_solicitado_id': self.turno_mañana.id,  # igual
            'motivo'             : 'Motivo cualquiera suficientemente largo.',
        })
        self.assertEqual(Solicitud.objects.count(), 0)

    def test_crear_solicitud_motivo_corto_rechazada(self):
        self.login_admin()
        self.client.post(reverse('guardar_solicitud'), {
            'empleado_id'        : self.empleado.id,
            'turno_actual_id'    : self.turno_mañana.id,
            'turno_solicitado_id': self.turno_tarde.id,
            'motivo'             : 'Corto',    # < 10 caracteres
        })
        self.assertEqual(Solicitud.objects.count(), 0)

    def _crear_solicitud(self):
        return Solicitud.objects.create(
            empleado         = self.empleado,
            turno_actual     = self.turno_mañana,
            turno_solicitado = self.turno_tarde,
            motivo           = 'Motivo de prueba suficientemente largo.',
            estado           = 'Pendiente',
        )

    def test_aprobar_solicitud(self):
        self.login_admin()
        sol = self._crear_solicitud()
        self.client.post(reverse('revisar_solicitud', args=[sol.id]), {
            'estado': 'Aprobado',
        })
        sol.refresh_from_db()
        self.assertEqual(sol.estado, 'Aprobado')

    def test_rechazar_solicitud(self):
        self.login_admin()
        sol = self._crear_solicitud()
        self.client.post(reverse('revisar_solicitud', args=[sol.id]), {
            'estado': 'Rechazado',
        })
        sol.refresh_from_db()
        self.assertEqual(sol.estado, 'Rechazado')

    def test_estado_invalido_no_cambia(self):
        self.login_admin()
        sol = self._crear_solicitud()
        self.client.post(reverse('revisar_solicitud', args=[sol.id]), {
            'estado': 'Inventado',
        })
        sol.refresh_from_db()
        self.assertEqual(sol.estado, 'Pendiente')


# ============================================================
# 6. ASIGNACIONES
# ============================================================

class AsignacionTests(ChocoFlowTestBase):

    def _payload_asignacion(self, fecha=None, forzar='0'):
        if fecha is None:
            fecha = date.today() + timedelta(days=1)
        return {
            'tarea'            : 'Temperar',
            'fecha_asignacion' : fecha.isoformat(),
            'empleado_id'      : self.empleado.id,
            'turno_id'         : self.turno_mañana.id,
            'estado'           : 'Pendiente',
            'forzar'           : forzar,
        }

    def test_listar_asignaciones(self):
        self.login_admin()
        resp = self.client.get(reverse('asignaciones'))
        self.assertEqual(resp.status_code, 200)

    def test_crear_asignacion_exitosa(self):
        self.login_admin()
        resp = self.client.post(reverse('guardar_asignacion'), self._payload_asignacion())
        self.assertRedirects(resp, reverse('asignaciones'))
        self.assertEqual(Asignacion.objects.count(), 1)

    def test_asignacion_fecha_pasada_rechazada(self):
        self.login_admin()
        ayer = date.today() - timedelta(days=1)
        self.client.post(reverse('guardar_asignacion'), self._payload_asignacion(fecha=ayer))
        self.assertEqual(Asignacion.objects.count(), 0)

    def test_limite_2_tareas_admin_muestra_confirmacion(self):
        """Al llegar a 2 tareas, el admin ve modal de confirmación."""
        self.login_admin()
        fecha = date.today() + timedelta(days=1)
        # Primera y segunda tarea sin problema
        for tarea in ['Temperar', 'Mezclado']:
            Asignacion.objects.create(
                tarea            = tarea,
                fecha_asignacion = fecha,
                empleado         = self.empleado,
                turno            = self.turno_mañana,
                asignado_por     = self.admin_perfil,
                estado           = 'Pendiente',
            )
        # Tercera sin forzar → debe devolver página con confirmar_extra
        resp = self.client.post(
            reverse('guardar_asignacion'),
            self._payload_asignacion(fecha=fecha, forzar='0'),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context.get('confirmar_extra'))
        self.assertEqual(Asignacion.objects.count(), 2)

    def test_limite_2_tareas_admin_forzar(self):
        """Con forzar=1 el admin puede superar el límite de 2 tareas."""
        self.login_admin()
        fecha = date.today() + timedelta(days=1)
        for tarea in ['Temperar', 'Mezclado']:
            Asignacion.objects.create(
                tarea=tarea, fecha_asignacion=fecha,
                empleado=self.empleado, turno=self.turno_mañana,
                asignado_por=self.admin_perfil, estado='Pendiente',
            )
        resp = self.client.post(
            reverse('guardar_asignacion'),
            self._payload_asignacion(fecha=fecha, forzar='1'),
        )
        self.assertRedirects(resp, reverse('asignaciones'))
        self.assertEqual(Asignacion.objects.count(), 3)

    def test_asignacion_turno_incorrecto_rechazada(self):
        """Turno que no coincide con la rotación del empleado → error."""
        self.login_admin()
        payload = self._payload_asignacion()
        payload['turno_id'] = self.turno_tarde.id   # el empleado está en mañana
        self.client.post(reverse('guardar_asignacion'), payload)
        self.assertEqual(Asignacion.objects.count(), 0)

    def test_inactivar_asignacion(self):
        self.login_admin()
        asig = Asignacion.objects.create(
            tarea='Temperar',
            fecha_asignacion=date.today() + timedelta(days=1),
            empleado=self.empleado,
            turno=self.turno_mañana,
            asignado_por=self.admin_perfil,
            estado='Pendiente',
        )
        resp = self.client.get(reverse('inactivar_asignacion', args=[asig.id]))
        self.assertRedirects(resp, reverse('asignaciones'))
        asig.refresh_from_db()
        self.assertEqual(asig.estado, 'Finalizado')

    # ── Supervisor: límite duro de 2 ─────────────────────────────
    def test_supervisor_limite_2_tareas_duro(self):
        self.login_supervisor()
        fecha = date.today() + timedelta(days=1)
        for tarea in ['Temperar', 'Mezclado']:
            Asignacion.objects.create(
                tarea=tarea, fecha_asignacion=fecha,
                empleado=self.empleado, turno=self.turno_mañana,
                asignado_por=self.sup_perfil, estado='Pendiente',
            )
        resp = self.client.post(reverse('guardar_asignacion_supervisor'), {
            'tarea'           : 'Moldear',
            'fecha_asignacion': fecha.isoformat(),
            'empleado_id'     : self.empleado.id,
            'turno_id'        : self.turno_mañana.id,
        })
        # El supervisor no puede forzar → sigue en 2
        self.assertEqual(Asignacion.objects.count(), 2)


# ============================================================
# 7. PRODUCCIÓN
# ============================================================

class ProduccionTests(ChocoFlowTestBase):

    def test_listar_producciones(self):
        self.login_admin()
        resp = self.client.get(reverse('producciones'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.produccion, resp.context['producciones'])

    def test_crear_produccion_exitosa(self):
        self.login_admin()
        hoy = date.today()
        resp = self.client.post(reverse('guardar_produccion'), {
            'producto'            : 'Trufa rellena',
            'ingredientes'        : 'Crema, cacao',
            'cantidad_requerida'  : '50',
            'fecha_entrega'       : (hoy + timedelta(days=5)).isoformat(),
            'fecha_limite'        : (hoy + timedelta(days=10)).isoformat(),
            'estado'              : 'Pendiente',
            'empleado_responsable': self.empleado.id,
        })
        self.assertRedirects(resp, reverse('producciones'))
        self.assertTrue(Produccion.objects.filter(producto='Trufa rellena').exists())

    def test_crear_produccion_fecha_limite_anterior_rechazada(self):
        self.login_admin()
        hoy = date.today()
        self.client.post(reverse('guardar_produccion'), {
            'producto'            : 'Producto Malo',
            'ingredientes'        : 'Cacao',
            'fecha_entrega'       : (hoy + timedelta(days=5)).isoformat(),
            'fecha_limite'        : (hoy + timedelta(days=2)).isoformat(),  # anterior
            'estado'              : 'Pendiente',
            'empleado_responsable': self.empleado.id,
        })
        self.assertFalse(Produccion.objects.filter(producto='Producto Malo').exists())

    def test_crear_produccion_semana_anterior_rechazada(self):
        self.login_admin()
        hoy          = date.today()
        semana_pasada = hoy - timedelta(days=hoy.weekday()) - timedelta(weeks=1)
        self.client.post(reverse('guardar_produccion'), {
            'producto'            : 'Producto Antiguo',
            'ingredientes'        : 'Cacao',
            'fecha_entrega'       : semana_pasada.isoformat(),
            'fecha_limite'        : (semana_pasada + timedelta(days=5)).isoformat(),
            'estado'              : 'Pendiente',
            'empleado_responsable': self.empleado.id,
        })
        self.assertFalse(Produccion.objects.filter(producto='Producto Antiguo').exists())

    def test_crear_produccion_campos_vacios_rechazada(self):
        self.login_admin()
        self.client.post(reverse('guardar_produccion'), {
            'producto': '',
            'estado'  : 'Pendiente',
        })
        # Solo existe la producción creada en setUp
        self.assertEqual(Produccion.objects.count(), 1)

    def test_cancelar_produccion(self):
        self.login_admin()
        resp = self.client.get(reverse('inactivar_produccion', args=[self.produccion.id]))
        self.assertRedirects(resp, reverse('producciones'))
        self.produccion.refresh_from_db()
        self.assertEqual(self.produccion.estado, 'Cancelado')

    def test_cancelar_produccion_finalizada_bloqueada(self):
        self.login_admin()
        self.produccion.estado = 'Finalizado'
        self.produccion.save()
        self.client.get(reverse('inactivar_produccion', args=[self.produccion.id]))
        self.produccion.refresh_from_db()
        self.assertEqual(self.produccion.estado, 'Finalizado')

    def test_editar_produccion(self):
        self.login_admin()
        hoy = date.today()
        self.client.post(reverse('guardar_produccion'), {
            'id'                  : self.produccion.id,
            'producto'            : 'Chocolate editado',
            'ingredientes'        : 'Cacao, leche',
            'cantidad_requerida'  : '200',
            'fecha_entrega'       : (hoy + timedelta(days=7)).isoformat(),
            'fecha_limite'        : (hoy + timedelta(days=14)).isoformat(),
            'estado'              : 'En Proceso',
            'empleado_responsable': self.empleado.id,
        })
        self.produccion.refresh_from_db()
        self.assertEqual(self.produccion.producto, 'Chocolate editado')


# ============================================================
# 8. LOTES
# ============================================================

class LoteTests(ChocoFlowTestBase):

    def _payload_lote(self, codigo='CH-001', fecha_prod=None, fecha_venc=None):
        if fecha_prod is None:
            fecha_prod = self.produccion.fecha_entrega
        if fecha_venc is None:
            fecha_venc = fecha_prod + timedelta(days=90)
        return {
            'codigo_lote'      : codigo,
            'origen_cacao'     : 'Antioquia',
            'cantidad'         : '500',
            'unidad'           : 'Kilogramos',
            'nombre_producto'  : 'Chocolate negro',
            'fecha_produccion' : fecha_prod.isoformat(),
            'fecha_vencimiento': fecha_venc.isoformat(),
            'produccion_id'    : self.produccion.id,
        }

    def test_listar_lotes(self):
        self.login_admin()
        resp = self.client.get(reverse('gestionar_lotes'))
        self.assertEqual(resp.status_code, 200)

    def test_crear_lote_exitoso(self):
        self.login_admin()
        resp = self.client.post(reverse('guardar_lote'), self._payload_lote())
        self.assertRedirects(resp, reverse('gestionar_lotes'))
        self.assertTrue(Lote.objects.filter(codigo_lote='CH-001').exists())

    def test_crear_lote_codigo_invalido(self):
        """Código que no sigue el patrón XX-000 debe ser rechazado."""
        self.login_admin()
        self.client.post(reverse('guardar_lote'), self._payload_lote(codigo='MALO'))
        self.assertFalse(Lote.objects.filter(codigo_lote='MALO').exists())

    def test_crear_lote_codigo_duplicado(self):
        self.login_admin()
        self.client.post(reverse('guardar_lote'), self._payload_lote('AB-001'))
        self.client.post(reverse('guardar_lote'), self._payload_lote('AB-001'))  # duplicado
        self.assertEqual(Lote.objects.filter(codigo_lote='AB-001').count(), 1)

    def test_crear_lote_fecha_produccion_no_coincide(self):
        """La fecha de producción del lote debe coincidir con fecha_entrega de la producción."""
        self.login_admin()
        payload = self._payload_lote('ZZ-001')
        payload['fecha_produccion'] = (self.produccion.fecha_entrega + timedelta(days=1)).isoformat()
        self.client.post(reverse('guardar_lote'), payload)
        self.assertFalse(Lote.objects.filter(codigo_lote='ZZ-001').exists())

    def test_crear_lote_vencimiento_anterior_produccion(self):
        self.login_admin()
        fecha_prod = self.produccion.fecha_entrega
        payload = self._payload_lote('YY-001', fecha_prod=fecha_prod,
                                     fecha_venc=fecha_prod - timedelta(days=1))
        self.client.post(reverse('guardar_lote'), payload)
        self.assertFalse(Lote.objects.filter(codigo_lote='YY-001').exists())

    def test_eliminar_lote(self):
        self.login_admin()
        lote = Lote.objects.create(
            codigo_lote='EL-001',
            cantidad='100',
            fecha_produccion=self.produccion.fecha_entrega,
            fecha_vencimiento=self.produccion.fecha_entrega + timedelta(days=90),
            produccion=self.produccion,
        )
        resp = self.client.get(reverse('eliminar_lote', args=[lote.id]))
        self.assertRedirects(resp, reverse('gestionar_lotes'))
        self.assertFalse(Lote.objects.filter(id=lote.id).exists())


# ============================================================
# 9. EXPORTACIONES
# ============================================================

class ExportacionTests(ChocoFlowTestBase):

    def setUp(self):
        super().setUp()
        # Lote base para las exportaciones
        self.lote = Lote.objects.create(
            codigo_lote       = 'EX-001',
            cantidad          = '200',
            fecha_produccion  = self.produccion.fecha_entrega,
            fecha_vencimiento = self.produccion.fecha_entrega + timedelta(days=180),
            produccion        = self.produccion,
        )

    def _payload_exportacion(self, **kwargs):
        fecha_envio    = self.produccion.fecha_entrega + timedelta(days=1)
        fecha_entrega  = fecha_envio + timedelta(days=10)
        base = {
            'destino'          : 'Bélgica',
            'pais'             : 'Bélgica',
            'fecha_envio'      : fecha_envio.isoformat(),
            'fecha_entrega'    : fecha_entrega.isoformat(),
            'estado'           : 'Pendiente',
            'produccion_id'    : self.produccion.id,
            'lote_id'          : self.lote.id,
        }
        base.update(kwargs)
        return base

    def test_listar_exportaciones(self):
        self.login_admin()
        resp = self.client.get(reverse('gestionar_exportaciones'))
        self.assertEqual(resp.status_code, 200)

    def test_crear_exportacion_exitosa(self):
        self.login_admin()
        resp = self.client.post(reverse('guardar_exportacion'), self._payload_exportacion())
        self.assertRedirects(resp, reverse('gestionar_exportaciones'))
        self.assertTrue(Exportacion.objects.filter(destino='Bélgica').exists())

    def test_crear_exportacion_destino_con_numeros_rechazada(self):
        self.login_admin()
        self.client.post(reverse('guardar_exportacion'),
                         self._payload_exportacion(destino='B3lgica'))
        self.assertFalse(Exportacion.objects.filter(destino='B3lgica').exists())

    def test_crear_exportacion_fecha_entrega_anterior_envio(self):
        self.login_admin()
        fecha_envio   = self.produccion.fecha_entrega + timedelta(days=5)
        fecha_entrega = fecha_envio - timedelta(days=2)    # anterior → error
        self.client.post(reverse('guardar_exportacion'), self._payload_exportacion(
            fecha_envio=fecha_envio.isoformat(),
            fecha_entrega=fecha_entrega.isoformat(),
        ))
        self.assertEqual(Exportacion.objects.count(), 0)

    def test_crear_exportacion_fecha_envio_antes_produccion(self):
        """Fecha de envío no puede ser anterior a fecha_entrega de la producción."""
        self.login_admin()
        fecha_envio = self.produccion.fecha_entrega - timedelta(days=1)
        self.client.post(reverse('guardar_exportacion'), self._payload_exportacion(
            fecha_envio=fecha_envio.isoformat(),
            fecha_entrega=(fecha_envio + timedelta(days=5)).isoformat(),
        ))
        self.assertEqual(Exportacion.objects.count(), 0)

    def test_crear_exportacion_lote_no_pertenece_produccion(self):
        """Lote de otra producción → error."""
        self.login_admin()
        otra_prod = Produccion.objects.create(
            producto='Otro producto', ingredientes='Cacao',
            fecha_entrega=date.today() + timedelta(days=3),
            fecha_limite=date.today() + timedelta(days=10),
            estado='Pendiente',
            empleado_responsable=self.empleado,
            creado_por=self.admin_perfil,
        )
        otro_lote = Lote.objects.create(
            codigo_lote='OT-001', cantidad='50',
            fecha_produccion=otra_prod.fecha_entrega,
            fecha_vencimiento=otra_prod.fecha_entrega + timedelta(days=60),
            produccion=otra_prod,
        )
        self.client.post(reverse('guardar_exportacion'), self._payload_exportacion(
            produccion_id=self.produccion.id,
            lote_id=otro_lote.id,     # lote de otra producción
        ))
        self.assertEqual(Exportacion.objects.count(), 0)

    def test_cancelar_exportacion(self):
        self.login_admin()
        exp = Exportacion.objects.create(
            destino='Alemania', pais='Alemania',
            fecha_envio=self.produccion.fecha_entrega + timedelta(days=2),
            fecha_entrega=self.produccion.fecha_entrega + timedelta(days=12),
            estado='Pendiente',
            produccion=self.produccion,
            lote=self.lote,
        )
        resp = self.client.get(reverse('inactivar_exportacion', args=[exp.id]))
        self.assertRedirects(resp, reverse('gestionar_exportaciones'))
        exp.refresh_from_db()
        self.assertEqual(exp.estado, 'Cancelado')


# ============================================================
# 10. BITÁCORA
# ============================================================

class BitacoraTests(ChocoFlowTestBase):

    def _payload_bitacora(self, estado='Borrador'):
        return {
            'titulo'             : 'Reporte del turno de hoy',
            'descripcion'        : 'Se completó el proceso de templado y moldeo sin novedades.',
            'tipo_reporte'       : 'Diario',
            'produccion'         : self.produccion.id,
            'unidades_producidas': '80',
            'unidades_pendientes': '20',
            'observaciones'      : 'Sin novedad.',
            'estado'             : estado,
        }

    def test_listar_bitacoras_admin(self):
        self.login_admin()
        resp = self.client.get(reverse('listar_bitacoras'))
        self.assertEqual(resp.status_code, 200)

    def test_crear_bitacora_borrador(self):
        self.login_supervisor()
        resp = self.client.post(reverse('bitacora_supervisor'), self._payload_bitacora('Borrador'))
        self.assertRedirects(resp, reverse('listar_bitacoras_supervisor'))
        self.assertEqual(Bitacora.objects.filter(estado='Borrador').count(), 1)

    def test_crear_bitacora_y_enviar(self):
        self.login_supervisor()
        self.client.post(reverse('bitacora_supervisor'), self._payload_bitacora('Enviado'))
        self.assertEqual(Bitacora.objects.filter(estado='Enviado').count(), 1)

    def test_crear_bitacora_titulo_corto_rechazada(self):
        self.login_supervisor()
        payload = self._payload_bitacora()
        payload['titulo'] = 'Hoy'   # < 5 caracteres
        self.client.post(reverse('bitacora_supervisor'), payload)
        self.assertEqual(Bitacora.objects.count(), 0)

    def test_crear_bitacora_descripcion_corta_rechazada(self):
        self.login_supervisor()
        payload = self._payload_bitacora()
        payload['descripcion'] = 'Muy corta.'   # < 20 caracteres
        self.client.post(reverse('bitacora_supervisor'), payload)
        self.assertEqual(Bitacora.objects.count(), 0)

    def test_enviar_bitacora_borrador(self):
        """Envío explícito de una bitácora en Borrador."""
        self.login_supervisor()
        bitacora = Bitacora.objects.create(
            titulo='Bitácora de prueba',
            descripcion='Descripción suficientemente larga para la prueba.',
            tipo_reporte='Diario',
            estado='Borrador',
            supervisor=self.sup_perfil,
            produccion=self.produccion,
            unidades_producidas='60',
            unidades_pendientes='40',
        )
        resp = self.client.get(reverse('enviar_bitacora', args=[bitacora.id]))
        self.assertRedirects(resp, reverse('listar_bitacoras_supervisor'))
        bitacora.refresh_from_db()
        self.assertEqual(bitacora.estado, 'Enviado')

    def test_no_puede_enviar_bitacora_ya_enviada(self):
        self.login_supervisor()
        bitacora = Bitacora.objects.create(
            titulo='Ya enviada',
            descripcion='Descripción suficientemente larga para la prueba.',
            tipo_reporte='Diario',
            estado='Enviado',
            supervisor=self.sup_perfil,
            produccion=self.produccion,
            unidades_producidas='60',
            unidades_pendientes='40',
        )
        self.client.get(reverse('enviar_bitacora', args=[bitacora.id]))
        bitacora.refresh_from_db()
        self.assertEqual(bitacora.estado, 'Enviado')   # no cambia a otro estado

    def test_aprobar_bitacora(self):
        self.login_admin()
        bitacora = Bitacora.objects.create(
            titulo='Para aprobar',
            descripcion='Descripción suficientemente larga para la prueba.',
            tipo_reporte='Diario',
            estado='Enviado',
            supervisor=self.sup_perfil,
            produccion=self.produccion,
            unidades_producidas='70',
            unidades_pendientes='30',
        )
        resp = self.client.post(reverse('revisar_bitacora', args=[bitacora.id]), {
            'estado'           : 'Aprobado',
            'observacion_admin': 'Todo correcto.',
        })
        self.assertRedirects(resp, reverse('listar_bitacoras'))
        bitacora.refresh_from_db()
        self.assertEqual(bitacora.estado, 'Aprobado')

    def test_rechazar_bitacora(self):
        self.login_admin()
        bitacora = Bitacora.objects.create(
            titulo='Para rechazar',
            descripcion='Descripción suficientemente larga para la prueba.',
            tipo_reporte='Diario',
            estado='Enviado',
            supervisor=self.sup_perfil,
            produccion=self.produccion,
            unidades_producidas='10',
            unidades_pendientes='90',
        )
        self.client.post(reverse('revisar_bitacora', args=[bitacora.id]), {
            'estado'           : 'Rechazado',
            'observacion_admin': 'Faltan datos importantes.',
        })
        bitacora.refresh_from_db()
        self.assertEqual(bitacora.estado, 'Rechazado')

    def test_no_revisar_bitacora_ya_revisada(self):
        self.login_admin()
        bitacora = Bitacora.objects.create(
            titulo='Ya revisada',
            descripcion='Descripción suficientemente larga para la prueba.',
            tipo_reporte='Diario',
            estado='Aprobado',   # ya fue revisada
            supervisor=self.sup_perfil,
            produccion=self.produccion,
            unidades_producidas='50',
            unidades_pendientes='50',
        )
        self.client.post(reverse('revisar_bitacora', args=[bitacora.id]), {
            'estado': 'Rechazado',
        })
        bitacora.refresh_from_db()
        self.assertEqual(bitacora.estado, 'Aprobado')   # no cambió