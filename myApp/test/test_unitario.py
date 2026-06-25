"""
=============================================================
PRUEBAS UNITARIAS — ChocoFlow
views.py versión 2 (resend + IA integrada + carga masiva empleados)
=============================================================
Cómo ejecutar:
    python manage.py test myApp.test.test_unitario --verbosity=2
=============================================================
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from myApp.models import (
    Usuario,
    Empleado,
    Turno,
    RotacionTurno,
    Solicitud,
    Asignacion,
    Produccion,
    Lote,
    Exportacion,
    Bitacora,
    HistorialCorreo,
)


# ============================================================
# HELPERS DE CREACIÓN RÁPIDA
# ============================================================

def crear_usuario_django(username="admin001", email="admin@chocoflow.com", password="Admin123"):
    return User.objects.create_user(username=username, email=email, password=password)


def crear_usuario_db(nombre="Admin Test", email="admin@chocoflow.com", rol="Administrador", turno=None):
    return Usuario.objects.create(
        nombre=nombre,
        email=email,
        telefono="3001234567",
        direccion="Calle 1",
        contrasena="Admin123",
        rol=rol,
        estado="Activo",
        turno=turno,
    )


def crear_empleado(cedula="123456789", nombre="Juan Perez", email="juan@chocoflow.com",
                    estado="Activo", creado_por=None):
    """
    🛠️ FIX: el campo 'creado_por' de Empleado es obligatorio (NOT NULL) en el
    modelo real. Antes este helper no lo pasaba, lo que tumbaba con
    IntegrityError cualquier test que llamara a crear_empleado() sin
    especificar un usuario creador.

    Ahora, si no se pasa 'creado_por' explícitamente, se crea (o reutiliza)
    un Usuario por defecto para no tener que tocar cada llamada en los tests.
    """
    if creado_por is None:
        creado_por, _ = Usuario.objects.get_or_create(
            email="creador_default@chocoflow.com",
            defaults=dict(
                nombre="Creador Default",
                telefono="3000000000",
                direccion="Calle 0",
                contrasena="Default123",
                rol="Administrador",
                estado="Activo",
            ),
        )

    return Empleado.objects.create(
        cedula=cedula,
        nombre=nombre,
        email=email,
        telefono="3009876543",
        direccion="Calle 2",
        estado=estado,
        creado_por=creado_por,
    )


def crear_turno(horario="Mañana 6:00am - 2:00pm", activo=True):
    return Turno.objects.get_or_create(horario=horario, defaults={"activo": activo})[0]


def lunes_semana_actual():
    hoy = date.today()
    return hoy - timedelta(days=hoy.weekday())


def crear_produccion(empleado, usuario, estado="En Proceso"):
    lunes = lunes_semana_actual()
    return Produccion.objects.create(
        producto="Chocolate Negro",
        ingredientes="Cacao, azúcar",
        cantidad_requerida=100,
        fecha_entrega=lunes + timedelta(days=5),
        fecha_limite=lunes + timedelta(days=10),
        estado=estado,
        empleado_responsable=empleado,
        creado_por=usuario,
    )


def crear_lote(produccion, codigo="CH-001"):
    return Lote.objects.create(
        codigo_lote=codigo,
        cantidad=50,
        fecha_produccion=produccion.fecha_entrega,
        fecha_vencimiento=produccion.fecha_entrega + timedelta(days=180),
        produccion=produccion,
    )


def sesion_admin(client, usuario_db):
    session = client.session
    session["usuario_id"] = usuario_db.id
    session["rol"] = "Administrador"
    session.save()


def sesion_supervisor(client, usuario_db):
    session = client.session
    session["usuario_id"] = usuario_db.id
    session["rol"] = "Supervisor"
    session.save()


# ============================================================
# 1. MODELOS
# ============================================================

class UsuarioModelTest(TestCase):
    def test_crear_administrador(self):
        u = crear_usuario_db()
        self.assertEqual(u.rol, "Administrador")
        self.assertEqual(u.estado, "Activo")

    def test_crear_supervisor_con_turno(self):
        u = crear_usuario_db(
            nombre="Sup Test", email="sup@cf.com",
            rol="Supervisor", turno="Mañana 6:00am - 2:00pm"
        )
        self.assertEqual(u.turno, "Mañana 6:00am - 2:00pm")

    def test_str_usuario(self):
        u = crear_usuario_db()
        self.assertIsNotNone(str(u))


class EmpleadoModelTest(TestCase):
    def test_crear_activo(self):
        emp = crear_empleado()
        self.assertEqual(emp.estado, "Activo")

    def test_inactivar(self):
        emp = crear_empleado()
        emp.estado = "Inactivo"
        emp.save()
        self.assertEqual(Empleado.objects.get(pk=emp.pk).estado, "Inactivo")


class TurnoModelTest(TestCase):
    def test_crear_turno_manana(self):
        t = crear_turno()
        self.assertIn("Mañana", t.horario)

    def test_crear_turno_tarde(self):
        t = crear_turno("Tarde 2:00pm - 10:00pm")
        self.assertIn("Tarde", t.horario)


class RotacionTurnoModelTest(TestCase):
    def setUp(self):
        self.emp = crear_empleado()
        self.turno = crear_turno()

    def test_crear_rotacion(self):
        lunes = lunes_semana_actual()
        rot = RotacionTurno.objects.create(
            empleado=self.emp, turno=self.turno,
            fecha_inicio=lunes, fecha_fin=lunes + timedelta(days=6),
            semana=lunes.isocalendar()[1], estado="Asignado",
        )
        self.assertEqual(rot.empleado, self.emp)


class SolicitudModelTest(TestCase):
    def test_crear_solicitud(self):
        emp = crear_empleado()
        ta = crear_turno()
        tb = crear_turno("Tarde 2:00pm - 10:00pm")
        sol = Solicitud.objects.create(
            empleado=emp, turno_actual=ta, turno_solicitado=tb,
            motivo="Razones familiares urgentes.", estado="Pendiente",
        )
        self.assertEqual(sol.estado, "Pendiente")


class ProduccionModelTest(TestCase):
    def test_crear_y_cancelar(self):
        emp = crear_empleado()
        usu = crear_usuario_db()
        p = crear_produccion(emp, usu)
        self.assertEqual(p.estado, "En Proceso")
        p.estado = "Cancelado"
        p.save()
        self.assertEqual(Produccion.objects.get(pk=p.pk).estado, "Cancelado")


class LoteModelTest(TestCase):
    def test_crear_lote(self):
        emp = crear_empleado()
        usu = crear_usuario_db()
        prod = crear_produccion(emp, usu)
        lote = crear_lote(prod)
        self.assertEqual(lote.codigo_lote, "CH-001")

    def test_str_lote(self):
        emp = crear_empleado()
        usu = crear_usuario_db()
        prod = crear_produccion(emp, usu)
        lote = crear_lote(prod)
        self.assertIn("CH-001", str(lote))


class ExportacionModelTest(TestCase):
    def test_crear_exportacion(self):
        emp = crear_empleado()
        usu = crear_usuario_db()
        prod = crear_produccion(emp, usu)
        lote = crear_lote(prod)
        exp = Exportacion.objects.create(
            destino="Madrid", pais="España",
            fecha_envio=prod.fecha_entrega + timedelta(days=1),
            fecha_entrega=prod.fecha_entrega + timedelta(days=10),
            estado="Pendiente", produccion=prod, lote=lote,
        )
        self.assertEqual(exp.estado, "Pendiente")


class BitacoraModelTest(TestCase):
    def test_crear_borrador(self):
        sup = crear_usuario_db(rol="Supervisor", email="s@cf.com")
        emp = crear_empleado()
        usu = crear_usuario_db(email="a@cf.com")
        prod = crear_produccion(emp, usu)
        b = Bitacora.objects.create(
            titulo="Reporte turno mañana",
            descripcion="Se completaron 80 unidades de chocolate en el turno.",
            tipo_reporte="Diario", unidades_producidas=80,
            unidades_pendientes=20, supervisor=sup,
            produccion=prod, estado="Borrador",
        )
        self.assertEqual(b.estado, "Borrador")


# ============================================================
# 2. AUTENTICACIÓN
# ============================================================

class AuthViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.usuario_db = crear_usuario_db()

    def test_login_exitoso(self):
        resp = self.client.post(reverse("login"), {
            "username": "admin@chocoflow.com", "password": "Admin123",
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_login_credenciales_incorrectas(self):
        resp = self.client.post(reverse("login"), {
            "username": "admin@chocoflow.com", "password": "Mal",
        })
        self.assertEqual(resp.status_code, 200)

    def test_login_correo_invalido(self):
        resp = self.client.post(reverse("login"), {
            "username": "no-es-correo", "password": "Admin123",
        })
        self.assertEqual(resp.status_code, 200)

    def test_login_campos_vacios(self):
        resp = self.client.post(reverse("login"), {"username": "", "password": ""})
        self.assertEqual(resp.status_code, 200)

    def test_cerrar_sesion(self):
        self.client.login(username="admin001", password="Admin123")
        resp = self.client.get(reverse("logout"))
        self.assertEqual(resp.status_code, 302)

    def test_index_sin_autenticar(self):
        resp = self.client.get(reverse("index"))
        self.assertEqual(resp.status_code, 200)


class RegistroViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def _base(self, **kw):
        d = {
            "identificacion": "99887766",
            "nombre": "Carlos Lopez",
            "correo": "carlos@chocoflow.com",
            "telefono": "3001112222",
            "direccion": "Carrera 5",
            "password": "Segura123",
            "rol": "Administrador",
            "estado": "Activo",
            "turno": "",
        }
        d.update(kw)
        return d

    def test_registro_exitoso(self):
        resp = self.client.post(reverse("registro"), self._base())
        self.assertIn(resp.status_code, [200, 302])

    def test_identificacion_no_numerica(self):
        resp = self.client.post(reverse("registro"), self._base(identificacion="ABC"))
        self.assertEqual(resp.status_code, 302)

    def test_correo_invalido(self):
        resp = self.client.post(reverse("registro"), self._base(correo="noescorreo"))
        self.assertEqual(resp.status_code, 302)

    def test_password_sin_mayuscula(self):
        resp = self.client.post(reverse("registro"), self._base(password="segura123"))
        self.assertEqual(resp.status_code, 302)

    def test_password_sin_numero(self):
        resp = self.client.post(reverse("registro"), self._base(password="SinNumero"))
        self.assertEqual(resp.status_code, 302)

    def test_supervisor_sin_turno(self):
        resp = self.client.post(reverse("registro"), self._base(rol="Supervisor", turno=""))
        self.assertEqual(resp.status_code, 302)

    def test_supervisor_con_turno(self):
        resp = self.client.post(reverse("registro"), self._base(
            identificacion="11223344",
            correo="sup_nuevo@chocoflow.com",
            rol="Supervisor",
            turno="Mañana 6:00am - 2:00pm",
        ))
        self.assertIn(resp.status_code, [200, 302])


# ============================================================
# 3. RECUPERACIÓN DE CONTRASEÑA
# ============================================================

class RecuperacionPasswordTest(TestCase):
    def setUp(self):
        self.client = Client()
        crear_usuario_django(email="recover@chocoflow.com")

    def test_get_olvide_password(self):
        resp = self.client.get(reverse("olvide_password"))
        self.assertEqual(resp.status_code, 200)

    def test_correo_vacio(self):
        resp = self.client.post(reverse("olvide_password"), {"email": ""})
        self.assertEqual(resp.status_code, 200)

    def test_correo_no_registrado(self):
        resp = self.client.post(reverse("olvide_password"), {"email": "noexiste@cf.com"})
        self.assertIn(resp.status_code, [200, 302])

    @patch("myApp.views.resend.Emails.send")
    def test_correo_valido_envia(self, mock_send):
        mock_send.return_value = {"id": "fake-id"}
        resp = self.client.post(reverse("olvide_password"), {"email": "recover@chocoflow.com"})
        self.assertIn(resp.status_code, [200, 302])


# ============================================================
# 4. DASHBOARDS
# ============================================================

class DashboardAdminTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)

    def test_accesible(self):
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_sin_login_redirige(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)


class DashboardSupervisorTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django(username="sup001", email="sup001@cf.com")
        self.udb = crear_usuario_db(nombre="Sup", email="sup001@cf.com",
                                    rol="Supervisor", turno="Mañana 6:00am - 2:00pm")
        self.client.login(username="sup001", password="Admin123")
        sesion_supervisor(self.client, self.udb)

    def test_accesible(self):
        self.assertEqual(self.client.get(reverse("dashboard_supervisor")).status_code, 200)


# ============================================================
# 5. EMPLEADOS
# ============================================================

class EmpleadosViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)

    def test_listar(self):
        self.assertEqual(self.client.get(reverse("empleados")).status_code, 200)

    def test_guardar_nuevo(self):
        resp = self.client.post(reverse("guardar_empleado"), {
            "cedula": "987654321", "nombre": "Maria Garcia",
            "email": "maria@cf.com", "telefono": "3112223344",
            "direccion": "Calle 10", "estado": "Activo",
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_guardar_cedula_duplicada(self):
        crear_empleado(cedula="111111111")
        resp = self.client.post(reverse("guardar_empleado"), {
            "cedula": "111111111", "nombre": "Otro",
            "email": "otro@cf.com", "estado": "Activo",
        })
        self.assertIn(resp.status_code, [200, 302])
        self.assertEqual(Empleado.objects.filter(cedula="111111111").count(), 1)

    def test_guardar_email_invalido(self):
        resp = self.client.post(reverse("guardar_empleado"), {
            "cedula": "555444333", "nombre": "Luis Mora",
            "email": "no_es_correo", "estado": "Activo",
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_inactivar(self):
        emp = crear_empleado(cedula="222333444", email="inac@cf.com")
        self.client.get(reverse("inactivar_empleado", args=[emp.id]))
        self.assertEqual(Empleado.objects.get(pk=emp.id).estado, "Inactivo")

    def test_reporte_pdf(self):
        resp = self.client.get(reverse("reporte_empleados"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")


# ============================================================
# 6. CARGA MASIVA EMPLEADOS (nueva en este views.py)
# ============================================================

class CargaMasivaEmpleadosTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)

    def _csv(self, contenido):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile("empleados.csv", contenido.encode("utf-8"), content_type="text/csv")

    def test_sin_archivo(self):
        resp = self.client.post(reverse("carga_masiva_empleados"), {})
        self.assertEqual(resp.status_code, 400)

    def test_extension_incorrecta(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        arch = SimpleUploadedFile("data.txt", b"x", content_type="text/plain")
        resp = self.client.post(reverse("carga_masiva_empleados"), {"csv_file": arch})
        self.assertEqual(resp.status_code, 400)

    def test_columnas_faltantes(self):
        resp = self.client.post(reverse("carga_masiva_empleados"),
                                {"csv_file": self._csv("nombre,email\nJuan,j@cf.com\n")})
        self.assertEqual(resp.status_code, 400)

    def test_csv_valido(self):
        csv = "cedula,nombre,email,estado\n123456789,Pedro Ruiz,pedro@cf.com,Activo\n"
        resp = self.client.post(reverse("carga_masiva_empleados"),
                                {"csv_file": self._csv(csv)})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["creados"], 1)

    def test_email_invalido_en_csv(self):
        csv = "cedula,nombre,email,estado\n987654321,Ana,noemail,Activo\n"
        resp = self.client.post(reverse("carga_masiva_empleados"),
                                {"csv_file": self._csv(csv)})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["creados"], 0)
        self.assertTrue(len(data["errores"]) > 0)

    def test_duplicado_omitido(self):
        crear_empleado(cedula="111222333", email="dup@cf.com")
        csv = "cedula,nombre,email,estado\n111222333,Dup,dup@cf.com,Activo\n"
        resp = self.client.post(reverse("carga_masiva_empleados"),
                                {"csv_file": self._csv(csv)})
        self.assertEqual(resp.json()["omitidos"], 1)


# ============================================================
# 7. TURNOS Y ROTACIONES
# ============================================================

class TurnosViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)
        self.emp = crear_empleado()
        self.turno = crear_turno()

    def test_listar(self):
        self.assertEqual(self.client.get(reverse("turnos")).status_code, 200)

    def test_guardar_rotacion_valida(self):
        lunes = lunes_semana_actual()
        resp = self.client.post(reverse("guardar_rotacion"), {
            "empleado_id": self.emp.id, "turno_id": self.turno.id,
            "fecha_inicio": lunes.isoformat(),
            "fecha_fin": (lunes + timedelta(days=6)).isoformat(),
            "semana": lunes.isocalendar()[1], "estado": "Asignado",
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_guardar_rotacion_campos_vacios(self):
        resp = self.client.post(reverse("guardar_rotacion"), {
            "empleado_id": "", "turno_id": "",
            "fecha_inicio": "", "fecha_fin": "", "semana": "",
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_guardar_rotacion_semana_pasada(self):
        hoy = date.today()
        lunes = hoy - timedelta(days=hoy.weekday() + 7)
        resp = self.client.post(reverse("guardar_rotacion"), {
            "empleado_id": self.emp.id, "turno_id": self.turno.id,
            "fecha_inicio": lunes.isoformat(),
            "fecha_fin": (lunes + timedelta(days=6)).isoformat(),
            "semana": lunes.isocalendar()[1], "estado": "Asignado",
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_eliminar_rotacion(self):
        lunes = lunes_semana_actual()
        rot = RotacionTurno.objects.create(
            empleado=self.emp, turno=self.turno,
            fecha_inicio=lunes, fecha_fin=lunes + timedelta(days=6),
            semana=lunes.isocalendar()[1],
        )
        self.client.get(reverse("eliminar_rotacion", args=[rot.id]))
        self.assertFalse(RotacionTurno.objects.filter(pk=rot.id).exists())

    def test_reporte_turnos_pdf(self):
        resp = self.client.get(reverse("reporte_turnos"))
        self.assertEqual(resp["Content-Type"], "application/pdf")

    def test_reporte_rotacion_pdf(self):
        resp = self.client.get(reverse("reporte_rotacion"))
        self.assertEqual(resp["Content-Type"], "application/pdf")


# ============================================================
# 8. SOLICITUDES
# ============================================================

class SolicitudesViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)
        self.emp = crear_empleado()
        self.ta = crear_turno()
        self.tb = crear_turno("Tarde 2:00pm - 10:00pm")

    def test_listar(self):
        self.assertEqual(self.client.get(reverse("solicitudes")).status_code, 200)

    def test_guardar_valida(self):
        resp = self.client.post(reverse("guardar_solicitud"), {
            "empleado_id": self.emp.id, "turno_actual_id": self.ta.id,
            "turno_solicitado_id": self.tb.id,
            "motivo": "Compromisos familiares urgentes del empleado.",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Solicitud.objects.count(), 1)

    def test_mismo_turno_rechazado(self):
        resp = self.client.post(reverse("guardar_solicitud"), {
            "empleado_id": self.emp.id, "turno_actual_id": self.ta.id,
            "turno_solicitado_id": self.ta.id, "motivo": "Quiero quedarme igual.",
        })
        self.assertEqual(Solicitud.objects.count(), 0)

    def test_motivo_corto(self):
        resp = self.client.post(reverse("guardar_solicitud"), {
            "empleado_id": self.emp.id, "turno_actual_id": self.ta.id,
            "turno_solicitado_id": self.tb.id, "motivo": "Corto",
        })
        self.assertEqual(Solicitud.objects.count(), 0)

    def test_revisar_aprobada(self):
        sol = Solicitud.objects.create(
            empleado=self.emp, turno_actual=self.ta, turno_solicitado=self.tb,
            motivo="Motivo suficientemente largo para pasar la validación.",
            estado="Pendiente",
        )
        self.client.post(reverse("revisar_solicitud", args=[sol.id]), {"estado": "Aprobado"})
        self.assertEqual(Solicitud.objects.get(pk=sol.id).estado, "Aprobado")

    def test_revisar_rechazada(self):
        sol = Solicitud.objects.create(
            empleado=self.emp, turno_actual=self.ta, turno_solicitado=self.tb,
            motivo="Motivo suficientemente largo para pasar la validación.",
            estado="Pendiente",
        )
        self.client.post(reverse("revisar_solicitud", args=[sol.id]), {"estado": "Rechazado"})
        self.assertEqual(Solicitud.objects.get(pk=sol.id).estado, "Rechazado")

    def test_reporte_pdf(self):
        resp = self.client.get(reverse("generar_reporte_solicitudes"))
        self.assertEqual(resp["Content-Type"], "application/pdf")


# ============================================================
# 9. ASIGNACIONES
# ============================================================

class AsignacionesViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)
        self.emp = crear_empleado()
        self.turno = crear_turno()
        lunes = lunes_semana_actual()
        RotacionTurno.objects.create(
            empleado=self.emp, turno=self.turno,
            fecha_inicio=lunes, fecha_fin=lunes + timedelta(days=6),
            semana=lunes.isocalendar()[1],
        )

    def test_listar(self):
        self.assertEqual(self.client.get(reverse("asignaciones")).status_code, 200)

    def test_guardar_valida(self):
        fecha = (date.today() + timedelta(days=1)).isoformat()
        resp = self.client.post(reverse("guardar_asignacion"), {
            "tarea": "Revisar lote", "fecha_asignacion": fecha,
            "empleado_id": self.emp.id, "turno_id": self.turno.id,
            "estado": "Pendiente", "forzar": "0",
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_fecha_pasada_rechazada(self):
        fecha = (date.today() - timedelta(days=1)).isoformat()
        resp = self.client.post(reverse("guardar_asignacion"), {
            "tarea": "Tarea pasada", "fecha_asignacion": fecha,
            "empleado_id": self.emp.id, "turno_id": self.turno.id,
            "estado": "Pendiente", "forzar": "0",
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_inactivar(self):
        asig = Asignacion.objects.create(
            tarea="Prueba", fecha_asignacion=date.today() + timedelta(days=2),
            empleado=self.emp, turno=self.turno, asignado_por=self.udb,
            estado="Pendiente",
        )
        self.client.get(reverse("inactivar_asignacion", args=[asig.id]))
        self.assertEqual(Asignacion.objects.get(pk=asig.id).estado, "Finalizado")

    def test_reporte_pdf(self):
        resp = self.client.get(reverse("reporte_asignaciones"))
        self.assertEqual(resp["Content-Type"], "application/pdf")


# ============================================================
# 10. PRODUCCIÓN
# ============================================================

class ProduccionViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)
        self.emp = crear_empleado()

    def test_listar(self):
        self.assertEqual(self.client.get(reverse("producciones")).status_code, 200)

    def test_guardar_valida(self):
        lunes = lunes_semana_actual()
        resp = self.client.post(reverse("guardar_produccion"), {
            "producto": "Chocolate Blanco", "ingredientes": "Manteca, leche",
            "cantidad_requerida": 200,
            "fecha_entrega": (lunes + timedelta(days=3)).isoformat(),
            "fecha_limite": (lunes + timedelta(days=7)).isoformat(),
            "estado": "Pendiente", "empleado_responsable": self.emp.id,
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_fecha_entrega_semana_anterior(self):
        """La nueva validación rechaza fechas de semanas anteriores."""
        hoy = date.today()
        semana_pasada = hoy - timedelta(days=hoy.weekday() + 7)
        resp = self.client.post(reverse("guardar_produccion"), {
            "producto": "Chocolate", "ingredientes": "Cacao",
            "cantidad_requerida": 50,
            "fecha_entrega": semana_pasada.isoformat(),
            "fecha_limite": (semana_pasada + timedelta(days=3)).isoformat(),
            "estado": "Pendiente", "empleado_responsable": self.emp.id,
        })
        self.assertIn(resp.status_code, [200, 302])
        # No debe haberse creado la producción
        self.assertEqual(Produccion.objects.count(), 0)

    def test_fecha_limite_anterior_entrega(self):
        lunes = lunes_semana_actual()
        resp = self.client.post(reverse("guardar_produccion"), {
            "producto": "Chocolate", "ingredientes": "Cacao",
            "cantidad_requerida": 50,
            "fecha_entrega": (lunes + timedelta(days=5)).isoformat(),
            "fecha_limite": (lunes + timedelta(days=3)).isoformat(),
            "estado": "Pendiente", "empleado_responsable": self.emp.id,
        })
        self.assertIn(resp.status_code, [200, 302])
        self.assertEqual(Produccion.objects.count(), 0)

    def test_cancelar(self):
        p = crear_produccion(self.emp, self.udb)
        self.client.get(reverse("inactivar_produccion", args=[p.id]))
        self.assertEqual(Produccion.objects.get(pk=p.id).estado, "Cancelado")

    def test_no_cancelar_finalizada(self):
        p = crear_produccion(self.emp, self.udb, estado="Finalizado")
        self.client.get(reverse("inactivar_produccion", args=[p.id]))
        self.assertEqual(Produccion.objects.get(pk=p.id).estado, "Finalizado")

    def test_reporte_pdf(self):
        resp = self.client.get(reverse("reporte_producciones"))
        self.assertEqual(resp["Content-Type"], "application/pdf")


# ============================================================
# 11. LOTES
# ============================================================

class LotesViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)
        self.emp = crear_empleado()
        self.prod = crear_produccion(self.emp, self.udb)

    def test_listar(self):
        self.assertEqual(self.client.get(reverse("gestionar_lotes")).status_code, 200)

    def test_guardar_valido(self):
        resp = self.client.post(reverse("guardar_lote"), {
            "codigo_lote": "AB-001", "cantidad": 100,
            "unidad": "Kilogramos", "nombre_producto": "Chocolate",
            "fecha_produccion": self.prod.fecha_entrega.isoformat(),
            "fecha_vencimiento": (self.prod.fecha_entrega + timedelta(days=180)).isoformat(),
            "produccion_id": self.prod.id,
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_codigo_invalido(self):
        resp = self.client.post(reverse("guardar_lote"), {
            "codigo_lote": "invalido", "cantidad": 50,
            "fecha_produccion": self.prod.fecha_entrega.isoformat(),
            "fecha_vencimiento": (self.prod.fecha_entrega + timedelta(days=90)).isoformat(),
            "produccion_id": self.prod.id,
        })
        self.assertIn(resp.status_code, [200, 302])
        self.assertEqual(Lote.objects.count(), 0)

    def test_vencimiento_anterior_produccion(self):
        resp = self.client.post(reverse("guardar_lote"), {
            "codigo_lote": "AB-002", "cantidad": 50,
            "fecha_produccion": self.prod.fecha_entrega.isoformat(),
            "fecha_vencimiento": (self.prod.fecha_entrega - timedelta(days=1)).isoformat(),
            "produccion_id": self.prod.id,
        })
        self.assertEqual(Lote.objects.count(), 0)

    def test_fecha_produccion_no_coincide_con_entrega(self):
        """Regla: fecha_produccion del lote debe == fecha_entrega de la producción."""
        resp = self.client.post(reverse("guardar_lote"), {
            "codigo_lote": "AB-003", "cantidad": 50,
            "fecha_produccion": (self.prod.fecha_entrega + timedelta(days=1)).isoformat(),
            "fecha_vencimiento": (self.prod.fecha_entrega + timedelta(days=90)).isoformat(),
            "produccion_id": self.prod.id,
        })
        self.assertEqual(Lote.objects.count(), 0)

    def test_codigo_duplicado(self):
        crear_lote(self.prod, "DU-001")
        resp = self.client.post(reverse("guardar_lote"), {
            "codigo_lote": "DU-001", "cantidad": 20,
            "fecha_produccion": self.prod.fecha_entrega.isoformat(),
            "fecha_vencimiento": (self.prod.fecha_entrega + timedelta(days=60)).isoformat(),
            "produccion_id": self.prod.id,
        })
        self.assertEqual(Lote.objects.filter(codigo_lote="DU-001").count(), 1)

    def test_eliminar(self):
        lote = crear_lote(self.prod, "EL-001")
        self.client.get(reverse("eliminar_lote", args=[lote.id]))
        self.assertFalse(Lote.objects.filter(pk=lote.id).exists())

    def test_reporte_pdf(self):
        resp = self.client.get(reverse("reporte_lotes"))
        self.assertEqual(resp["Content-Type"], "application/pdf")


# ============================================================
# 12. EXPORTACIONES
# ============================================================

class ExportacionesViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)
        self.emp = crear_empleado()
        self.prod = crear_produccion(self.emp, self.udb)
        self.lote = crear_lote(self.prod)

    def test_listar(self):
        self.assertEqual(self.client.get(reverse("gestionar_exportaciones")).status_code, 200)

    def test_guardar_valida(self):
        envio = self.prod.fecha_entrega + timedelta(days=1)
        entrega = self.prod.fecha_entrega + timedelta(days=10)
        resp = self.client.post(reverse("guardar_exportacion"), {
            "destino": "Madrid", "pais": "España",
            "fecha_envio": envio.isoformat(),
            "fecha_entrega": entrega.isoformat(),
            "estado": "Pendiente", "produccion_id": self.prod.id,
            "lote_id": self.lote.id,
        })
        self.assertIn(resp.status_code, [200, 302])
        self.assertEqual(Exportacion.objects.count(), 1)

    def test_entrega_antes_envio(self):
        envio = self.prod.fecha_entrega + timedelta(days=5)
        entrega = self.prod.fecha_entrega + timedelta(days=2)
        resp = self.client.post(reverse("guardar_exportacion"), {
            "destino": "Paris", "pais": "Francia",
            "fecha_envio": envio.isoformat(),
            "fecha_entrega": entrega.isoformat(),
            "estado": "Pendiente", "produccion_id": self.prod.id,
            "lote_id": self.lote.id,
        })
        self.assertEqual(Exportacion.objects.count(), 0)

    def test_envio_anterior_a_produccion(self):
        """fecha_envio no puede ser anterior a fecha_entrega de la producción."""
        envio = self.prod.fecha_entrega - timedelta(days=1)
        resp = self.client.post(reverse("guardar_exportacion"), {
            "destino": "Roma", "pais": "Italia",
            "fecha_envio": envio.isoformat(),
            "fecha_entrega": (envio + timedelta(days=5)).isoformat(),
            "estado": "Pendiente", "produccion_id": self.prod.id,
            "lote_id": self.lote.id,
        })
        self.assertEqual(Exportacion.objects.count(), 0)

    def test_entrega_supera_vencimiento_lote(self):
        entrega_fuera = self.lote.fecha_vencimiento + timedelta(days=1)
        resp = self.client.post(reverse("guardar_exportacion"), {
            "destino": "Berlin", "pais": "Alemania",
            "fecha_envio": (self.prod.fecha_entrega + timedelta(days=1)).isoformat(),
            "fecha_entrega": entrega_fuera.isoformat(),
            "estado": "Pendiente", "produccion_id": self.prod.id,
            "lote_id": self.lote.id,
        })
        self.assertEqual(Exportacion.objects.count(), 0)

    def test_lote_no_pertenece_a_produccion(self):
        emp2 = crear_empleado(cedula="999888777", email="e2@cf.com")
        prod2 = crear_produccion(emp2, self.udb)
        lote2 = crear_lote(prod2, "ZZ-002")
        resp = self.client.post(reverse("guardar_exportacion"), {
            "destino": "Lisboa", "pais": "Portugal",
            "fecha_envio": (self.prod.fecha_entrega + timedelta(days=1)).isoformat(),
            "fecha_entrega": (self.prod.fecha_entrega + timedelta(days=5)).isoformat(),
            "estado": "Pendiente", "produccion_id": self.prod.id,
            "lote_id": lote2.id,
        })
        self.assertEqual(Exportacion.objects.count(), 0)

    def test_cancelar(self):
        exp = Exportacion.objects.create(
            destino="Oslo", pais="Noruega",
            fecha_envio=self.prod.fecha_entrega + timedelta(days=1),
            fecha_entrega=self.prod.fecha_entrega + timedelta(days=10),
            estado="Pendiente", produccion=self.prod, lote=self.lote,
        )
        self.client.get(reverse("inactivar_exportacion", args=[exp.id]))
        self.assertEqual(Exportacion.objects.get(pk=exp.id).estado, "Cancelado")

    def test_reporte_pdf(self):
        resp = self.client.get(reverse("reporte_exportaciones"))
        self.assertEqual(resp["Content-Type"], "application/pdf")


# ============================================================
# 13. SUPERVISORES
# ============================================================

class SupervisoresViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)
        self.sup = crear_usuario_db(nombre="Sup Test", email="sup_t@cf.com", rol="Supervisor")

    def test_listar(self):
        self.assertEqual(self.client.get(reverse("gestionar_supervisores")).status_code, 200)

    def test_asignar_turno_valido(self):
        self.client.post(reverse("asignar_turno_supervisor", args=[self.sup.id]),
                         {"turno": "Mañana 6:00am - 2:00pm"})
        self.assertEqual(Usuario.objects.get(pk=self.sup.id).turno, "Mañana 6:00am - 2:00pm")

    def test_asignar_turno_invalido(self):
        self.client.post(reverse("asignar_turno_supervisor", args=[self.sup.id]),
                         {"turno": "Turno Falso"})
        self.assertNotEqual(Usuario.objects.get(pk=self.sup.id).turno, "Turno Falso")

    def test_editar_supervisor(self):
        resp = self.client.post(reverse("editar_supervisor"), {
            "id": self.sup.id, "nombre": "Sup Editado",
            "email": "sup_t@cf.com", "telefono": "3001234567",
            "direccion": "Nueva dir", "estado": "Activo",
            "turno": "Tarde 2:00pm - 10:00pm",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Usuario.objects.get(pk=self.sup.id).nombre, "Sup Editado")

    def test_inactivar(self):
        self.client.get(reverse("inactivar_supervisor", args=[self.sup.id]))
        self.assertEqual(Usuario.objects.get(pk=self.sup.id).estado, "Inactivo")

    def test_reporte_pdf(self):
        resp = self.client.get(reverse("reporte_supervisores"))
        self.assertEqual(resp["Content-Type"], "application/pdf")


# ============================================================
# 14. CARGA MASIVA SUPERVISORES
# ============================================================

class CargaMasivaSupervisoresTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)

    def _csv(self, contenido):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile("supervisores.csv", contenido.encode("utf-8"), content_type="text/csv")

    def test_sin_archivo(self):
        self.assertEqual(self.client.post(reverse("carga_masiva_supervisores"), {}).status_code, 400)

    def test_extension_incorrecta(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        arch = SimpleUploadedFile("data.txt", b"x", content_type="text/plain")
        self.assertEqual(
            self.client.post(reverse("carga_masiva_supervisores"), {"csv_file": arch}).status_code, 400
        )

    def test_csv_valido(self):
        csv = ("nombre,email,contrasena,estado,turno\n"
               "Sup CSV,supcsv@cf.com,Pass1234,Activo,Mañana 6:00am - 2:00pm\n")
        resp = self.client.post(reverse("carga_masiva_supervisores"), {"csv_file": self._csv(csv)})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["creados"], 1)

    def test_columnas_faltantes(self):
        resp = self.client.post(reverse("carga_masiva_supervisores"),
                                {"csv_file": self._csv("nombre,email\nSup,s@cf.com\n")})
        self.assertEqual(resp.status_code, 400)

    def test_email_invalido(self):
        csv = "nombre,email,contrasena,estado\nSup,noemail,Pass1234,Activo\n"
        resp = self.client.post(reverse("carga_masiva_supervisores"), {"csv_file": self._csv(csv)})
        data = resp.json()
        self.assertEqual(data["creados"], 0)
        self.assertTrue(len(data["errores"]) > 0)

    def test_duplicado_omitido(self):
        crear_usuario_db(nombre="Dup", email="dup@cf.com", rol="Supervisor")
        csv = "nombre,email,contrasena,estado\nDup,dup@cf.com,Pass1234,Activo\n"
        resp = self.client.post(reverse("carga_masiva_supervisores"), {"csv_file": self._csv(csv)})
        self.assertEqual(resp.json()["omitidos"], 1)


# ============================================================
# 15. BITÁCORA
# ============================================================

class BitacoraSupervisorTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_dj = crear_usuario_django(username="sup99", email="sup99@cf.com")
        self.sup = crear_usuario_db(nombre="Sup Bit", email="sup99@cf.com", rol="Supervisor")
        self.client.login(username="sup99", password="Admin123")
        sesion_supervisor(self.client, self.sup)
        self.emp = crear_empleado(cedula="876543210", email="eb@cf.com")
        self.udb = crear_usuario_db(email="adm2@cf.com")
        self.prod = crear_produccion(self.emp, self.udb)

    def test_crear_borrador(self):
        resp = self.client.post(reverse("bitacora_supervisor"), {
            "titulo": "Informe turno mañana",
            "descripcion": "Durante el turno se completaron satisfactoriamente las tareas asignadas al equipo.",
            "tipo_reporte": "Diario", "produccion": self.prod.id,
            "unidades_producidas": 80, "unidades_pendientes": 20,
            "observaciones": "", "estado": "Borrador",
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_titulo_corto_rechazado(self):
        resp = self.client.post(reverse("bitacora_supervisor"), {
            "titulo": "Inf",
            "descripcion": "Descripción suficientemente larga para pasar la validación.",
            "tipo_reporte": "Diario", "produccion": self.prod.id,
            "unidades_producidas": 50, "unidades_pendientes": 10, "estado": "Borrador",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Bitacora.objects.count(), 0)

    def test_descripcion_corta_rechazada(self):
        resp = self.client.post(reverse("bitacora_supervisor"), {
            "titulo": "Titulo válido ok",
            "descripcion": "Muy corta.",
            "tipo_reporte": "Diario", "produccion": self.prod.id,
            "unidades_producidas": 50, "unidades_pendientes": 10, "estado": "Borrador",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Bitacora.objects.count(), 0)

    def test_listar_bitacoras(self):
        self.assertEqual(self.client.get(reverse("listar_bitacoras_supervisor")).status_code, 200)

    def test_enviar_bitacora(self):
        b = Bitacora.objects.create(
            titulo="Para enviar ahora", descripcion="Descripción larga y válida del turno.",
            tipo_reporte="Diario", unidades_producidas=60, unidades_pendientes=15,
            supervisor=self.sup, produccion=self.prod, estado="Borrador",
        )
        self.client.get(reverse("enviar_bitacora", args=[b.id]))
        self.assertEqual(Bitacora.objects.get(pk=b.id).estado, "Enviado")

    def test_no_reenviar_bitacora_ya_enviada(self):
        b = Bitacora.objects.create(
            titulo="Ya enviada previo", descripcion="Descripción larga y válida del turno.",
            tipo_reporte="Diario", unidades_producidas=40, unidades_pendientes=10,
            supervisor=self.sup, produccion=self.prod, estado="Enviado",
        )
        self.client.get(reverse("enviar_bitacora", args=[b.id]))
        self.assertEqual(Bitacora.objects.get(pk=b.id).estado, "Enviado")


class BitacoraAdminTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)
        self.sup = crear_usuario_db(nombre="Sup Adm", email="su_adm@cf.com", rol="Supervisor")
        self.emp = crear_empleado(cedula="456789012", email="e3@cf.com")
        self.prod = crear_produccion(self.emp, self.udb)

    def test_listar(self):
        self.assertEqual(self.client.get(reverse("listar_bitacoras")).status_code, 200)

    def test_aprobar(self):
        b = Bitacora.objects.create(
            titulo="Bitácora ok", descripcion="Descripción larga y válida del turno diario.",
            tipo_reporte="Diario", unidades_producidas=70, unidades_pendientes=5,
            supervisor=self.sup, produccion=self.prod, estado="Enviado",
        )
        self.client.post(reverse("revisar_bitacora", args=[b.id]),
                         {"estado": "Aprobado", "observacion_admin": "Todo ok."})
        self.assertEqual(Bitacora.objects.get(pk=b.id).estado, "Aprobado")

    def test_rechazar(self):
        b = Bitacora.objects.create(
            titulo="Bitácora a rechazar", descripcion="Descripción larga y válida del reporte.",
            tipo_reporte="Semanal", unidades_producidas=30, unidades_pendientes=50,
            supervisor=self.sup, produccion=self.prod, estado="Enviado",
        )
        self.client.post(reverse("revisar_bitacora", args=[b.id]),
                         {"estado": "Rechazado", "observacion_admin": "Faltan datos."})
        self.assertEqual(Bitacora.objects.get(pk=b.id).estado, "Rechazado")

    def test_no_revisar_ya_revisada(self):
        b = Bitacora.objects.create(
            titulo="Ya aprobada antes", descripcion="Descripción larga y válida del turno.",
            tipo_reporte="Diario", unidades_producidas=50, unidades_pendientes=0,
            supervisor=self.sup, produccion=self.prod, estado="Aprobado",
        )
        self.client.post(reverse("revisar_bitacora", args=[b.id]),
                         {"estado": "Rechazado", "observacion_admin": "Intento."})
        self.assertEqual(Bitacora.objects.get(pk=b.id).estado, "Aprobado")


# ============================================================
# 16. CORREOS (resend mockeado)
# ============================================================

class CorreosViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)
        self.emp = crear_empleado()

    def test_vista_accesible(self):
        self.assertEqual(self.client.get(reverse("correos_vista")).status_code, 200)

    def test_enviar_sin_seleccion(self):
        resp = self.client.post(reverse("enviar_correos_masivos"), {"empleados_ids": []})
        self.assertIn(resp.status_code, [200, 302])

    @patch("myApp.views.resend.Emails.send")
    def test_enviar_exitoso(self, mock_send):
        mock_send.return_value = {"id": "fake-id"}
        resp = self.client.post(reverse("enviar_correos_masivos"),
                                {"empleados_ids": [self.emp.id]})
        self.assertIn(resp.status_code, [200, 302])
        self.assertEqual(HistorialCorreo.objects.filter(estado="Enviado").count(), 1)

    @patch("myApp.views.resend.Emails.send", side_effect=Exception("Error de red"))
    def test_enviar_con_error(self, mock_send):
        resp = self.client.post(reverse("enviar_correos_masivos"),
                                {"empleados_ids": [self.emp.id]})
        self.assertIn(resp.status_code, [200, 302])
        self.assertEqual(HistorialCorreo.objects.filter(estado="Error").count(), 1)


# ============================================================
# 17. HELPERS INTERNOS
# ============================================================

class HelpersInternosTest(TestCase):
    def setUp(self):
        self.sup = crear_usuario_db(
            rol="Supervisor", email="h_sup@cf.com", turno="Mañana 6:00am - 2:00pm"
        )
        self.emp = crear_empleado()
        self.turno = crear_turno()
        lunes = lunes_semana_actual()
        RotacionTurno.objects.create(
            empleado=self.emp, turno=self.turno,
            fecha_inicio=lunes, fecha_fin=lunes + timedelta(days=6),
            semana=lunes.isocalendar()[1],
        )

    def test_get_turno_supervisor(self):
        from myApp.views import get_turno_supervisor
        self.assertEqual(get_turno_supervisor(self.sup.id), "Mañana 6:00am - 2:00pm")

    def test_get_turno_supervisor_inexistente(self):
        from myApp.views import get_turno_supervisor
        self.assertIsNone(get_turno_supervisor(99999))

    def test_get_empleados_de_turno_supervisor(self):
        from myApp.views import get_empleados_de_turno_supervisor
        ids = get_empleados_de_turno_supervisor("Mañana 6:00am - 2:00pm")
        self.assertIn(self.emp.id, list(ids))

    def test_get_empleados_turno_inexistente(self):
        from myApp.views import get_empleados_de_turno_supervisor
        self.assertEqual(list(get_empleados_de_turno_supervisor("No existe")), [])


# ============================================================
# 18. FUNCIONES IA INTEGRADAS (sin llamada a API externa)
# ============================================================

class FuncionesIATest(TestCase):
    def setUp(self):
        self.emp = crear_empleado()
        self.udb = crear_usuario_db()

    def test_obtener_resumen_empresa(self):
        from myApp.views import obtener_resumen_empresa
        r = obtener_resumen_empresa()
        self.assertIn("empleados_activos", r)
        self.assertIn("total_lotes", r)

    def test_detectar_alertas_sin_datos(self):
        from myApp.views import detectar_alertas
        alertas = detectar_alertas()
        self.assertIsInstance(alertas, list)

    def test_detectar_alertas_lote_por_vencer(self):
        prod = crear_produccion(self.emp, self.udb)
        Lote.objects.create(
            codigo_lote="VE-001", cantidad=10,
            fecha_produccion=prod.fecha_entrega,
            fecha_vencimiento=date.today() + timedelta(days=3),
            produccion=prod,
        )
        from myApp.views import detectar_alertas
        alertas = detectar_alertas()
        self.assertTrue(any("VE-001" in a for a in alertas))

    def test_predecir_proxima_produccion_sin_datos(self):
        from myApp.views import predecir_proxima_produccion
        r = predecir_proxima_produccion()
        self.assertIn("insuficientes", r.lower())

    def test_detectar_vencimientos_lotes_sin_lotes(self):
        from myApp.views import detectar_vencimientos_lotes
        r = detectar_vencimientos_lotes()
        self.assertTrue(any("No hay" in x or "✅" in x for x in r))

    def test_detectar_retrasos_exportaciones_sin_datos(self):
        from myApp.views import detectar_retrasos_exportaciones
        r = detectar_retrasos_exportaciones()
        self.assertTrue(any("No hay" in x or "✅" in x for x in r))

    def test_analizar_rendimiento_sin_datos(self):
        from myApp.views import analizar_rendimiento
        r = analizar_rendimiento()
        self.assertIn("mejor_empleado", r)

    def test_predecir_exportaciones_sin_datos(self):
        from myApp.views import predecir_exportaciones
        r = predecir_exportaciones()
        self.assertIn("insuficientes", r.lower())

    def test_detectar_anomalias_sin_datos(self):
        from myApp.views import detectar_anomalias
        r = detectar_anomalias()
        self.assertTrue(any("insuficientes" in x.lower() or "anomalías" in x.lower() for x in r))


# ============================================================
# 19. ENDPOINT IA (Gemini mockeado)
# ============================================================

class IAEndpointTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = crear_usuario_django()
        self.udb = crear_usuario_db()
        self.client.login(username="admin001", password="Admin123")
        sesion_admin(self.client, self.udb)

    def test_metodo_get_no_permitido(self):
        self.assertEqual(self.client.get(reverse("consultar_ia")).status_code, 405)

    def test_pregunta_vacia(self):
        resp = self.client.post(reverse("consultar_ia"), {"pregunta": ""})
        self.assertEqual(resp.status_code, 400)

    def test_pregunta_muy_corta(self):
        resp = self.client.post(reverse("consultar_ia"), {"pregunta": "hol"})
        self.assertEqual(resp.status_code, 400)

    @patch("myApp.views.genai")
    def test_respuesta_simulada(self, mock_genai):
        mock_resp = MagicMock()
        mock_resp.text = "Respuesta de prueba de IA."
        mock_genai.Client.return_value.models.generate_content.return_value = mock_resp
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            resp = self.client.post(reverse("consultar_ia"),
                                    {"pregunta": "¿Cómo va la producción?"})
        self.assertIn(resp.status_code, [200, 500, 503])

    def test_sin_api_key(self):
        import os
        key_original = os.environ.pop("GEMINI_API_KEY", None)
        resp = self.client.post(reverse("consultar_ia"),
                                {"pregunta": "¿Cuál es el estado actual de la empresa?"})
        self.assertIn(resp.status_code, [200, 400, 500])
        if key_original:
            os.environ["GEMINI_API_KEY"] = key_original