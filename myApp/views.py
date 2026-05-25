from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from io import BytesIO
from dotenv import load_dotenv
from google import genai
import os
import json
import re

load_dotenv()

from datetime import date
from .models import (
    Usuario,
    Empleado,
    Turno,
    RotacionTurno,
    Solicitud,
    Asignacion,
    Produccion,
    Lote,
    Exportacion,
    Bitacora,
)

# ========================
# FUNCIÓN AUXILIAR
# ========================

def parse_body(request):
    try:
        return json.loads(request.body)
    except Exception:
        return {}


# ========================
# INDEX — si no hay sesión, va al login
# ========================

def index(request):
    if request.user.is_authenticated:
        rol = request.session.get('rol', '').strip()
        if rol == 'Administrador':
            return redirect('dashboard')
        elif rol == 'Supervisor':
            return redirect('dashboard_supervisor')
    return render(request, 'index.html')


# ========================
# LOGIN
# ========================

def login_usuario(request):

    if request.user.is_authenticated:
        rol = request.session.get('rol', '').strip()
        if rol == 'Administrador':
            return redirect('dashboard')
        elif rol == 'Supervisor':
            return redirect('dashboard_supervisor')

    if request.method == 'POST':

        correo   = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not correo or not password:
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'auth/login.html')

        patron_correo = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
        if not re.match(patron_correo, correo):
            messages.error(request, "El correo no tiene un formato válido.")
            return render(request, 'auth/login.html')

        try:
            user_obj = User.objects.get(email=correo)
            user     = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None

        if user is not None:
            login(request, user)

            try:
                usuario_db = Usuario.objects.get(email=correo)
                request.session['usuario_id'] = usuario_db.id
                request.session['rol']        = usuario_db.rol.strip()

                # Guardar horario_fijo en sesión si es Supervisor
                # NOTA: horario_fijo se almacena en sesión (no en modelo Usuario)
                # El admin lo puede setear via gestionar_supervisores
                horario_fijo = request.session.get('horario_fijo', '')
                # Si ya existía en sesión lo mantenemos; si no, queda vacío hasta que admin lo asigne

                rol = usuario_db.rol.strip()

                if rol == 'Administrador':
                    return redirect('dashboard')
                elif rol == 'Supervisor':
                    return redirect('dashboard_supervisor')
                else:
                    messages.error(request, f"Rol no reconocido: '{rol}'")
                    return redirect('login')

            except Usuario.DoesNotExist:
                messages.error(request, "No existe perfil del usuario.")
                return redirect('login')
        else:
            messages.error(request, "Correo o contraseña incorrectos.")

    return render(request, 'auth/login.html')


# ========================
# CERRAR SESIÓN
# ========================

def cerrar_sesion(request):
    logout(request)
    request.session.flush()
    return redirect('index')


# ========================
# REGISTRO
# ========================

def registro(request):

    if request.method == 'POST':

        identificacion = request.POST.get('identificacion', '').strip()
        nombre         = request.POST.get('nombre', '').strip()
        correo         = request.POST.get('correo', '').strip()
        password       = request.POST.get('password', '').strip()
        rol            = request.POST.get('rol', '')
        estado         = request.POST.get('estado', '')

        # --- Validaciones ---
        if not identificacion.isdigit():
            messages.error(request, "La identificación solo debe contener números.")
            return redirect('registro')

        if len(identificacion) < 5:
            messages.error(request, "La identificación debe tener al menos 5 dígitos.")
            return redirect('registro')

        if not all(c.isalpha() or c.isspace() for c in nombre):
            messages.error(request, "El nombre solo debe contener letras.")
            return redirect('registro')

        if len(nombre) < 3:
            messages.error(request, "El nombre debe tener al menos 3 caracteres.")
            return redirect('registro')

        patron_correo = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
        if not re.match(patron_correo, correo):
            messages.error(request, "El correo no tiene un formato válido.")
            return redirect('registro')

        if len(password) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
            return redirect('registro')

        if not any(c.isupper() for c in password):
            messages.error(request, "La contraseña debe tener al menos una mayúscula.")
            return redirect('registro')

        if not any(c.isdigit() for c in password):
            messages.error(request, "La contraseña debe tener al menos un número.")
            return redirect('registro')

        if User.objects.filter(username=identificacion).exists():
            messages.error(request, "Esa identificación ya está registrada.")
            return redirect('registro')

        if User.objects.filter(email=correo).exists():
            messages.error(request, "Ese correo ya está registrado.")
            return redirect('registro')

        if not rol:
            messages.error(request, "Selecciona un rol.")
            return redirect('registro')

        if not estado:
            messages.error(request, "Selecciona un estado.")
            return redirect('registro')

        # --- Crear usuario Django ---
        User.objects.create_user(
            username   = identificacion,
            first_name = nombre,
            email      = correo,
            password   = password
        )

        # --- Crear perfil Usuario (modelo propio) ---
        # NOTA: el modelo tiene 'ttelefono' (typo real en el modelo),
        # pero como no lo tocamos lo dejamos con el campo correcto según el modelo.
        Usuario.objects.create(
            nombre     = nombre,
            email      = correo,
            direccion  = 'Sin dirección',
            contrasena = password,
            rol        = rol,
            estado     = estado,
        )

        messages.success(request, "Usuario registrado correctamente.")
        return redirect('login')

    return render(request, 'auth/registro.html')


# =======================
# DASHBOARD ADMINISTRADOR
# =======================

@login_required(login_url='login')
def dashboard(request):

    usuario_id     = request.session.get('usuario_id')
    usuario_nombre = 'Administrador'
    usuario_rol    = 'Administrador'

    try:
        usuario_db     = Usuario.objects.get(id=usuario_id)
        usuario_nombre = usuario_db.nombre
        usuario_rol    = usuario_db.rol
    except Usuario.DoesNotExist:
        pass

    total_usuarios           = Usuario.objects.count()
    total_empleados          = Empleado.objects.count()
    empleados_activos        = Empleado.objects.filter(estado='Activo').count()
    empleados_suspendidos    = Empleado.objects.filter(estado='Suspendido').count()
    total_producciones       = Produccion.objects.count()
    producciones_proceso     = Produccion.objects.filter(estado='En Proceso').count()
    producciones_finalizadas = Produccion.objects.filter(estado='Finalizado').count()
    total_exportaciones      = Exportacion.objects.count()
    exportaciones_pendientes = Exportacion.objects.filter(estado='Pendiente').count()
    total_lotes              = Lote.objects.count()
    bitacoras_pendientes     = Bitacora.objects.filter(estado='Enviado').count()
    solicitudes_pendientes   = Solicitud.objects.filter(estado='Pendiente').count()
    asignaciones             = Asignacion.objects.select_related('empleado').order_by('-id')[:5]
    producciones_recientes   = Produccion.objects.select_related('empleado_responsable').order_by('-id')[:5]

    context = {
        'usuario_nombre':           usuario_nombre,
        'usuario_rol':              usuario_rol,
        'total_usuarios':           total_usuarios,
        'total_empleados':          total_empleados,
        'empleados_activos':        empleados_activos,
        'empleados_suspendidos':    empleados_suspendidos,
        'total_producciones':       total_producciones,
        'producciones_proceso':     producciones_proceso,
        'producciones_finalizadas': producciones_finalizadas,
        'total_exportaciones':      total_exportaciones,
        'exportaciones_pendientes': exportaciones_pendientes,
        'total_lotes':              total_lotes,
        'bitacoras_pendientes':     bitacoras_pendientes,
        'solicitudes_pendientes':   solicitudes_pendientes,
        'asignaciones':             asignaciones,
        'producciones_recientes':   producciones_recientes,
    }

    return render(request, 'dashboard.html', context)


# =======================
# GESTIONAR SUPERVISORES
# =======================
# CORRECCIÓN: horario_fijo no existe en el modelo Usuario.
# Lo guardamos en la sesión usando un diccionario persistente en BD simulado
# a través de la sesión de Django. Si quieres persistencia real, agrega el
# campo al modelo. Por ahora usamos la sesión del request actual para demo,
# y guardamos en un dict global (cache simple) para que funcione entre sesiones.

_horarios_supervisores = {}  # {usuario_id: horario} — cache en memoria del proceso

@login_required(login_url='login')
def gestionar_supervisores(request):

    if request.method == 'POST':
        supervisor_id = request.POST.get('supervisor_id')
        horario       = request.POST.get('horario_fijo', '').strip()

        supervisor = get_object_or_404(Usuario, id=supervisor_id, rol='Supervisor')

        if not horario:
            messages.error(request, "Debes seleccionar un horario.")
            return redirect('gestionar_supervisores')

        # Persistimos en caché en memoria (reemplazar por campo en modelo para producción)
        _horarios_supervisores[supervisor.id] = horario

        messages.success(request, f"Horario de {supervisor.nombre} actualizado a '{horario}'.")
        return redirect('gestionar_supervisores')

    supervisores = Usuario.objects.filter(rol='Supervisor')

    # Inyectamos el horario asignado para cada supervisor desde caché
    supervisores_con_horario = []
    for sup in supervisores:
        supervisores_con_horario.append({
            'id':          sup.id,
            'nombre':      sup.nombre,
            'email':       sup.email,
            'estado':      sup.estado,
            'horario_fijo': _horarios_supervisores.get(sup.id, ''),
        })

    return render(request, 'modulos/supervisores/gestionar_supervisores.html', {
        'supervisores': supervisores_con_horario,
        'turnos':       Turno.objects.filter(activo=True),
    })


# =======================
# DASHBOARD SUPERVISOR
# =======================

@login_required(login_url='login')
def dashboard_supervisor(request):

    # Sincronizar horario del supervisor desde caché al iniciar sesión
    usuario_id = request.session.get('usuario_id')
    if usuario_id and usuario_id in _horarios_supervisores:
        request.session['horario_fijo'] = _horarios_supervisores[usuario_id]

    empleados_activos        = Empleado.objects.filter(estado='Activo').count()
    turnos                   = Turno.objects.count()
    producciones_proceso     = Produccion.objects.filter(estado='En Proceso').count()
    producciones_pendientes  = Produccion.objects.filter(estado='Pendiente').count()
    exportaciones_pendientes = Exportacion.objects.filter(estado='Pendiente').count()
    total_lotes              = Lote.objects.count()
    total_asignaciones       = Asignacion.objects.count()
    total_bitacora           = Bitacora.objects.count()
    asignaciones             = Asignacion.objects.select_related('empleado').order_by('-id')[:10]
    lotes                    = Lote.objects.order_by('-fecha_vencimiento')[:5]

    context = {
        'empleados_activos':        empleados_activos,
        'turnos':                   turnos,
        'producciones_proceso':     producciones_proceso,
        'producciones_pendientes':  producciones_pendientes,
        'exportaciones_pendientes': exportaciones_pendientes,
        'total_lotes':              total_lotes,
        'total_asignaciones':       total_asignaciones,
        'total_bitacora':           total_bitacora,
        'asignaciones':             asignaciones,
        'lotes':                    lotes,
    }

    return render(request, 'dashboard_supervisor.html', context)


# ========================
# API STATS SUPERVISOR
# ========================

@login_required(login_url='login')
def api_stats_supervisor(request):

    hoy = timezone.now().date()

    empleados_con_turno = RotacionTurno.objects.values_list('empleado_id', flat=True)

    sin_turno = Empleado.objects.filter(
        estado='Activo'
    ).exclude(
        id__in=empleados_con_turno
    ).count()

    turno = Turno.objects.filter(activo=True).first()

    data = {
        'total_empleados':          Empleado.objects.count(),
        'empleados_activos':        Empleado.objects.filter(estado='Activo').count(),
        'asignaciones_hoy':         Asignacion.objects.filter(fecha_asignacion=hoy).count(),
        'sin_turno':                sin_turno,
        'lotes_totales':            Lote.objects.count(),
        'exportaciones_pendientes': Exportacion.objects.filter(estado='Pendiente').count(),
        'exportaciones_enviadas':   Exportacion.objects.filter(estado='Enviado').count(),
        'bitacora_hoy':             Bitacora.objects.filter(fecha_registro=hoy).count(),
        'bitacora_pendientes':      Bitacora.objects.filter(fecha_registro=hoy, estado='Borrador').count(),
        'bitacora_enviados':        Bitacora.objects.filter(fecha_registro=hoy, estado='Enviado').count(),
        'turno_nombre':             turno.horario if turno else 'Sin turno hoy',
    }

    return JsonResponse(data)


# ===================
# EMPLEADOS
# ===================

@login_required(login_url='login')
def empleados(request):

    rol    = request.session.get('rol', '')
    query  = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    lista  = Empleado.objects.all()

    if rol == 'Supervisor':
        lista = lista.filter(estado='Activo')
    else:
        if estado and estado != 'Todos':
            lista = lista.filter(estado=estado)

    if query:
        lista = lista.filter(
            Q(nombre__icontains=query) |
            Q(cedula__icontains=query)  |
            Q(email__icontains=query)
        )

    return render(request, 'modulos/empleados/empleados.html', {
        'empleados': lista,
        'rol':       rol,
        'horario':   '',
        'fecha_hoy': date.today(),
        'busqueda':  query,
    })

@login_required(login_url='login')
def empleados_supervisor(request):

    query = request.GET.get('q', '')
    lista = Empleado.objects.filter(estado='Activo')

    if query:
        lista = lista.filter(
            Q(nombre__icontains=query) |
            Q(cedula__icontains=query)  |
            Q(email__icontains=query)
        )

    return render(request, 'modulos/empleados/empleados_supervisor.html', {
        'empleados': lista,
        'horario':   '',
        'fecha_hoy': date.today(),
        'busqueda':  query,
    })


@login_required(login_url='login')
def guardar_empleado(request):
    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')
        try:
            usuario_perfil = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            messages.error(request, "No se encontró tu perfil.")
            return redirect('login')

        empleado_id = request.POST.get('id')
        empleado    = get_object_or_404(Empleado, id=empleado_id) if empleado_id else Empleado()

        cedula    = request.POST.get('cedula', '').strip()
        nombre    = request.POST.get('nombre', '').strip()
        email     = request.POST.get('email', '').strip()
        telefono  = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        estado    = request.POST.get('estado', '').strip()

        if not nombre or not email or not estado:
            messages.error(request, "Nombre, email y estado son obligatorios.")
            return redirect('empleados')

        # Validar email duplicado (solo si es nuevo o cambió)
        if not empleado_id:
            if Empleado.objects.filter(email=email).exists():
                messages.error(request, "Ya existe un empleado con ese correo.")
                return redirect('empleados')
        else:
            if Empleado.objects.filter(email=email).exclude(id=empleado_id).exists():
                messages.error(request, "Ya existe un empleado con ese correo.")
                return redirect('empleados')

        empleado.cedula    = cedula
        empleado.nombre    = nombre
        empleado.email     = email
        empleado.telefono  = telefono
        empleado.direccion = direccion if direccion else 'Sin dirección'
        empleado.estado    = estado
        empleado.creado_por = usuario_perfil
        empleado.save()
        messages.success(request, "Empleado guardado correctamente.")

    return redirect('empleados')


@login_required(login_url='login')
def inactivar_empleado(request, id):
    empleado        = get_object_or_404(Empleado, id=id)
    empleado.estado = 'Inactivo'
    empleado.save()
    messages.success(request, f"{empleado.nombre} fue inactivado.")
    return redirect('empleados')


@login_required(login_url='login')
def generar_reporte_empleados(request):

    lista    = Empleado.objects.all()
    busqueda = request.GET.get('busqueda', '')
    estado   = request.GET.get('estado', '')

    if busqueda:
        lista = lista.filter(nombre__icontains=busqueda)
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)

    buffer    = BytesIO()
    doc       = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos   = getSampleStyleSheet()

    elementos.append(Paragraph("Reporte de Empleados - ChocoFlow", estilos['Title']))
    elementos.append(Spacer(1, 20))

    datos = [['Cédula', 'Nombre', 'Email', 'Teléfono', 'Estado']]
    for emp in lista:
        datos.append([
            emp.cedula or '',
            emp.nombre,
            emp.email,
            emp.telefono or '',
            emp.estado,
        ])

    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#603C1C')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('GRID',       (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_empleados.pdf"'
    response.write(pdf)
    return response


# ===================
# TURNOS
# ===================

@login_required(login_url='login')
def turnos(request):

    horario_filtro = request.GET.get('horario', '')
    semana_filtro  = request.GET.get('semana', '')
    semana_actual  = date.today().isocalendar()[1]

    lista = RotacionTurno.objects.select_related('empleado', 'turno').all()

    if horario_filtro:
        lista = lista.filter(turno__horario=horario_filtro)
    if semana_filtro:
        lista = lista.filter(semana=semana_filtro)

    return render(request, 'modulos/turnos/turnos.html', {
        'rotaciones':    lista,
        'semana_actual': semana_actual,
        'turnos':        Turno.objects.filter(activo=True),
        'empleados':     Empleado.objects.filter(estado='Activo'),
    })


@login_required(login_url='login')
def turnos_supervisor(request):

    busqueda = request.GET.get('q', '')

    lista = RotacionTurno.objects.select_related('empleado', 'turno').all().order_by('-fecha_inicio')

    if busqueda:
        lista = lista.filter(empleado__nombre__icontains=busqueda)

    return render(request, 'modulos/turnos/turnos_supervisor.html', {
        'turnos':    lista,
        'rol':       'Supervisor',
        'fecha_hoy': timezone.now().date(),
        'busqueda':  busqueda,
    })


@login_required(login_url='login')
def guardar_rotacion(request):
    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')

        rotacion_id  = request.POST.get('id', '').strip()
        empleado_id  = request.POST.get('empleado_id', '').strip()
        turno_id     = request.POST.get('turno_id', '').strip()
        fecha_inicio = request.POST.get('fecha_inicio', '').strip()
        fecha_fin    = request.POST.get('fecha_fin', '').strip()
        semana       = request.POST.get('semana', '').strip()
        sabado       = request.POST.get('sabado_asignado') == 'on'
        estado       = request.POST.get('estado', 'Pendiente')

        if not all([empleado_id, turno_id, fecha_inicio, fecha_fin, semana]):
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('turnos')

        # Validar que fecha_fin no sea anterior a fecha_inicio
        if fecha_fin < fecha_inicio:
            messages.error(request, "La fecha de fin no puede ser anterior a la de inicio.")
            return redirect('turnos')

        try:
            empleado = get_object_or_404(Empleado, id=empleado_id)
            turno    = get_object_or_404(Turno, id=turno_id)

            if rotacion_id:
                rot                 = get_object_or_404(RotacionTurno, id=rotacion_id)
                rot.empleado        = empleado
                rot.turno           = turno
                rot.fecha_inicio    = fecha_inicio
                rot.fecha_fin       = fecha_fin
                rot.semana          = int(semana)
                rot.sabado_asignado = sabado
                rot.estado          = estado
                rot.save()
                messages.success(request, "Rotación actualizada correctamente.")
            else:
                # Verificar constraint único (empleado + fecha_inicio + fecha_fin)
                if RotacionTurno.objects.filter(
                    empleado=empleado,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin
                ).exists():
                    messages.error(request, f"{empleado.nombre} ya tiene un turno asignado para ese período.")
                    return redirect('turnos')

                RotacionTurno.objects.create(
                    empleado        = empleado,
                    turno           = turno,
                    fecha_inicio    = fecha_inicio,
                    fecha_fin       = fecha_fin,
                    semana          = int(semana),
                    sabado_asignado = sabado,
                    estado          = estado,
                )
                messages.success(request, "Rotación registrada correctamente.")
        except Exception as e:
            messages.error(request, f"Error al guardar rotación: {str(e)}")

    return redirect('turnos')


@login_required(login_url='login')
def eliminar_rotacion(request, id):
    rot = get_object_or_404(RotacionTurno, id=id)
    rot.delete()
    messages.success(request, "Rotación eliminada correctamente.")
    return redirect('turnos')


@login_required
def rotacion_turnos(request):

    semana_filtro = request.GET.get('semana', '')
    lista = RotacionTurno.objects.select_related('empleado', 'turno').all()

    if semana_filtro:
        lista = lista.filter(semana=semana_filtro)

    return render(request, 'modulos/turnos/rotacion.html', {
        'rotaciones': lista,
    })


@login_required(login_url='login')
def generar_reporte_turnos(request):

    lista = Turno.objects.select_related('creado_por').filter(activo=True)

    buffer    = BytesIO()
    doc       = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos   = getSampleStyleSheet()

    elementos.append(Paragraph("Reporte de Turnos - ChocoFlow", estilos['Title']))
    elementos.append(Spacer(1, 20))

    datos = [['Horario', 'Estado', 'Creado por']]
    for t in lista:
        datos.append([
            t.horario,
            'Activo' if t.activo else 'Inactivo',
            t.creado_por.nombre,
        ])

    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#603C1C')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('GRID',       (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_turnos.pdf"'
    response.write(pdf)
    return response


@login_required(login_url='login')
def generar_reporte_rotacion(request):

    lista = RotacionTurno.objects.select_related('empleado', 'turno').all()

    buffer    = BytesIO()
    doc       = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos   = getSampleStyleSheet()

    elementos.append(Paragraph("Reporte de Rotación de Turnos - ChocoFlow", estilos['Title']))
    elementos.append(Spacer(1, 20))

    datos = [['Empleado', 'Turno', 'Semana', 'Fecha Inicio', 'Fecha Fin', 'Sábado', 'Estado']]
    for r in lista:
        datos.append([
            r.empleado.nombre,
            r.turno.horario,
            str(r.semana),
            str(r.fecha_inicio),
            str(r.fecha_fin),
            'Sí' if r.sabado_asignado else 'No',
            r.estado,
        ])

    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#603C1C')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('GRID',       (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_rotacion.pdf"'
    response.write(pdf)
    return response


# ===================
# SOLICITUDES
# ===================

@login_required(login_url='login')
def solicitudes(request):

    query  = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    lista  = Solicitud.objects.select_related(
        'empleado', 'turno_actual', 'turno_solicitado', 'revisado_por'
    ).all()

    if query:
        lista = lista.filter(empleado__nombre__icontains=query)
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)

    turnos_activos = Turno.objects.filter(activo=True)
    empleados_activos = Empleado.objects.filter(estado='Activo')

    return render(request, 'modulos/solicitudes/solicitudes.html', {
        'solicitudes': lista,
        'turnos':      turnos_activos,
        'empleados':   empleados_activos,
    })


@login_required(login_url='login')
def guardar_solicitud(request):
    if request.method == 'POST':

        empleado_id     = request.POST.get('empleado_id', '').strip()
        turno_actual_id = request.POST.get('turno_actual_id', '').strip()
        turno_sol_id    = request.POST.get('turno_solicitado_id', '').strip()
        motivo          = request.POST.get('motivo', '').strip()

        if not empleado_id or not turno_actual_id or not turno_sol_id or not motivo:
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('solicitudes')

        if turno_actual_id == turno_sol_id:
            messages.error(request, "El turno solicitado debe ser diferente al turno actual.")
            return redirect('solicitudes')

        if len(motivo) < 10:
            messages.error(request, "El motivo debe tener al menos 10 caracteres.")
            return redirect('solicitudes')

        Solicitud.objects.create(
            empleado         = get_object_or_404(Empleado, id=empleado_id),
            turno_actual     = get_object_or_404(Turno, id=turno_actual_id),
            turno_solicitado = get_object_or_404(Turno, id=turno_sol_id),
            motivo           = motivo,
            estado           = 'Pendiente',
        )
        messages.success(request, "Solicitud registrada correctamente.")

    return redirect('solicitudes')


@login_required(login_url='login')
def revisar_solicitud(request, id):
    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')

        usuario   = get_object_or_404(Usuario, id=usuario_id)
        solicitud = get_object_or_404(Solicitud, id=id)

        nuevo_estado = request.POST.get('estado', '').strip()
        estados_validos = ['Aprobado', 'Rechazado', 'Pendiente']

        if nuevo_estado not in estados_validos:
            messages.error(request, "Estado no válido.")
            return redirect('solicitudes')

        solicitud.estado       = nuevo_estado
        solicitud.revisado_por = usuario
        solicitud.save()

        messages.success(request, f"Solicitud {solicitud.estado.lower()} correctamente.")

    return redirect('solicitudes')


@login_required(login_url='login')
def generar_reporte_solicitudes(request):

    lista = Solicitud.objects.select_related(
        'empleado', 'turno_actual', 'turno_solicitado', 'revisado_por'
    ).all()

    buffer    = BytesIO()
    doc       = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos   = getSampleStyleSheet()

    elementos.append(Paragraph("Reporte de Solicitudes - ChocoFlow", estilos['Title']))
    elementos.append(Spacer(1, 20))

    datos = [['Empleado', 'Turno Actual', 'Turno Solicitado', 'Motivo', 'Estado', 'Revisado por']]
    for s in lista:
        datos.append([
            s.empleado.nombre,
            s.turno_actual.horario,
            s.turno_solicitado.horario,
            s.motivo[:50],
            s.estado,
            s.revisado_por.nombre if s.revisado_por else 'Pendiente',
        ])

    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#603C1C')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('GRID',       (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_solicitudes.pdf"'
    response.write(pdf)
    return response


# ===================
# ASIGNACIONES
# ===================

@login_required(login_url='login')
def asignaciones(request):
 
    query  = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
 
    lista = Asignacion.objects.select_related(
        'empleado', 'turno', 'asignado_por'
    ).all()
 
    if query:
        lista = lista.filter(
            Q(tarea__icontains=query) |
            Q(empleado__nombre__icontains=query)
        )
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)
 
    empleados_activos = Empleado.objects.filter(estado='Activo')
    turnos_activos    = Turno.objects.filter(activo=True)
 
    return render(request, 'modulos/asignaciones/asignaciones.html', {
        'asignaciones': lista,
        'empleados':    empleados_activos,
        'turnos':       turnos_activos,
    })
 
 
# ─────────────────────────────────────────────
#  ADMIN — Crear / Editar asignación
# ─────────────────────────────────────────────
@login_required(login_url='login')
def guardar_asignacion(request):
    if request.method != 'POST':
        return redirect('asignaciones')
 
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        messages.error(request, "Sesión inválida.")
        return redirect('login')
 
    try:
        usuario_perfil = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "No se encontró tu perfil.")
        return redirect('login')
 
    asignacion_id = request.POST.get('id', '').strip()
    tarea         = request.POST.get('tarea', '').strip()
    fecha         = request.POST.get('fecha_asignacion', '').strip()
    emp_id        = request.POST.get('empleado_id', '').strip()
    turno_id      = request.POST.get('turno_id', '').strip()
    estado        = request.POST.get('estado', 'Pendiente')
 
    if not tarea or not fecha or not emp_id or not turno_id:
        messages.error(request, "Todos los campos son obligatorios.")
        return redirect('asignaciones')
 
    empleado = get_object_or_404(Empleado, id=emp_id)
    turno    = get_object_or_404(Turno, id=turno_id)
 
    if asignacion_id:
        asignacion = get_object_or_404(Asignacion, id=asignacion_id)
    else:
        asignacion = Asignacion()
 
    asignacion.tarea            = tarea
    asignacion.fecha_asignacion = fecha
    asignacion.empleado         = empleado
    asignacion.turno            = turno
    asignacion.asignado_por     = usuario_perfil
    asignacion.estado           = estado
 
    try:
        asignacion.save()
        messages.success(request, "Asignación guardada correctamente.")
    except Exception as e:
        messages.error(request, str(e))
 
    return redirect('asignaciones')
 
 
# ─────────────────────────────────────────────
#  ADMIN — Inactivar / Finalizar asignación
# ─────────────────────────────────────────────
@login_required(login_url='login')
def inactivar_asignacion(request, id):
    asignacion        = get_object_or_404(Asignacion, id=id)
    asignacion.estado = 'Finalizado'
    asignacion.save()
    messages.success(request, "Asignación finalizada.")
    return redirect('asignaciones')
 
 
# ─────────────────────────────────────────────
#  SUPERVISOR — Listado de asignaciones
# ─────────────────────────────────────────────
@login_required(login_url='login')
def asignaciones_supervisor(request):
 
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')
 
    busqueda = request.GET.get('q', '')
 
    lista = Asignacion.objects.select_related(
        'empleado', 'turno', 'asignado_por'
    ).order_by('-fecha_asignacion')
 
    if busqueda:
        lista = lista.filter(
            Q(tarea__icontains=busqueda) |
            Q(empleado__nombre__icontains=busqueda)
        )
 
    empleados_activos = Empleado.objects.filter(estado='Activo')
    turnos_activos    = Turno.objects.filter(activo=True)
 
    return render(request, 'modulos/asignaciones/asignaciones_supervisor.html', {
        'asignaciones': lista,
        'busqueda':     busqueda,
        'empleados':    empleados_activos,
        'turnos':       turnos_activos,
        'fecha_hoy':    timezone.now().date(),
    })
 
 
# ─────────────────────────────────────────────
#  SUPERVISOR — Solo crear asignación
# ─────────────────────────────────────────────
@login_required(login_url='login')
def guardar_asignacion_supervisor(request):
    if request.method != 'POST':
        return redirect('asignaciones_supervisor')
 
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        messages.error(request, "Sesión inválida.")
        return redirect('login')
 
    try:
        usuario_perfil = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "No se encontró tu perfil.")
        return redirect('login')
 
    tarea    = request.POST.get('tarea', '').strip()
    fecha    = request.POST.get('fecha_asignacion', '').strip()
    emp_id   = request.POST.get('empleado_id', '').strip()
    turno_id = request.POST.get('turno_id', '').strip()
 
    if not tarea or not fecha or not emp_id or not turno_id:
        messages.error(request, "Todos los campos son obligatorios.")
        return redirect('asignaciones_supervisor')
 
    empleado = get_object_or_404(Empleado, id=emp_id)
    turno    = get_object_or_404(Turno, id=turno_id)
 
    asignacion                  = Asignacion()
    asignacion.tarea            = tarea
    asignacion.fecha_asignacion = fecha
    asignacion.empleado         = empleado
    asignacion.turno            = turno
    asignacion.asignado_por     = usuario_perfil
    asignacion.estado           = 'Pendiente'
 
    try:
        asignacion.save()
        messages.success(request, "Asignación creada correctamente.")
    except Exception as e:
        messages.error(request, str(e))
 
    return redirect('asignaciones_supervisor')
 
 
# ─────────────────────────────────────────────
#  ADMIN — Generar reporte PDF de asignaciones
# ─────────────────────────────────────────────
@login_required(login_url='login')
def generar_reporte_asignaciones(request):
 
    query = request.GET.get('q', '')
 
    lista = Asignacion.objects.select_related(
        'empleado', 'turno', 'asignado_por'
    ).all()
 
    if query:
        lista = lista.filter(
            Q(tarea__icontains=query) |
            Q(empleado__nombre__icontains=query)
        )
 
    buffer    = BytesIO()
    doc       = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos   = getSampleStyleSheet()
 
    elementos.append(Paragraph("Reporte de Asignaciones - ChocoFlow", estilos['Title']))
    elementos.append(Spacer(1, 20))
 
    datos = [['Tarea', 'Empleado', 'Turno', 'Fecha', 'Estado', 'Asignado por']]
    for a in lista:
        datos.append([
            a.tarea,
            a.empleado.nombre,
            a.turno.horario,
            str(a.fecha_asignacion),
            a.estado,
            a.asignado_por.nombre,
        ])
 
    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#603C1C')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('GRID',       (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
    ]))
 
    elementos.append(tabla)
    doc.build(elementos)
 
    pdf = buffer.getvalue()
    buffer.close()
 
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_asignaciones.pdf"'
    response.write(pdf)
    return response
 


# ===================
# PRODUCCION
# ===================

@login_required(login_url='login')
def producciones(request):

    query  = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    lista  = Produccion.objects.select_related('empleado_responsable', 'creado_por').all()

    if query:
        lista = lista.filter(
            Q(producto__icontains=query) |
            Q(empleado_responsable__nombre__icontains=query)
        )
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)

    empleados = Empleado.objects.filter(estado='Activo')

    return render(request, 'modulos/produccion/produccion.html', {
        'producciones': lista,
        'empleados':    empleados,
    })


@login_required(login_url='login')
def guardar_produccion(request):
    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')
        try:
            usuario_perfil = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            messages.error(request, "No se encontró tu perfil.")
            return redirect('login')

        produccion_id = request.POST.get('id', '').strip()

        # Campos reales del modelo Produccion
        producto           = request.POST.get('producto', '').strip()
        ingredientes       = request.POST.get('ingredientes', '').strip()
        cantidad_requerida = request.POST.get('cantidad_requerida', '').strip()
        fecha_entrega      = request.POST.get('fecha_entrega', '').strip()
        fecha_limite       = request.POST.get('fecha_limite', '').strip()
        estado             = request.POST.get('estado', '').strip()
        emp_id             = request.POST.get('empleado_responsable', '').strip()

        if not producto or not emp_id or not fecha_entrega or not fecha_limite or not estado:
            messages.error(request, "Los campos obligatorios no pueden estar vacíos.")
            return redirect('producciones')

        if not ingredientes:
            messages.error(request, "Los ingredientes son obligatorios.")
            return redirect('producciones')

        # Validar que fecha_limite no sea anterior a fecha_entrega
        if fecha_limite < fecha_entrega:
            messages.error(request, "La fecha límite no puede ser anterior a la fecha de entrega.")
            return redirect('producciones')

        empleado = get_object_or_404(Empleado, id=emp_id)

        if produccion_id:
            produccion = get_object_or_404(Produccion, id=produccion_id)
        else:
            produccion = Produccion()

        produccion.producto           = producto
        produccion.ingredientes       = ingredientes
        produccion.cantidad_requerida = cantidad_requerida
        produccion.fecha_entrega      = fecha_entrega
        produccion.fecha_limite       = fecha_limite
        produccion.estado             = estado
        produccion.empleado_responsable = empleado
        produccion.creado_por           = usuario_perfil

        try:
            produccion.save()
            messages.success(request, "Producción guardada correctamente.")
        except Exception as e:
            messages.error(request, f"Error al guardar: {str(e)}")

    return redirect('producciones')


@login_required(login_url='login')
def inactivar_produccion(request, id):
    produccion        = get_object_or_404(Produccion, id=id)
    produccion.estado = 'Cancelado'
    produccion.save()
    messages.success(request, "Producción cancelada.")
    return redirect('producciones')


@login_required(login_url='login')
def generar_reporte_producciones(request):

    lista  = Produccion.objects.select_related('empleado_responsable').all()
    query  = request.GET.get('q', '')
    estado = request.GET.get('estado', '')

    if query:
        lista = lista.filter(producto__icontains=query)
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)

    buffer    = BytesIO()
    doc       = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos   = getSampleStyleSheet()

    elementos.append(Paragraph("Reporte de Producciones - ChocoFlow", estilos['Title']))
    elementos.append(Spacer(1, 20))

    # Columnas ajustadas a campos reales del modelo
    datos = [['Producto', 'Responsable', 'Cant. Requerida', 'Fecha Entrega', 'Fecha Límite', 'Estado']]
    for p in lista:
        datos.append([
            p.producto or '',
            p.empleado_responsable.nombre,
            p.cantidad_requerida or '',
            str(p.fecha_entrega),
            str(p.fecha_limite),
            p.estado,
        ])

    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#603C1C')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('GRID',       (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_producciones.pdf"'
    response.write(pdf)
    return response

# La misma monda pero del supervisor
@login_required(login_url='login')
def producciones_supervisor(request):
    query  = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    lista  = Produccion.objects.select_related('empleado_responsable').all()

    if query:
        lista = lista.filter(producto__icontains=query)
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)

    empleados = Empleado.objects.filter(estado='Activo')

    return render(request, 'modulos/produccion/produccion_supervisor.html', {
        'producciones': lista,
        'empleados':    empleados,
        'fecha_hoy':    timezone.now().date(),
    })


# ===================
# EXPORTACIONES
# ===================
# CORRECCIÓN: Exportacion no tiene campo 'creado_por' en el modelo.
# Se eliminó esa asignación.

@login_required(login_url='login')
def gestionar_exportaciones(request):

    q      = request.GET.get('q', '')
    estado = request.GET.get('estado', '')

    exportaciones = Exportacion.objects.all()

    if q:
        exportaciones = exportaciones.filter(destino__icontains=q)
    if estado:
        exportaciones = exportaciones.filter(estado=estado)

    # Solo producciones En Proceso o Pendiente para asociar a exportaciones
    producciones = Produccion.objects.filter(estado__in=['En Proceso', 'Pendiente'])

    return render(request, 'modulos/exportaciones/exportaciones.html', {
        'exportaciones': exportaciones,
        'producciones':  producciones,
        'q':             q,
        'estado_filtro': estado,
    })


@login_required(login_url='login')
def exportaciones_supervisor(request):
    busqueda      = request.GET.get('q', '')
    estado_filtro = request.GET.get('estado', '')

    lista = Exportacion.objects.all().order_by('-fecha_envio')

    if busqueda:
        lista = lista.filter(
            Q(destino__icontains=busqueda) |
            Q(producto__icontains=busqueda)
        )
    if estado_filtro and estado_filtro != 'Todos':
        lista = lista.filter(estado=estado_filtro)

    return render(request, 'modulos/exportaciones/exportaciones_supervisor.html', {
        'exportaciones': lista,
        'busqueda':      busqueda,
        'estado_filtro': estado_filtro,
        'fecha_hoy':     timezone.now().date(),
    })


@login_required(login_url='login')
def guardar_exportacion(request):
    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')
        # Verificamos que el usuario existe aunque Exportacion no tenga creado_por
        try:
            Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            messages.error(request, "No se encontró tu perfil.")
            return redirect('login')

        exp_id        = request.POST.get('id', '').strip()
        destino       = request.POST.get('destino', '').strip()
        pais          = request.POST.get('pais', 'Colombia').strip()
        producto      = request.POST.get('producto', '').strip()
        fecha_envio   = request.POST.get('fecha_envio', '').strip()
        fecha_entrega = request.POST.get('fecha_entrega', '').strip()
        estado        = request.POST.get('estado', '').strip()
        produccion_id = request.POST.get('produccion_id', '').strip()

        if not destino or not fecha_envio or not fecha_entrega or not estado:
            messages.error(request, "Destino, fechas y estado son obligatorios.")
            return redirect('gestionar_exportaciones')

        if fecha_entrega < fecha_envio:
            messages.error(request, 'La fecha de entrega no puede ser anterior a la de envío.')
            return redirect('gestionar_exportaciones')

        produccion = Produccion.objects.filter(id=produccion_id).first() if produccion_id else None

        if exp_id:
            exp               = get_object_or_404(Exportacion, pk=exp_id)
            exp.destino       = destino
            exp.pais          = pais
            exp.producto      = producto
            exp.fecha_envio   = fecha_envio
            exp.fecha_entrega = fecha_entrega
            exp.estado        = estado
            exp.produccion    = produccion
            exp.save()
            messages.success(request, 'Exportación actualizada correctamente.')
        else:
            Exportacion.objects.create(
                destino       = destino,
                pais          = pais,
                producto      = producto,
                fecha_envio   = fecha_envio,
                fecha_entrega = fecha_entrega,
                estado        = estado,
                produccion    = produccion,
                # Sin creado_por: el modelo Exportacion no tiene ese campo
            )
            messages.success(request, 'Exportación creada correctamente.')

    return redirect('gestionar_exportaciones')


@login_required(login_url='login')
def inactivar_exportacion(request, id):
    exp        = get_object_or_404(Exportacion, pk=id)
    exp.estado = 'Cancelado'
    exp.save()
    messages.success(request, 'Exportación cancelada correctamente.')
    return redirect('gestionar_exportaciones')


@login_required(login_url='login')
def generar_reporte_exportaciones(request):

    exportaciones = Exportacion.objects.all()
    busqueda      = request.GET.get('busqueda', '')
    estado        = request.GET.get('estado', '')

    if busqueda:
        exportaciones = exportaciones.filter(destino__icontains=busqueda)
    if estado and estado != "Todos":
        exportaciones = exportaciones.filter(estado=estado)

    buffer    = BytesIO()
    doc       = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos   = getSampleStyleSheet()

    elementos.append(Paragraph("Reporte de Exportaciones - ChocoFlow", estilos['Title']))
    elementos.append(Spacer(1, 20))

    datos = [['Destino', 'País', 'Producto', 'Fecha Envío', 'Fecha Entrega', 'Estado']]
    for exp in exportaciones:
        datos.append([
            exp.destino,
            exp.pais,
            exp.producto,
            str(exp.fecha_envio),
            str(exp.fecha_entrega),
            exp.estado,
        ])

    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#603C1C')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('GRID',       (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_exportaciones.pdf"'
    response.write(pdf)
    return response


# ===================
# LOTES
# ===================

@login_required(login_url='login')
def gestionar_lotes(request):

    q     = request.GET.get('q', '')
    lotes = Lote.objects.select_related('produccion', 'exportacion').all()

    if q:
        lotes = lotes.filter(codigo_lote__icontains=q)

    producciones  = Produccion.objects.all()
    exportaciones = Exportacion.objects.all()

    return render(request, 'modulos/lotes/lotes.html', {
        'lotes':         lotes,
        'producciones':  producciones,
        'exportaciones': exportaciones,
        'q':             q,
    })


@login_required(login_url='login')
def lotes_supervisor(request):
    busqueda = request.GET.get('q', '')

    lista = Lote.objects.select_related(
        'produccion', 'exportacion'
    ).order_by('-fecha_produccion')

    if busqueda:
        lista = lista.filter(codigo_lote__icontains=busqueda)

    return render(request, 'modulos/lotes/lotes_supervisor.html', {
        'lotes':     lista,
        'busqueda':  busqueda,
        'fecha_hoy': timezone.now().date(),
    })
    
@login_required(login_url='login')
def guardar_lote(request):
    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')

        lote_id           = request.POST.get('id', '').strip()
        codigo_lote       = request.POST.get('codigo_lote', '').strip()
        cantidad          = request.POST.get('cantidad', '').strip()
        fecha_produccion  = request.POST.get('fecha_produccion', '').strip()
        fecha_vencimiento = request.POST.get('fecha_vencimiento', '').strip()
        produccion_id     = request.POST.get('produccion_id', '').strip()
        exportacion_id    = request.POST.get('exportacion_id', '').strip()

        if not all([codigo_lote, cantidad, fecha_produccion, fecha_vencimiento, produccion_id, exportacion_id]):
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('gestionar_lotes')

        if fecha_vencimiento < fecha_produccion:
            messages.error(request, "La fecha de vencimiento no puede ser anterior a la de producción.")
            return redirect('gestionar_lotes')

        produccion  = get_object_or_404(Produccion,  pk=produccion_id)
        exportacion = get_object_or_404(Exportacion, pk=exportacion_id)

        if lote_id:
            lote                   = get_object_or_404(Lote, pk=lote_id)
            lote.codigo_lote       = codigo_lote
            lote.cantidad          = cantidad
            lote.fecha_produccion  = fecha_produccion
            lote.fecha_vencimiento = fecha_vencimiento
            lote.produccion        = produccion
            lote.exportacion       = exportacion
            lote.save()
            messages.success(request, f"Lote '{codigo_lote}' actualizado correctamente.")
        else:
            if Lote.objects.filter(codigo_lote=codigo_lote).exists():
                messages.error(request, f"Ya existe un lote con el código '{codigo_lote}'.")
                return redirect('gestionar_lotes')
            Lote.objects.create(
                codigo_lote       = codigo_lote,
                cantidad          = cantidad,
                fecha_produccion  = fecha_produccion,
                fecha_vencimiento = fecha_vencimiento,
                produccion        = produccion,
                exportacion       = exportacion,
            )
            messages.success(request, f"Lote '{codigo_lote}' creado correctamente.")

    return redirect('gestionar_lotes')


@login_required(login_url='login')
def eliminar_lote(request, id):
    lote   = get_object_or_404(Lote, pk=id)
    codigo = lote.codigo_lote
    lote.delete()
    messages.success(request, f"Lote '{codigo}' eliminado correctamente.")
    return redirect('gestionar_lotes')


@login_required(login_url='login')
def generar_reporte_lotes(request):

    lotes    = Lote.objects.select_related('produccion', 'exportacion').all()
    busqueda = request.GET.get('busqueda', '')

    if busqueda:
        lotes = lotes.filter(codigo_lote__icontains=busqueda)

    buffer    = BytesIO()
    doc       = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos   = getSampleStyleSheet()

    elementos.append(Paragraph("Reporte de Lotes - ChocoFlow", estilos['Title']))
    elementos.append(Spacer(1, 20))

    datos = [['Código Lote', 'Cantidad', 'Fecha Producción', 'Fecha Vencimiento', 'Producción', 'Exportación']]
    for lote in lotes:
        datos.append([
            lote.codigo_lote,
            str(lote.cantidad),
            str(lote.fecha_produccion),
            str(lote.fecha_vencimiento),
            str(lote.produccion),
            str(lote.exportacion),
        ])

    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#603C1C')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('GRID',       (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_lotes.pdf"'
    response.write(pdf)
    return response


# ========================
# BITÁCORA DE PRODUCCIÓN
# ========================

from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Bitacora, Produccion, Usuario


# ─────────────────────────────────────────────
#  SUPERVISOR — Crear nueva bitácora
# ─────────────────────────────────────────────
@login_required(login_url='login')
def bitacora_supervisor(request):

    # Validar sesión y rol
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    supervisor = Usuario.objects.filter(id=usuario_id, rol='Supervisor').first()
    if not supervisor:
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('login')

    if request.method == 'POST':

        titulo              = request.POST.get('titulo', '').strip()
        descripcion         = request.POST.get('descripcion', '').strip()
        tipo_reporte        = request.POST.get('tipo_reporte', '').strip()
        produccion_id       = request.POST.get('produccion', '').strip()
        unidades_producidas = request.POST.get('unidades_producidas', '').strip()
        unidades_pendientes = request.POST.get('unidades_pendientes', '').strip()
        observaciones       = request.POST.get('observaciones', '').strip()
        estado              = request.POST.get('estado', 'Borrador')

        # --- Validaciones ---
        if not titulo or len(titulo) < 5:
            messages.error(request, "El título debe tener mínimo 5 caracteres.")
            return redirect('bitacora_supervisor')

        if not descripcion or len(descripcion) < 20:
            messages.error(request, "La descripción debe tener mínimo 20 caracteres.")
            return redirect('bitacora_supervisor')

        if not tipo_reporte:
            messages.error(request, "Seleccione un tipo de reporte.")
            return redirect('bitacora_supervisor')

        if not produccion_id:
            messages.error(request, "Seleccione una producción.")
            return redirect('bitacora_supervisor')

        if not unidades_producidas:
            messages.error(request, "Debe ingresar las unidades producidas.")
            return redirect('bitacora_supervisor')

        if not unidades_pendientes:
            messages.error(request, "Debe ingresar las unidades pendientes.")
            return redirect('bitacora_supervisor')

        produccion = Produccion.objects.filter(id=produccion_id).first()
        if not produccion:
            messages.error(request, "La producción seleccionada no existe.")
            return redirect('bitacora_supervisor')

        Bitacora.objects.create(
            titulo              = titulo,
            descripcion         = descripcion,
            tipo_reporte        = tipo_reporte,
            unidades_producidas = unidades_producidas,
            unidades_pendientes = unidades_pendientes,
            observaciones       = observaciones,
            supervisor          = supervisor,
            produccion          = produccion,
            estado              = estado,
        )

        messages.success(request, "Bitácora registrada correctamente.")
        return redirect('listar_bitacoras_supervisor')

    producciones = Produccion.objects.all()

    return render(request, 'modulos/bitacora/bitacora_supervisor.html', {
        'producciones': producciones,
        'today':        date.today(),
        'supervisor':   supervisor,
    })


# ─────────────────────────────────────────────
#  SUPERVISOR — Listar sus propias bitácoras
# ─────────────────────────────────────────────
@login_required(login_url='login')
def listar_bitacoras_supervisor(request):

    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    supervisor = Usuario.objects.filter(id=usuario_id, rol='Supervisor').first()
    if not supervisor:
        return redirect('login')

    # El supervisor solo ve sus propias bitácoras
    bitacoras = Bitacora.objects.select_related(
        'produccion', 'revisado_por'
    ).filter(supervisor=supervisor).order_by('-fecha_registro')

    return render(request, 'modulos/bitacora/listar_bitacoras_supervisor.html', {
        'bitacoras':  bitacoras,
        'fecha_hoy':  date.today(),
        'supervisor': supervisor,
    })


# ─────────────────────────────────────────────
#  ADMIN — Listar todas las bitácoras
# ─────────────────────────────────────────────
@login_required(login_url='login')
def listar_bitacoras(request):

    bitacoras = Bitacora.objects.select_related(
        'supervisor', 'produccion', 'revisado_por'
    ).order_by('-fecha_registro')

    # Contar pendientes para mostrar badge de notificación
    pendientes = bitacoras.filter(estado='Enviado').count()

    return render(request, 'modulos/bitacora/listar_bitacoras.html', {
        'bitacoras':  bitacoras,
        'pendientes': pendientes,
        'fecha_hoy':  date.today(),
    })


# ─────────────────────────────────────────────
#  ADMIN — Revisar bitácora (aprobar / rechazar)
# ─────────────────────────────────────────────
@login_required(login_url='login')
def revisar_bitacora(request, id):

    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')

        bitacora = get_object_or_404(Bitacora, id=id)
        admin    = get_object_or_404(Usuario, id=usuario_id)

        nuevo_estado      = request.POST.get('estado', '').strip()
        observacion_admin = request.POST.get('observacion_admin', '').strip()
        estados_validos   = ['Aprobado', 'Rechazado']

        if nuevo_estado not in estados_validos:
            messages.error(request, "Estado de revisión no válido.")
            return redirect('listar_bitacoras')

        # Solo se pueden revisar bitácoras que estén en estado 'Enviado'
        if bitacora.estado != 'Enviado':
            messages.error(request, "Esta bitácora ya fue revisada.")
            return redirect('listar_bitacoras')

        bitacora.estado            = nuevo_estado
        bitacora.revisado_por      = admin
        bitacora.fecha_revision    = date.today()
        bitacora.observacion_admin = observacion_admin
        bitacora.save()

        accion = "aprobada" if nuevo_estado == "Aprobado" else "rechazada"
        messages.success(request, f"Bitácora '{bitacora.titulo}' {accion} correctamente.")

    return redirect('listar_bitacoras')
# ========================
# ASISTENTE IA CON GEMINI
# ========================

@login_required(login_url='login')
def consultar_ia(request):

    if request.method == 'POST':

        pregunta = request.POST.get('pregunta', '').strip()

        if not pregunta:
            return JsonResponse({'error': 'La pregunta no puede estar vacía.'}, status=400)

        if len(pregunta) < 5:
            return JsonResponse({'error': 'La pregunta es demasiado corta.'}, status=400)

        empleados_activos        = Empleado.objects.filter(estado='Activo').count()
        empleados_suspendidos    = Empleado.objects.filter(estado='Suspendido').count()
        producciones_proceso     = Produccion.objects.filter(estado='En Proceso').count()
        producciones_finalizadas = Produccion.objects.filter(estado='Finalizado').count()
        exportaciones_pendientes = Exportacion.objects.filter(estado='Pendiente').count()
        total_lotes              = Lote.objects.count()
        total_asignaciones       = Asignacion.objects.count()
        bitacoras_pendientes     = Bitacora.objects.filter(estado='Enviado').count()

        contexto = f"""
Eres un asistente experto en gestión de producción de chocolate llamado ChocoBot.
Respondes en español, de forma clara, profesional y con recomendaciones prácticas.

Datos actuales de la empresa ChocoFlow:
- Empleados activos: {empleados_activos}
- Empleados suspendidos: {empleados_suspendidos}
- Producciones en proceso: {producciones_proceso}
- Producciones finalizadas: {producciones_finalizadas}
- Exportaciones pendientes: {exportaciones_pendientes}
- Total de lotes: {total_lotes}
- Total de asignaciones: {total_asignaciones}
- Bitácoras pendientes de revisión: {bitacoras_pendientes}

Con base en estos datos reales, responde la siguiente pregunta:
{pregunta}
        """

        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return JsonResponse({'error': 'API key de Gemini no configurada.'}, status=500)

            cliente   = genai.Client(api_key=api_key)
            respuesta = cliente.models.generate_content(
                model    = "gemini-2.0-flash",
                contents = contexto
            )
            return JsonResponse({'respuesta': respuesta.text})

        except Exception as e:
            return JsonResponse({'error': f'Error al consultar la IA: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Método no permitido.'}, status=405)