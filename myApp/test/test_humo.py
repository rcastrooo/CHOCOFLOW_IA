"""
TEST DE HUMO - CHOCOFLOW
Verifica rápidamente que los módulos esenciales del sistema
respondan correctamente después de un deploy.
No mide carga, solo disponibilidad básica (smoke test).
"""

import requests
import sys

# ──────────────────────────────────────────────
# CONFIGURACIÓN — AJUSTA ESTO A TU ENTORNO
# ──────────────────────────────────────────────

BASE_URL = "https://chocoflow.up.railway.app"   # cambia a http://127.0.0.1:8000 para probar local

USUARIO_TEST = "supervisor@gmail.com"        # username/cédula con el que haces login
PASSWORD_TEST = "Super123*"      # contraseña de esa cuenta

# ──────────────────────────────────────────────
# RESULTADOS
# ──────────────────────────────────────────────

resultados = []


def registrar(nombre, ok, detalle=""):
    estado = "✅ PASA" if ok else "❌ FALLA"
    resultados.append((nombre, ok, detalle))
    print(f"{estado} | {nombre} {('-> ' + detalle) if detalle else ''}")


def login():
    """Hace login y devuelve la sesión autenticada."""
    session = requests.Session()

    resp_login_page = session.get(f"{BASE_URL}/login/")
    csrf_token = session.cookies.get("csrftoken")

    if not csrf_token:
        registrar("Login - obtener CSRF token", False, "No se encontró csrftoken en cookies")
        return None

    payload = {
        "username": USUARIO_TEST,
        "password": PASSWORD_TEST,
        "csrfmiddlewaretoken": csrf_token,
    }
    headers = {"Referer": f"{BASE_URL}/login/"}

    resp = session.post(f"{BASE_URL}/login/", data=payload, headers=headers, allow_redirects=True)

    # Si el login funcionó, normalmente termina en dashboard (200) y no de vuelta en /login/
    ok = resp.status_code == 200 and "/login" not in resp.url
    registrar("Login con usuario de prueba", ok, f"status={resp.status_code}, url_final={resp.url}")

    return session if ok else None


def verificar_get(session, ruta, nombre):
    """Verifica que una ruta GET responda 200."""
    try:
        resp = session.get(f"{BASE_URL}{ruta}", timeout=15)
        ok = resp.status_code == 200
        registrar(nombre, ok, f"status={resp.status_code}")
    except Exception as e:
        registrar(nombre, False, f"error: {str(e)}")


def verificar_get_publico(ruta, nombre):
    """Verifica una ruta pública sin sesión (ej: index, login page)."""
    try:
        resp = requests.get(f"{BASE_URL}{ruta}", timeout=15)
        ok = resp.status_code == 200
        registrar(nombre, ok, f"status={resp.status_code}")
    except Exception as e:
        registrar(nombre, False, f"error: {str(e)}")


def main():
    print(f"\n🚀 Iniciando test de humo sobre {BASE_URL}\n")

    # ── 1. Páginas públicas (sin login) ──────────────────────
    verificar_get_publico("/", "Index (página pública)")
    verificar_get_publico("/login/", "Página de login")
    verificar_get_publico("/registro/", "Página de registro")
    verificar_get_publico("/olvide-password/", "Página de recuperar contraseña")

    # ── 2. Login ──────────────────────────────────────────────
    session = login()

    if not session:
        print("\n💥 El login falló. No se pueden probar las rutas protegidas.")
        mostrar_resumen()
        sys.exit(1)

    # ── 3. Dashboards ────────────────────────────────────────
    verificar_get(session, "/dashboard/", "Dashboard Administrador")

    # ── 4. Módulos principales (CRUD) ────────────────────────
    verificar_get(session, "/empleados/", "Módulo Empleados")
    verificar_get(session, "/turnos/", "Módulo Turnos")
    verificar_get(session, "/solicitudes/", "Módulo Solicitudes")
    verificar_get(session, "/asignaciones/", "Módulo Asignaciones")
    verificar_get(session, "/producciones/", "Módulo Producción")
    verificar_get(session, "/exportaciones/", "Módulo Exportaciones")
    verificar_get(session, "/lotes/", "Módulo Lotes")
    verificar_get(session, "/correos/", "Módulo Correos")
    verificar_get(session, "/supervisores/", "Módulo Gestión Supervisores")
    verificar_get(session, "/bitacora/admin/", "Módulo Bitácora (admin)")

    # ── 5. Reportes PDF (verifica que ReportLab no esté roto) ─
    verificar_get(session, "/empleados/reporte/", "Reporte PDF Empleados")
    verificar_get(session, "/turnos/reporte/", "Reporte PDF Turnos")
    verificar_get(session, "/solicitudes/reporte/", "Reporte PDF Solicitudes")
    verificar_get(session, "/asignaciones/reporte/", "Reporte PDF Asignaciones")
    verificar_get(session, "/producciones/reporte/", "Reporte PDF Producciones")
    verificar_get(session, "/exportaciones/reporte/", "Reporte PDF Exportaciones")
    verificar_get(session, "/lotes/reporte/", "Reporte PDF Lotes")
    verificar_get(session, "/supervisores/reporte/", "Reporte PDF Supervisores")

    # ── 6. Asistente IA (solo verifica que la ruta responda, sin abusar) ─
    csrf_token = session.cookies.get("csrftoken")
    try:
        resp = session.post(
            f"{BASE_URL}/dashboard/ia/",
            data={
                "pregunta": "¿Cómo va la producción esta semana?",
                "csrfmiddlewaretoken": csrf_token,
            },
            headers={"Referer": BASE_URL},
            timeout=30,
        )
        ok = resp.status_code == 200
        registrar("Asistente IA (ChocoBot)", ok, f"status={resp.status_code}")
    except Exception as e:
        registrar("Asistente IA (ChocoBot)", False, f"error: {str(e)}")

    # ── 7. Logout ─────────────────────────────────────────────
    try:
        resp = session.get(f"{BASE_URL}/logout/", timeout=15)
        ok = resp.status_code == 200
        registrar("Logout", ok, f"status={resp.status_code}")
    except Exception as e:
        registrar("Logout", False, f"error: {str(e)}")

    mostrar_resumen()


def mostrar_resumen():
    print("\n" + "=" * 50)
    print("📊 RESUMEN DEL TEST DE HUMO")
    print("=" * 50)

    total = len(resultados)
    exitosos = sum(1 for _, ok, _ in resultados if ok)
    fallidos = total - exitosos

    print(f"Total de pruebas:     {total}")
    print(f"✅ Pasaron:           {exitosos}")
    print(f"❌ Fallaron:          {fallidos}")

    if fallidos > 0:
        print("\n⚠️ PRUEBAS FALLIDAS:")
        for nombre, ok, detalle in resultados:
            if not ok:
                print(f"  - {nombre} ({detalle})")
        print("\n💥 EL SISTEMA TIENE PROBLEMAS. Revisa antes de continuar.")
        sys.exit(1)
    else:
        print("\n🎉 TODO BIEN. El sistema está operativo después del deploy.")
        sys.exit(0)


if __name__ == "__main__":
    main()