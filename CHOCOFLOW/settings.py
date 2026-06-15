from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

# ==========================================================
# VARIABLES DE ENTORNO
# ==========================================================
load_dotenv()

# ==========================================================
# RUTA BASE DEL PROYECTO
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ==========================================================
# SEGURIDAD
# ==========================================================
SECRET_KEY = os.getenv(
    'Lucky123*',
    'django-insecure-cambia-esto-en-produccion'
)

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    '.railway.app',
    'localhost',
    '127.0.0.1',
]

# ==========================================================
# APPS INSTALADAS
# ==========================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_apscheduler',

    'myApp',
]

# ==========================================================
# MIDDLEWARE
# ==========================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ==========================================================
# URLS
# ==========================================================
ROOT_URLCONF = 'CHOCOFLOW.urls'

# ==========================================================
# TEMPLATES
# ==========================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                'myApp.context_processors.bitacoras_pendientes',
            ],
        },
    },
]

# ==========================================================
# WSGI
# ==========================================================
WSGI_APPLICATION = 'CHOCOFLOW.wsgi.application'

# ==========================================================
# BASE DE DATOS
# ==========================================================

# Railway
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }

# Local (MariaDB/MySQL)
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'chocoflow',
            'USER': 'root',
            'PASSWORD': '',
            'HOST': 'localhost',
            'PORT': '3306',
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
            }
        }
    }

# ==========================================================
# VALIDACIÓN DE CONTRASEÑAS
# ==========================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ==========================================================
# INTERNACIONALIZACIÓN
# ==========================================================
LANGUAGE_CODE = 'es-co'

TIME_ZONE = 'America/Bogota'

USE_I18N = True

USE_TZ = True

# ==========================================================
# ARCHIVOS ESTÁTICOS
# ==========================================================
STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'myApp' / 'static',
]
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
)

# ==========================================================
# ARCHIVOS MULTIMEDIA
# ==========================================================
MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'

# ==========================================================
# TIPO DE CLAVE PRIMARIA
# ==========================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==========================================================
# CONFIGURACIÓN DE CORREO
# ==========================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'smtp.gmail.com'

EMAIL_PORT = 587

EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.getenv('castromatallana2006@gmail.com')

EMAIL_HOST_PASSWORD = os.getenv('tmdb xvlz lndj viek')

DEFAULT_FROM_EMAIL = (
    f'ChocoFlow <{EMAIL_HOST_USER}>'
)
