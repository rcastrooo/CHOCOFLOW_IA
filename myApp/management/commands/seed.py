from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from myApp.models import Usuario


class Command(BaseCommand):
    help = 'Crea usuarios iniciales del sistema'

    def handle(self, *args, **kwargs):

        usuarios = [
            {
                "username": "admin001",
                "nombre": "Administrador Principal",
                "email": "admin@gmail.com",
                "password": "Admin123*",
                "rol": "Administrador",
                "estado": "Activo",
            },
            {
                "username": "super001",
                "nombre": "Supervisor Principal",
                "email": "supervisor@gmail.com",
                "password": "Super123*",
                "rol": "Supervisor",
                "estado": "Activo",
            },
        ]

        for u in usuarios:

            # Crear usuario de Django si no existe
            if not User.objects.filter(username=u['username']).exists():
                User.objects.create_user(
                    username=u['username'],
                    first_name=u['nombre'],
                    email=u['email'],
                    password=u['password']
                )
                self.stdout.write(self.style.SUCCESS(
                    f"✅ User Django creado: {u['username']}"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"⚠️  User Django ya existe: {u['username']}"
                ))

            # Crear perfil Usuario si no existe
            if not Usuario.objects.filter(email=u['email']).exists():
                Usuario.objects.create(
                    nombre=u['nombre'],
                    email=u['email'],
                    telefono=0,
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