from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = 'myApp'

    def ready(self):
        from . import scheduler
        scheduler.iniciar()