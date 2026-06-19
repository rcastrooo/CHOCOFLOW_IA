"""
========================================================
  PRUEBAS DE HUMO — CHOCOFLOW
  Sistema de Gestión de Producción de Chocolate

¿Qué son las pruebas de humo?
    Son pruebas rápidas y básicas que verifican que las
    funcionalidades CRÍTICAS del sistema responden y no
    están completamente rotas. No validan lógica compleja,
    solo comprueban que cada ruta existe, responde con un
    código HTTP válido y no explota al cargarla.

    Son el primer filtro antes de hacer pruebas más
    profundas como las pruebas integrales.

Cómo ejecutar:
    python manage.py test myApp.test.tests_humo --verbosity=2

Módulos cubiertos:
    ✅ Rutas públicas     — index, login, registro
    ✅ Protección         — rutas que exigen login
    ✅ Dashboard admin    — carga correctamente
    ✅ Dashboard sup.     — carga correctamente
    ✅ Supervisores       — listado responde
    ✅ Empleados          — listado responde
    ✅ Turnos             — listado responde
    ✅ Solicitudes        — listado responde
    ✅ Asignaciones       — listado responde
    ✅ Producción         — listado responde
    ✅ Lotes              — listado responde
    ✅ Exportaciones      — listado responde
    ✅ Bitácora admin     — listado responde
    ✅ Bitácora sup.      — listado responde
    ✅ Correos            — vista responde
    ✅ Reportes PDF       — generación no explota
    ✅ APIs JSON          — devuelven JSON válido
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
    Turno,
    Usuario,
)


# ============================================================
# BASE — misma estructura que las pruebas integrales
# ============================================================

class HumoBase(TestCase):
    """
    Crea la estructura mínima de datos para que las vistas
    no exploten por falta de objetos relacionados.
    """

    def setUp(self):
        self.client = Client()

        # Turnos
        self.turno_mañana = Turno.objects.create(
            horario='Mañana 6:00am - 2:00pm',
            activo=True,
        )
        self.turno_tarde = Turno.objects.create(
            horario='Tarde 2:00pm - 10:00pm',
            activo=True,
        )

        # Admin Django + perfil
        self.admin_django = User.objects.create_user(
            username='11111111',
            email='admin@chocoflow.com',
            password='Admin1234',
        )
        self.admin_perfil = Usuario.objects.create(
            nombre='Admin Humo',
            email='admin@chocoflow.com',
            direccion='Calle 1',
            contrasena='Admin1234',
            rol='Administrador',
            estado='Activo',
        )

        # Supervisor Django + perfil
        self.sup_django = User.objects.create_user(
            username='22222222',
            email='supervisor@chocoflow.com',
            password='Sup12345',
        )
        self.sup_perfil = Usuario.objects.create(
            nombre='Supervisor Humo',
            email='supervisor@chocoflow.com',
            direccion='Calle 2',
            contrasena='Sup12345',
            rol='Supervisor',
            estado='Activo',
            turno='Mañana 6:00am - 2:00pm',
        )

        # Empleado activo
        self.empleado = Empleado.objects.create(
            cedula='123456789',
            nombre='Empleado Humo',
            email='empleado@chocoflow.com',
            direccion='Calle 3',
            estado='Activo',
            creado_por=self.admin_perfil,
        )

        # Rotación semana actual
        hoy   = date.today()
        lunes = hoy - timedelta(days=hoy.weekday())
        dom   = lunes + timedelta(days=6)
        self.rotacion = RotacionTurno.objects.create(
            empleado     = self.empleado,
            turno        = self.turno_mañana,
            fecha_inicio = lunes,
            fecha_fin    = dom,
            semana       = hoy.isocalendar()[1],
            estado       = 'Asignado',
        )

        # Producción base
        self.produccion = Produccion.objects.create(
            producto             = 'Chocolate de prueba',
            ingredientes         = 'Cacao, azúcar',
            cantidad_requerida   = '100',
            fecha_entrega        = hoy + timedelta(days=7),
            fecha_limite         = hoy + timedelta(days=14),
            estado               = 'En Proceso',
            empleado_responsable = self.empleado,
            creado_por           = self.admin_perfil,
        )

        # Lote base
        self.lote = Lote.objects.create(
            codigo_lote       = 'HU-001',
            cantidad          = '100',
            fecha_produccion  = self.produccion.fecha_entrega,
            fecha_vencimiento = self.produccion.fecha_entrega + timedelta(days=180),
            produccion        = self.produccion,
        )

        # Exportación base
        self.exportacion = Exportacion.objects.create(
            destino       = 'Francia',
            pais          = 'Francia',
            fecha_envio   = self.produccion.fecha_entrega + timedelta(days=1),
            fecha_entrega = self.produccion.fecha_entrega + timedelta(days=10),
            estado        = 'Pendiente',
            produccion    = self.produccion,
            lote          = self.lote,
        )

        # Bitácora base
        self.bitacora = Bitacora.objects.create(
            titulo              = 'Bitácora de humo',
            descripcion         = 'Descripción de prueba de humo para el sistema.',
            tipo_reporte        = 'Diario',
            estado              = 'Enviado',
            supervisor          = self.sup_perfil,
            produccion          = self.produccion,
            unidades_producidas = '80',
            unidades_pendientes = '20',
        )

    def login_admin(self):
        self.client.post(reverse('login'), {
            'username': 'admin@chocoflow.com',
            'password': 'Admin1234',
        })
        s = self.client.session
        s['usuario_id'] = self.admin_perfil.id
        s['rol']        = 'Administrador'
        s.save()

    def login_supervisor(self):
        self.client.post(reverse('login'), {
            'username': 'supervisor@chocoflow.com',
            'password': 'Sup12345',
        })
        s = self.client.session
        s['usuario_id'] = self.sup_perfil.id
        s['rol']        = 'Supervisor'
        s.save()


# ============================================================
# 1. RUTAS PÚBLICAS
# ============================================================

class HumoRutasPublicas(HumoBase):
    """
    Verifica que las páginas públicas (sin login) respondan
    con HTTP 200 y no exploten.
    """

    def test_index_responde(self):
        resp = self.client.get(reverse('index'))
        self.assertIn(resp.status_code, [200, 302])

    def test_login_responde(self):
        resp = self.client.get(reverse('login'))
        self.assertEqual(resp.status_code, 200)

    def test_registro_responde(self):
        resp = self.client.get(reverse('registro'))
        self.assertEqual(resp.status_code, 200)


# ============================================================
# 2. PROTECCIÓN DE RUTAS (sin login → redirige a login)
# ============================================================

class HumoProteccionRutas(HumoBase):
    """
    Verifica que las rutas protegidas NO sean accesibles
    sin autenticación — deben redirigir al login.
    """

    def _assert_redirige_login(self, url):
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp['Location'])

    def test_dashboard_admin_protegido(self):
        self._assert_redirige_login(reverse('dashboard'))

    def test_dashboard_supervisor_protegido(self):
        self._assert_redirige_login(reverse('dashboard_supervisor'))

    def test_empleados_protegido(self):
        self._assert_redirige_login(reverse('empleados'))

    def test_turnos_protegido(self):
        self._assert_redirige_login(reverse('turnos'))

    def test_asignaciones_protegido(self):
        self._assert_redirige_login(reverse('asignaciones'))

    def test_producciones_protegido(self):
        self._assert_redirige_login(reverse('producciones'))

    def test_lotes_protegido(self):
        self._assert_redirige_login(reverse('gestionar_lotes'))

    def test_exportaciones_protegido(self):
        self._assert_redirige_login(reverse('gestionar_exportaciones'))

    def test_bitacora_admin_protegido(self):
        self._assert_redirige_login(reverse('listar_bitacoras'))

    def test_correos_protegido(self):
        self._assert_redirige_login(reverse('correos_vista'))

    def test_supervisores_protegido(self):
        self._assert_redirige_login(reverse('gestionar_supervisores'))


# ============================================================
# 3. DASHBOARDS
# ============================================================

class HumoDashboards(HumoBase):
    """
    Verifica que los dashboards carguen sin errores y
    usen el template correcto.
    """

    def test_dashboard_admin_carga(self):
        self.login_admin()
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'dashboard.html')

    def test_dashboard_supervisor_carga(self):
        self.login_supervisor()
        resp = self.client.get(reverse('dashboard_supervisor'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'dashboard_supervisor.html')

    def test_dashboard_admin_tiene_contexto(self):
        self.login_admin()
        resp = self.client.get(reverse('dashboard'))
        self.assertIn('total_empleados', resp.context)
        self.assertIn('total_producciones', resp.context)
        self.assertIn('total_exportaciones', resp.context)

    def test_dashboard_supervisor_tiene_contexto(self):
        self.login_supervisor()
        resp = self.client.get(reverse('dashboard_supervisor'))
        self.assertIn('empleados_activos', resp.context)
        self.assertIn('total_lotes', resp.context)


# ============================================================
# 4. MÓDULO SUPERVISORES
# ============================================================

class HumoSupervisores(HumoBase):

    def test_listado_carga(self):
        self.login_admin()
        resp = self.client.get(reverse('gestionar_supervisores'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/supervisores/gestionar_supervisores.html')

    def test_listado_contiene_supervisor(self):
        self.login_admin()
        resp = self.client.get(reverse('gestionar_supervisores'))
        self.assertIn(self.sup_perfil, resp.context['supervisores'])

    def test_reporte_pdf_no_explota(self):
        self.login_admin()
        resp = self.client.get(reverse('reporte_supervisores'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')


# ============================================================
# 5. MÓDULO EMPLEADOS
# ============================================================

class HumoEmpleados(HumoBase):

    def test_listado_admin_carga(self):
        self.login_admin()
        resp = self.client.get(reverse('empleados'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/empleados/empleados.html')

    def test_listado_supervisor_carga(self):
        self.login_supervisor()
        resp = self.client.get(reverse('empleados_supervisor'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/empleados/empleados_supervisor.html')

    def test_listado_contiene_empleado(self):
        self.login_admin()
        resp = self.client.get(reverse('empleados'))
        self.assertIn(self.empleado, resp.context['empleados'])

    def test_reporte_pdf_no_explota(self):
        self.login_admin()
        resp = self.client.get(reverse('reporte_empleados'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')


# ============================================================
# 6. MÓDULO TURNOS
# ============================================================

class HumoTurnos(HumoBase):

    def test_listado_admin_carga(self):
        self.login_admin()
        resp = self.client.get(reverse('turnos'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/turnos/turnos.html')

    def test_listado_supervisor_carga(self):
        self.login_supervisor()
        resp = self.client.get(reverse('turnos_supervisor'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/turnos/turnos_supervisor.html')

    def test_rotacion_carga(self):
        self.login_admin()
        resp = self.client.get(reverse('rotacion_turnos'))
        self.assertEqual(resp.status_code, 200)

    def test_reporte_turnos_no_explota(self):
        self.login_admin()
        resp = self.client.get(reverse('reporte_turnos'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_reporte_rotacion_no_explota(self):
        self.login_admin()
        resp = self.client.get(reverse('reporte_rotacion'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')


# ============================================================
# 7. MÓDULO SOLICITUDES
# ============================================================

class HumoSolicitudes(HumoBase):

    def test_listado_carga(self):
        self.login_admin()
        resp = self.client.get(reverse('solicitudes'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/solicitudes/solicitudes.html')

    def test_listado_tiene_contexto(self):
        self.login_admin()
        resp = self.client.get(reverse('solicitudes'))
        self.assertIn('solicitudes', resp.context)
        self.assertIn('turnos', resp.context)
        self.assertIn('empleados', resp.context)

    def test_reporte_pdf_no_explota(self):
        self.login_admin()
        resp = self.client.get(reverse('reporte_solicitudes'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')


# ============================================================
# 8. MÓDULO ASIGNACIONES
# ============================================================

class HumoAsignaciones(HumoBase):

    def test_listado_admin_carga(self):
        self.login_admin()
        resp = self.client.get(reverse('asignaciones'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/asignaciones/asignaciones.html')

    def test_listado_supervisor_carga(self):
        self.login_supervisor()
        resp = self.client.get(reverse('asignaciones_supervisor'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/asignaciones/asignaciones_supervisor.html')

    def test_listado_tiene_contexto(self):
        self.login_admin()
        resp = self.client.get(reverse('asignaciones'))
        self.assertIn('asignaciones', resp.context)
        self.assertIn('empleados', resp.context)
        self.assertIn('turnos', resp.context)

    def test_reporte_pdf_no_explota(self):
        self.login_admin()
        resp = self.client.get(reverse('reporte_asignaciones'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')


# ============================================================
# 9. MÓDULO PRODUCCIÓN
# ============================================================

class HumoProduccion(HumoBase):

    def test_listado_admin_carga(self):
        self.login_admin()
        resp = self.client.get(reverse('producciones'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/produccion/produccion.html')

    def test_listado_supervisor_carga(self):
        self.login_supervisor()
        resp = self.client.get(reverse('producciones_supervisor'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/produccion/produccion_supervisor.html')

    def test_listado_contiene_produccion(self):
        self.login_admin()
        resp = self.client.get(reverse('producciones'))
        self.assertIn(self.produccion, resp.context['producciones'])

    def test_reporte_pdf_no_explota(self):
        self.login_admin()
        resp = self.client.get(reverse('reporte_producciones'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')


# ============================================================
# 10. MÓDULO LOTES
# ============================================================

class HumoLotes(HumoBase):

    def test_listado_admin_carga(self):
        self.login_admin()
        resp = self.client.get(reverse('gestionar_lotes'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/lotes/lotes.html')

    def test_listado_supervisor_carga(self):
        self.login_supervisor()
        resp = self.client.get(reverse('lotes_supervisor'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/lotes/lotes_supervisor.html')

    def test_listado_contiene_lote(self):
        self.login_admin()
        resp = self.client.get(reverse('gestionar_lotes'))
        self.assertIn(self.lote, resp.context['lotes'])

    def test_reporte_pdf_no_explota(self):
        self.login_admin()
        resp = self.client.get(reverse('reporte_lotes'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')


# ============================================================
# 11. MÓDULO EXPORTACIONES
# ============================================================

class HumoExportaciones(HumoBase):

    def test_listado_admin_carga(self):
        self.login_admin()
        resp = self.client.get(reverse('gestionar_exportaciones'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/exportaciones/exportaciones.html')

    def test_listado_supervisor_carga(self):
        self.login_supervisor()
        resp = self.client.get(reverse('exportaciones_supervisor'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/exportaciones/exportaciones_supervisor.html')

    def test_listado_contiene_exportacion(self):
        self.login_admin()
        resp = self.client.get(reverse('gestionar_exportaciones'))
        self.assertIn(self.exportacion, resp.context['exportaciones'])

    def test_reporte_pdf_no_explota(self):
        self.login_admin()
        resp = self.client.get(reverse('reporte_exportaciones'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')


# ============================================================
# 12. MÓDULO BITÁCORA
# ============================================================

class HumoBitacora(HumoBase):

    def test_listado_admin_carga(self):
        self.login_admin()
        resp = self.client.get(reverse('listar_bitacoras'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/bitacora/listar_bitacoras.html')

    def test_listado_supervisor_carga(self):
        self.login_supervisor()
        resp = self.client.get(reverse('listar_bitacoras_supervisor'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/bitacora/listar_bitacoras_supervisor.html')

    def test_formulario_crear_carga(self):
        self.login_supervisor()
        resp = self.client.get(reverse('bitacora_supervisor'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/bitacora/bitacora_supervisor.html')

    def test_listado_admin_tiene_contexto(self):
        self.login_admin()
        resp = self.client.get(reverse('listar_bitacoras'))
        self.assertIn('bitacoras', resp.context)
        self.assertIn('pendientes', resp.context)

    def test_listado_admin_contiene_bitacora(self):
        self.login_admin()
        resp = self.client.get(reverse('listar_bitacoras'))
        self.assertIn(self.bitacora, resp.context['bitacoras'])


# ============================================================
# 13. MÓDULO CORREOS
# ============================================================

class HumoCorreos(HumoBase):

    def test_vista_carga(self):
        self.login_admin()
        resp = self.client.get(reverse('correos_vista'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modulos/correos/correos.html')

    def test_vista_tiene_contexto(self):
        self.login_admin()
        resp = self.client.get(reverse('correos_vista'))
        self.assertIn('historial', resp.context)
        self.assertIn('empleados_info', resp.context)


# ============================================================
# 14. API JSON — stats supervisor
# ============================================================

class HumoAPIs(HumoBase):
    """
    Verifica que los endpoints que devuelven JSON respondan
    correctamente y el contenido sea JSON válido.
    """

    def test_api_stats_supervisor_responde(self):
        self.login_supervisor()
        resp = self.client.get(reverse('api_stats_supervisor'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/json')

    def test_api_stats_supervisor_tiene_claves(self):
        self.login_supervisor()
        resp = self.client.get(reverse('api_stats_supervisor'))
        data = resp.json()
        claves_esperadas = [
            'total_empleados',
            'empleados_activos',
            'asignaciones_hoy',
            'lotes_totales',
            'exportaciones_pendientes',
            'turno_nombre',
        ]
        for clave in claves_esperadas:
            self.assertIn(clave, data, msg=f"Falta la clave '{clave}' en la respuesta JSON")

    def test_api_stats_protegida(self):
        resp = self.client.get(reverse('api_stats_supervisor'))
        self.assertEqual(resp.status_code, 302)