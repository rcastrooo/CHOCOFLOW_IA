"""
TEST DE ESTRÉS - CHOCOFLOW
Simula múltiples usuarios concurrentes golpeando los endpoints
más pesados del sistema (login, dashboard, IA, reportes, correos).
"""

import requests
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

# ──────────────────────────────────────────────
# CONFIGURACIÓN — AJUSTA ESTO A TU ENTORNO
# ──────────────────────────────────────────────

BASE_URL = "https://chocoflow.up.railway.app"   # cambia a tu URL de Railway si quieres probar producción
# Ej: BASE_URL = "https://chocoflow-ia.up.railway.app"

USUARIO_TEST = "super001"   # el username con el que haces login (no el correo)
PASSWORD_TEST = "Super123*"

NUM_USUARIOS_CONCURRENTES = 10   # cuántos "usuarios" simultáneos
NUM_PETICIONES_POR_USUARIO = 5   # cuántas veces cada uno repite el flujo

# ──────────────────────────────────────────────
# RESULTADOS GLOBALES
# ──────────────────────────────────────────────

resultados = {
    "exitosos": 0,
    "fallidos": 0,
    "tiempos": [],
    "errores": [],
}


def login_y_obtener_sesion():
    """
    Crea una sesión nueva (cookies independientes), hace login
    y devuelve la sesión autenticada lista para usar.
    """
    session = requests.Session()

    # 1. Obtener el CSRF token de la página de login
    resp_login_page = session.get(f"{BASE_URL}/login/")  # ajusta la ruta si es distinta
    csrf_token = session.cookies.get("csrftoken")

    # 2. Hacer login con ese token
    payload = {
        "username": USUARIO_TEST,
        "password": PASSWORD_TEST,
        "csrfmiddlewaretoken": csrf_token,
    }
    headers = {"Referer": f"{BASE_URL}/login/"}

    resp = session.post(f"{BASE_URL}/login/", data=payload, headers=headers)

    if resp.status_code not in (200, 302):
        raise Exception(f"Login falló con status {resp.status_code}")

    return session


def medir_peticion(session, metodo, url, nombre, **kwargs):
    """Mide tiempo de respuesta de una petición y registra el resultado."""
    inicio = time.time()
    try:
        if metodo == "GET":
            resp = session.get(url, timeout=30, **kwargs)
        else:
            resp = session.post(url, timeout=30, **kwargs)

        duracion = time.time() - inicio
        resultados["tiempos"].append(duracion)

        if resp.status_code < 400:
            resultados["exitosos"] += 1
            print(f"✅ {nombre} | {resp.status_code} | {duracion:.2f}s")
        else:
            resultados["fallidos"] += 1
            resultados["errores"].append(f"{nombre} -> status {resp.status_code}")
            print(f"❌ {nombre} | {resp.status_code} | {duracion:.2f}s")

    except Exception as e:
        duracion = time.time() - inicio
        resultados["fallidos"] += 1
        resultados["errores"].append(f"{nombre} -> {str(e)}")
        print(f"💥 {nombre} | ERROR: {str(e)} | {duracion:.2f}s")


def flujo_usuario(usuario_id):
    """
    Simula el comportamiento de UN usuario navegando por el sistema.
    Se repite NUM_PETICIONES_POR_USUARIO veces.
    """
    try:
        session = login_y_obtener_sesion()
    except Exception as e:
        resultados["fallidos"] += 1
        resultados["errores"].append(f"Usuario {usuario_id} -> login falló: {str(e)}")
        print(f"💥 Usuario {usuario_id} no pudo loguear: {e}")
        return

    for i in range(NUM_PETICIONES_POR_USUARIO):

        # Dashboard
        medir_peticion(session, "GET", f"{BASE_URL}/dashboard/",
                        f"Usuario{usuario_id}-Dashboard-{i}")

        # Lista de empleados (consulta a BD)
        medir_peticion(session, "GET", f"{BASE_URL}/empleados/",
                        f"Usuario{usuario_id}-Empleados-{i}")

        # Lista de producciones (consulta a BD)
        medir_peticion(session, "GET", f"{BASE_URL}/producciones/",
                        f"Usuario{usuario_id}-Producciones-{i}")

        # Reporte PDF de empleados (carga pesada: ReportLab)
        medir_peticion(session, "GET", f"{BASE_URL}/empleados/reporte/",
                        f"Usuario{usuario_id}-ReporteEmpleados-{i}")

        # Consulta a la IA (la más pesada: Gemini + pandas + sklearn)
        csrf_token = session.cookies.get("csrftoken")
        medir_peticion(
        session, "POST", f"{BASE_URL}/dashboard/ia/",
        f"Usuario{usuario_id}-IA-{i}",
        data={
        "pregunta": "¿Cómo va la producción esta semana?",
        "csrfmiddlewaretoken": csrf_token,
        },
        headers={"Referer": BASE_URL},
        )

        time.sleep(0.5)  # pequeña pausa entre peticiones, como un usuario real


def main():
    print(f"\n🚀 Iniciando test de estrés sobre {BASE_URL}")
    print(f"👥 {NUM_USUARIOS_CONCURRENTES} usuarios concurrentes")
    print(f"🔁 {NUM_PETICIONES_POR_USUARIO} repeticiones por usuario\n")

    inicio_total = time.time()

    with ThreadPoolExecutor(max_workers=NUM_USUARIOS_CONCURRENTES) as executor:
        futuros = [
            executor.submit(flujo_usuario, i)
            for i in range(1, NUM_USUARIOS_CONCURRENTES + 1)
        ]
        for f in as_completed(futuros):
            f.result()

    duracion_total = time.time() - inicio_total

    # ──────────────────────────────────────────────
    # REPORTE FINAL
    # ──────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("📊 RESULTADOS DEL TEST DE ESTRÉS")
    print("=" * 50)
    print(f"Tiempo total:         {duracion_total:.2f}s")
    print(f"Peticiones exitosas:  {resultados['exitosos']}")
    print(f"Peticiones fallidas:  {resultados['fallidos']}")

    if resultados["tiempos"]:
        print(f"Tiempo promedio:      {statistics.mean(resultados['tiempos']):.2f}s")
        print(f"Tiempo máximo:        {max(resultados['tiempos']):.2f}s")
        print(f"Tiempo mínimo:        {min(resultados['tiempos']):.2f}s")

    if resultados["errores"]:
        print("\n⚠️ ERRORES DETECTADOS:")
        for err in resultados["errores"][:20]:  # muestra máximo 20
            print(f"  - {err}")

    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()