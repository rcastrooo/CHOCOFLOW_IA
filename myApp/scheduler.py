from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django.utils import timezone
import datetime

def rotar_turnos_job():
    from myApp.models import Empleado, Turno, RotacionTurno

    hoy    = timezone.now().date()
    lunes  = hoy - datetime.timedelta(days=hoy.weekday())
    viernes = lunes + datetime.timedelta(days=4)
    semana  = hoy.isocalendar()[1]

    turno_manana = Turno.objects.filter(horario='Mañana 6:00am - 2:00pm').first()
    turno_tarde  = Turno.objects.filter(horario='Tarde 2:00pm - 10:00pm').first()

    if not turno_manana or not turno_tarde:
        return

    empleados = Empleado.objects.filter(estado='Activo')

    for empleado in empleados:
        ya_tiene = RotacionTurno.objects.filter(
            empleado=empleado,
            fecha_inicio=lunes,
            fecha_fin=viernes
        ).exists()

        if ya_tiene:
            continue

        rotacion_anterior = RotacionTurno.objects.filter(
            empleado=empleado,
            semana=semana - 1
        ).first()

        if rotacion_anterior:
            turno_asignado = turno_tarde if rotacion_anterior.turno == turno_manana else turno_manana
        else:
            count_m = RotacionTurno.objects.filter(semana=semana, turno=turno_manana).count()
            count_t = RotacionTurno.objects.filter(semana=semana, turno=turno_tarde).count()
            turno_asignado = turno_manana if count_m <= count_t else turno_tarde

        RotacionTurno.objects.create(
            empleado     = empleado,
            turno        = turno_asignado,
            fecha_inicio = lunes,
            fecha_fin    = viernes,
            semana       = semana,
            estado       = 'Asignado'
        )


def iniciar():
    scheduler = BackgroundScheduler(timezone='America/Bogota')
    scheduler.add_jobstore(DjangoJobStore(), 'default')

    scheduler.add_job(
        rotar_turnos_job,
        trigger=CronTrigger(day_of_week='mon', hour=0, minute=5),
        id='rotar_turnos_semanal',
        replace_existing=True,
    )

    # Si es lunes y el servidor arranca, corre la rotación por si acaso
    from django.utils import timezone as tz
    if tz.now().weekday() == 0:
        rotar_turnos_job()

    scheduler.start()