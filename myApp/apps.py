from django.apps import AppConfig
import os


class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myApp'

    def ready(self):
        if os.environ.get('RUN_SCHEDULER') == 'True':
            from . import scheduler
            scheduler.iniciar()