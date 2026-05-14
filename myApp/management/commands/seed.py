from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from myApp.models import Usuario

class Command(BaseCommand):
    help = 'Crea los usuarios iniciales'

    def handle(self, *args, **kwargs):

        usuarios = [
            {
                "username": "admin001",
                "nombre": "Administrador Principal",
                "email": "admin@gmail.com",
                "password": "Admin1234",
                "rol": "Administrador",
                "estado": "Activo",
            },
            {
                "username": "super001",
                "nombre": "Supervisor Principal",
                "email": "supervisor@gmail.com",
                "password": "Super1234",
                "rol": "Supervisor",
                "estado": "Activo",
            },
        ]

        for u in usuarios:
            if not User.objects.filter(username=u["username"]).exists():
                django_user = User.objects.create_user(
                    username=u["username"],
                    email=u["email"],
                    password=u["password"],        # Django encripta esto automáticamente
                    first_name=u["nombre"],
                )
                print(f"User creado: {u['email']}")
            else:
                django_user = User.objects.get(username=u["username"])
                print(f"Ya existe: {u['email']}")

            if not Usuario.objects.filter(email=u["email"]).exists():
                Usuario.objects.create(
                    nombre=u["nombre"],
                    email=u["email"],
                    telefono=0,
                    direccion="Sin definir",
                    contrasena=django_user.password,   # guarda el hash, NO texto plano
                    rol=u["rol"],
                    estado=u["estado"],
                )
                print(f"Perfil creado: {u['rol']}")
            else:
                print(f"Perfil ya existe: {u['email']}")

        print("\n Seed completado.")