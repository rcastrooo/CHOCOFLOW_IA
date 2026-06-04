from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from myApp.models import Usuario, Turno

class Command(BaseCommand):
    help = 'Crea los usuarios iniciales'
    help = 'Crea usuarios y turnos iniciales del sistema'

    def handle(self, *args, **kwargs):

        # ========================
        # USUARIOS
        # ========================
        usuarios = [
            {
                "username": "admin001",
                "nombre":   "Administrador Principal",
                "email":    "admin@gmail.com",
                "password": "Admin123*",
                "rol":      "Administrador",
                "estado":   "Activo",
            },
            {
                "username": "super001",
                "nombre":   "Supervisor Principal",
                "email":    "supervisor@gmail.com",
                "password": "Super123*",
                "rol":      "Supervisor",
                "estado":   "Activo",
            },
        ]

        for u in usuarios:

            if not User.objects.filter(username=u['username']).exists():
                User.objects.create_user(
                    username   = u['username'],
                    first_name = u['nombre'],
                    email      = u['email'],
                    password   = u['password']
                )
                self.stdout.write(self.style.SUCCESS(
                    f"✅ User Django creado: {u['username']}"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"⚠️  User Django ya existe: {u['username']}"
                ))

            if not Usuario.objects.filter(email=u['email']).exists():
                Usuario.objects.create(
                    nombre=u['nombre'],
                    email=u['email'],
                    direccion='Sin dirección',
                    contrasena=u['password'],
                    rol=u['rol'],
                    estado=u['estado']
                )
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Perfil creado: {u['nombre']} ({u['rol']})"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"⚠️  Perfil ya existe: {u['email']}"
                ))

        self.stdout.write(self.style.SUCCESS('\n🍫 Seeder ejecutado correctamente.'))
        # ========================
        # TURNOS — dentro del handle
        # ========================
        admin = Usuario.objects.filter(rol='Administrador').first()

        if not admin:
            self.stdout.write(self.style.ERROR(
                '❌ No se encontró el admin para crear turnos.'
            ))
            return

        turnos = [
            {'horario': 'Mañana 6:00am - 2:00pm'},
            {'horario': 'Tarde 2:00pm - 10:00pm'},
            {'horario': 'Sábado Mañana 6:00am - 12:00pm'},
            {'horario': 'Sábado Tarde 12:00pm - 6:00pm'},
        ]

        for t in turnos:
            if not Turno.objects.filter(horario=t['horario']).exists():
                Turno.objects.create(
                    horario    = t['horario'],
                    activo     = True,
                    creado_por = admin
                )
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Turno creado: {t['horario']}"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"⚠️  Turno ya existe: {t['horario']}"
                ))

        self.stdout.write(self.style.SUCCESS(
            '\n🍫 Seeder ejecutado correctamente.'
        ))
