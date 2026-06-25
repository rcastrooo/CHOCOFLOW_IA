from locust import HttpUser, task, between
import re


class ChocoFlowUser(HttpUser):

    wait_time = between(1, 3)

    # ──────────────────────────────────────────────
    # CREDENCIALES DE PRUEBA — AJUSTA ESTO
    # ──────────────────────────────────────────────
    USERNAME = "supervisor@gmail.com"   # el correo del usuario de prueba
    PASSWORD = "Super123*"

    def on_start(self):
        """
        Se ejecuta UNA VEZ por cada usuario simulado, antes de
        empezar a correr las tareas (@task). Aquí hacemos login.
        """
        # 1. Cargar la página de login para obtener el csrftoken
        resp = self.client.get("/login/")

        # 2. Extraer el csrf_token del HTML (Django lo pone en un input hidden)
        match = re.search(r"name=['\"]csrfmiddlewaretoken['\"] value=['\"]([^'\"]+)['\"]", resp.text)
        csrf_token = match.group(1) if match else self.client.cookies.get("csrftoken")

        # 3. Hacer login con ese token
        login_resp = self.client.post(
            "/login/",
            data={
                "username": self.USERNAME,
                "password": self.PASSWORD,
                "csrfmiddlewaretoken": csrf_token,
            },
            headers={"Referer": f"{self.host}/login/"},
        )

        # 4. Confirmar que el login funcionó
        if "/login" in login_resp.url:
            print(f"⚠️ LOGIN FALLÓ para {self.USERNAME} - revisa usuario/contraseña")

    # ──────────────────────────────────────────────
    # PUBLICAS (no necesitan sesión)
    # ──────────────────────────────────────────────

    @task(3)
    def inicio(self):
        self.client.get("/")

    @task(1)
    def registro(self):
        self.client.get("/registro/")

    # ──────────────────────────────────────────────
    # ADMIN (rutas protegidas, ya con sesión activa)
    # ──────────────────────────────────────────────

    @task(2)
    def dashboard(self):
        self.client.get("/dashboard/")

    @task(2)
    def empleados(self):
        self.client.get("/empleados/")

    @task(2)
    def turnos(self):
        self.client.get("/turnos/")

    @task(2)
    def solicitudes(self):
        self.client.get("/solicitudes/")

    @task(2)
    def asignaciones(self):
        self.client.get("/asignaciones/")

    @task(2)
    def producciones(self):
        self.client.get("/producciones/")

    @task(2)
    def exportaciones(self):
        self.client.get("/exportaciones/")

    @task(2)
    def lotes(self):
        self.client.get("/lotes/")

    @task(2)
    def bitacoras(self):
        self.client.get("/bitacora/admin/")

    @task(1)
    def correos(self):
        self.client.get("/correos/")

    # ──────────────────────────────────────────────
    # SUPERVISOR (solo si tu usuario de prueba es Supervisor;
    # si es Administrador, estas rutas pueden redirigir distinto)
    # ──────────────────────────────────────────────

    @task(2)
    def dashboard_supervisor(self):
        self.client.get("/supervisor/")

    @task(2)
    def empleados_supervisor(self):
        self.client.get("/empleados/supervisor/")

    @task(2)
    def turnos_supervisor(self):
        self.client.get("/turnos/supervisor/")

    @task(2)
    def asignaciones_supervisor(self):
        self.client.get("/supervisor/asignaciones/")

    @task(2)
    def producciones_supervisor(self):
        self.client.get("/produccion/supervisor/")

    @task(2)
    def exportaciones_supervisor(self):
        self.client.get("/supervisor/exportaciones/")

    @task(2)
    def lotes_supervisor(self):
        self.client.get("/supervisor/lotes/")

    @task(2)
    def bitacoras_supervisor(self):
        self.client.get("/bitacora/mis-bitacoras/")