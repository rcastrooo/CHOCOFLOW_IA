from django.core.management.base import BaseCommand
from django.utils import timezone
from myApp.models import Empleado, Turno, RotacionTurno
import datetime


class Command(BaseCommand):
    help = 'Genera la rotación semanal de turnos automáticamente'

    def handle(self, *args, **kwargs):

        hoy        = timezone.now().date()
        # Lunes de esta semana
        lunes      = hoy - datetime.timedelta(days=hoy.weekday())
        # Viernes de esta semana
        viernes    = lunes + datetime.timedelta(days=4)
        # Número de semana del año
        semana     = hoy.isocalendar()[1]

        empleados  = Empleado.objects.filter(estado='Activo')

        # Turnos normales
        turno_manana = Turno.objects.filter(horario='Mañana 6:00am - 2:00pm').first()
        turno_tarde  = Turno.objects.filter(horario='Tarde 2:00pm - 10:00pm').first()

        if not turno_manana or not turno_tarde:
            self.stdout.write(self.style.ERROR('❌ No existen los turnos base. Créalos primero.'))
            return

        # Contar cuántos empleados hay en cada turno esta semana
        count_manana = RotacionTurno.objects.filter(
            semana=semana, turno=turno_manana
        ).count()
        count_tarde  = RotacionTurno.objects.filter(
            semana=semana, turno=turno_tarde
        ).count()

        for empleado in empleados:

            # Verificar si ya tiene turno esta semana
            ya_tiene = RotacionTurno.objects.filter(
                empleado=empleado,
                fecha_inicio=lunes,
                fecha_fin=viernes
            ).exists()

            if ya_tiene:
                self.stdout.write(self.style.WARNING(
                    f"⚠️  {empleado.nombre} ya tiene turno esta semana."
                ))
                continue

            # Buscar turno de la semana anterior
            semana_anterior = semana - 1
            rotacion_anterior = RotacionTurno.objects.filter(
                empleado=empleado,
                semana=semana_anterior
            ).first()

            if rotacion_anterior:
                # Rotar al turno contrario
                if rotacion_anterior.turno == turno_manana:
                    turno_asignado = turno_tarde
                else:
                    turno_asignado = turno_manana
            else:
                # Sin historial → asignar al turno con menos empleados
                if count_manana <= count_tarde:
                    turno_asignado = turno_manana
                    count_manana  += 1
                else:
                    turno_asignado = turno_tarde
                    count_tarde   += 1

            RotacionTurno.objects.create(
                empleado    = empleado,
                turno       = turno_asignado,
                fecha_inicio = lunes,
                fecha_fin    = viernes,
                semana       = semana,
                estado       = 'Asignado'
            )

            self.stdout.write(self.style.SUCCESS(
                f"✅ {empleado.nombre} → {turno_asignado.horario} (Semana {semana})"
            ))

        # ---- SÁBADOS ----
        self.asignar_sabados(lunes, semana, empleados)

        self.stdout.write(self.style.SUCCESS('\n🍫 Rotación semanal completada.'))


    def asignar_sabados(self, lunes, semana, empleados):

        sabado = lunes + datetime.timedelta(days=5)
        mes    = sabado.month

        turno_sab_manana = Turno.objects.filter(horario='Sábado Mañana 6:00am - 12:00pm').first()
        turno_sab_tarde  = Turno.objects.filter(horario='Sábado Tarde 12:00pm - 6:00pm').first()

        if not turno_sab_manana or not turno_sab_tarde:
            self.stdout.write(self.style.WARNING('⚠️  No existen turnos de sábado.'))
            return

        for empleado in empleados:

            # Contar sábados trabajados este mes
            sabados_mes = RotacionTurno.objects.filter(
                empleado       = empleado,
                sabado_asignado = True,
                fecha_inicio__month = mes
            ).count()

            if sabados_mes >= 2:
                self.stdout.write(self.style.WARNING(
                    f"⚠️  {empleado.nombre} ya tiene 2 sábados este mes."
                ))
                continue

            # Todos trabajan el mismo sábado en diferente horario
            # Par → mañana, Impar → tarde
            if empleado.id % 2 == 0:
                turno_sab = turno_sab_manana
            else:
                turno_sab = turno_sab_tarde

            RotacionTurno.objects.create(
                empleado        = empleado,
                turno           = turno_sab,
                fecha_inicio    = sabado,
                fecha_fin       = sabado,
                semana          = semana,
                estado          = 'Asignado',
                sabado_asignado = True
            )

            self.stdout.write(self.style.SUCCESS(
                f"✅ Sábado: {empleado.nombre} → {turno_sab.horario}"
            ))