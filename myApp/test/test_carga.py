from locust import HttpUser, task, between
# locust -f test_carga.py --host=https://chocoflow.up.railway.app

class ChocoFlowUser(HttpUser):

    wait_time = between(1, 3)

    # PUBLICAS

    @task(3)
    def inicio(self):
        self.client.get("/")

    @task(2)
    def login(self):
        self.client.get("/login/")

    @task(1)
    def registro(self):
        self.client.get("/registro/")

    # ADMIN

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

    # SUPERVISOR

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