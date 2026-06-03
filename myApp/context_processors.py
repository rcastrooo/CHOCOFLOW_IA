from .models import Bitacora

def bitacoras_pendientes(request):
    count = 0
    if request.session.get('rol') == 'Administrador':
        count = Bitacora.objects.filter(estado='Enviado').count()
    return {'bitacoras_pendientes': count}