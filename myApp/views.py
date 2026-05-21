from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Prefetch
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
    except:
        return {}

# ========================
# INDEX
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

        User.objects.create_user(
            username=identificacion,
            first_name=nombre,
            email=correo,
            password=password
        )
        Usuario.objects.create(
            nombre=nombre,
            email=correo,
            direccion='Sin dirección',
            contrasena=password,
            rol=rol,
            estado=estado
        )
        messages.success(request, "Usuario registrado correctamente.")
        return redirect('login')

    return render(request, 'auth/registro.html')

# =======================
# DASHBOARD ADMINISTRADOR
# =======================

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
        'usuario_nombre':          usuario_nombre,
        'usuario_rol':             usuario_rol,
        'total_usuarios':          total_usuarios,
        'total_empleados':         total_empleados,
        'empleados_activos':       empleados_activos,
        'empleados_suspendidos':   empleados_suspendidos,
        'total_producciones':      total_producciones,
        'producciones_proceso':    producciones_proceso,
        'producciones_finalizadas':producciones_finalizadas,
        'total_exportaciones':     total_exportaciones,
        'exportaciones_pendientes':exportaciones_pendientes,
        'total_lotes':             total_lotes,
        'bitacoras_pendientes':    bitacoras_pendientes,
        'solicitudes_pendientes':  solicitudes_pendientes,
        'asignaciones':            asignaciones,
        'producciones_recientes':  producciones_recientes,
    }

    return render(request, 'dashboard.html', context)

# =======================
# DASHBOARD SUPERVISOR
# =======================

def dashboard_supervisor(request):

    usuario_id     = request.session.get('usuario_id')
    usuario_nombre = 'Supervisor'
    usuario_rol    = 'Supervisor'

    try:
        usuario_db     = Usuario.objects.get(id=usuario_id)
        usuario_nombre = usuario_db.nombre
        usuario_rol    = usuario_db.rol
    except Usuario.DoesNotExist:
        pass

    total_empleados          = Empleado.objects.count()
    empleados_activos        = Empleado.objects.filter(estado='Activo').count()
    total_turnos             = Turno.objects.count()
    total_asignaciones       = Asignacion.objects.count()
    exportaciones_pendientes = Exportacion.objects.filter(estado='Pendiente').count()
    total_lotes              = Lote.objects.count()
    total_bitacora           = Bitacora.objects.count()
    mis_bitacoras            = Bitacora.objects.filter(
        supervisor__id=usuario_id
    ).order_by('-fecha_registro')[:5]

    context = {
        'usuario_nombre':          usuario_nombre,
        'usuario_rol':             usuario_rol,
        'total_empleados':         total_empleados,
        'empleados_activos':       empleados_activos,
        'total_turnos':            total_turnos,
        'total_asignaciones':      total_asignaciones,
        'exportaciones_pendientes':exportaciones_pendientes,
        'total_lotes':             total_lotes,
        'total_bitacora':          total_bitacora,
        'mis_bitacoras':           mis_bitacoras,
    }

    return render(request, 'dashboardsuper.html', context)

# ===================
# EMPLEADOS
# ===================

def empleados(request):

    query  = request.GET.get('q') or request.GET.get('busqueda')
    estado = request.GET.get('estado')
    lista  = Empleado.objects.all()

    if query:
        lista = lista.filter(
            Q(nombre__icontains=query) |
            Q(email__icontains=query)  |
            Q(cedula__icontains=query)
        )
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)

    return render(request, 'modulos/empleados/empleados.html', {
        'empleados': lista
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

        empleado.cedula     = request.POST.get('cedula')
        empleado.nombre     = request.POST.get('nombre')
        empleado.email      = request.POST.get('email')
        empleado.telefono   = request.POST.get('telefono')
        empleado.direccion  = request.POST.get('direccion')
        empleado.estado     = request.POST.get('estado')
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
    busqueda = request.GET.get('busqueda')
    estado   = request.GET.get('estado')

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
        datos.append([emp.cedula, emp.nombre, emp.email, emp.telefono, emp.estado])

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

def turnos(request):
    horario_filtro = request.GET.get('horario')
    semana_filtro  = request.GET.get('semana')                    # ← nuevo
    semana_actual  = date.today().isocalendar()[1]

    lista = RotacionTurno.objects.select_related('empleado', 'turno').all()  # ← sin filtro fijo

    if horario_filtro:
        lista = lista.filter(turno__horario=horario_filtro)
    if semana_filtro:                                              # ← nuevo
        lista = lista.filter(semana=semana_filtro)

    return render(request, 'modulos/turnos/turnos.html', {
        'rotaciones':    lista,
        'semana_actual': semana_actual,
        'turnos':        Turno.objects.filter(activo=True),
        'empleados':     Empleado.objects.filter(estado='Activo'),
    })


@login_required(login_url='login')
def guardar_rotacion(request):
    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')

        rotacion_id    = request.POST.get('id')
        empleado_id    = request.POST.get('empleado_id')
        turno_id       = request.POST.get('turno_id')
        fecha_inicio   = request.POST.get('fecha_inicio')
        fecha_fin      = request.POST.get('fecha_fin')
        semana         = request.POST.get('semana')
        sabado         = request.POST.get('sabado_asignado') == 'on'
        estado         = request.POST.get('estado', 'Pendiente')

        if not all([empleado_id, turno_id, fecha_inicio, fecha_fin, semana]):
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('turnos')

        try:
            if rotacion_id:
                rot = get_object_or_404(RotacionTurno, id=rotacion_id)
                rot.empleado        = get_object_or_404(Empleado, id=empleado_id)
                rot.turno           = get_object_or_404(Turno, id=turno_id)
                rot.fecha_inicio    = fecha_inicio
                rot.fecha_fin       = fecha_fin
                rot.semana          = semana
                rot.sabado_asignado = sabado
                rot.estado          = estado
                rot.save()
                messages.success(request, "Rotación actualizada correctamente.")
            else:
                RotacionTurno.objects.create(
                    empleado        = get_object_or_404(Empleado, id=empleado_id),
                    turno           = get_object_or_404(Turno, id=turno_id),
                    fecha_inicio    = fecha_inicio,
                    fecha_fin       = fecha_fin,
                    semana          = int(semana),
                    sabado_asignado = sabado,
                    estado          = estado,
                )
                messages.success(request, "Rotación registrada correctamente.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return redirect('turnos')


@login_required(login_url='login')
def eliminar_rotacion(request, id):
    rot = get_object_or_404(RotacionTurno, id=id)
    rot.delete()
    messages.success(request, "Rotación eliminada correctamente.")
    return redirect('turnos')

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

# ===================
# ROTACION TURNOS
# ===================

def rotacion_turnos(request):

    semana_filtro = request.GET.get('semana')
    lista = RotacionTurno.objects.select_related('empleado', 'turno').all()

    if semana_filtro:
        lista = lista.filter(semana=semana_filtro)

    return render(request, 'modulos/turnos/rotacion.html', {
        'rotaciones': lista,
    })


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

def solicitudes(request):

    query  = request.GET.get('q')
    estado = request.GET.get('estado')
    lista  = Solicitud.objects.select_related(
        'empleado', 'turno_actual', 'turno_solicitado', 'revisado_por'
    ).all()

    if query:
        lista = lista.filter(empleado__nombre__icontains=query)
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)

    turnos    = Turno.objects.filter(activo=True)
    empleados = Empleado.objects.filter(estado='Activo')

    return render(request, 'modulos/solicitudes/solicitudes.html', {
        'solicitudes': lista,
        'turnos':      turnos,
        'empleados':   empleados,
    })


@login_required(login_url='login')
def guardar_solicitud(request):
    if request.method == 'POST':

        empleado_id      = request.POST.get('empleado_id')
        turno_actual_id  = request.POST.get('turno_actual_id')
        turno_sol_id     = request.POST.get('turno_solicitado_id')
        motivo           = request.POST.get('motivo', '').strip()

        if not empleado_id or not turno_actual_id or not turno_sol_id or not motivo:
            messages.error(request, "Todos los campos son obligatorios.")
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
        usuario    = get_object_or_404(Usuario, id=usuario_id)

        solicitud             = get_object_or_404(Solicitud, id=id)
        solicitud.estado      = request.POST.get('estado')
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

def asignaciones(request):

    query  = request.GET.get('q')
    estado = request.GET.get('estado')
    lista  = Asignacion.objects.select_related(
        'empleado', 'turno', 'asignado_por'
    ).all()

    if query:
        lista = lista.filter(
            Q(tarea__icontains=query) |
            Q(empleado__nombre__icontains=query)
        )
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)

    empleados = Empleado.objects.filter(estado='Activo')
    turnos    = Turno.objects.filter(activo=True)

    return render(request, 'modulos/asignaciones/asignaciones.html', {
        'asignaciones': lista,
        'empleados':    empleados,
        'turnos':       turnos,
    })


@login_required(login_url='login')
def guardar_asignacion(request):
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

        asignacion_id = request.POST.get('id')
        asignacion    = get_object_or_404(Asignacion, id=asignacion_id) if asignacion_id else Asignacion()

        tarea    = request.POST.get('tarea', '').strip()
        fecha    = request.POST.get('fecha_asignacion', '').strip()
        emp_id   = request.POST.get('empleado_id')
        turno_id = request.POST.get('turno_id')
        estado   = request.POST.get('estado', 'Pendiente')

        if not tarea or not fecha or not emp_id or not turno_id:
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('asignaciones')

        asignacion.tarea            = tarea
        asignacion.fecha_asignacion = fecha
        asignacion.empleado         = get_object_or_404(Empleado, id=emp_id)
        asignacion.turno            = get_object_or_404(Turno, id=turno_id)
        asignacion.asignado_por     = usuario_perfil
        asignacion.estado           = estado

        try:
            asignacion.save()
            messages.success(request, "Asignación guardada correctamente.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect('asignaciones')


@login_required(login_url='login')
def inactivar_asignacion(request, id):
    asignacion        = get_object_or_404(Asignacion, id=id)
    asignacion.estado = 'Pendiente'
    asignacion.save()
    messages.success(request, "Asignación inactivada.")
    return redirect('asignaciones')


@login_required(login_url='login')
def generar_reporte_asignaciones(request):

    lista = Asignacion.objects.select_related('empleado', 'turno', 'asignado_por').all()
    query = request.GET.get('q')

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

def producciones(request):

    query  = request.GET.get('q')
    estado = request.GET.get('estado')
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

        produccion_id      = request.POST.get('id')
        produccion         = get_object_or_404(Produccion, id=produccion_id) if produccion_id else Produccion()

        producto           = request.POST.get('producto', '').strip()
        ingredientes       = request.POST.get('ingredientes', '').strip()
        cantidad_requerida = request.POST.get('cantidad_requerida', '').strip()
        fecha_entrega      = request.POST.get('fecha_entrega', '').strip()
        fecha_limite       = request.POST.get('fecha_limite', '').strip()
        estado             = request.POST.get('estado', '').strip()
        emp_id             = request.POST.get('empleado_responsable')

        if not producto or not emp_id or not fecha_entrega or not fecha_limite:
            messages.error(request, "Los campos obligatorios no pueden estar vacíos.")
            return redirect('producciones')

        produccion.producto           = producto
        produccion.ingredientes       = ingredientes
        produccion.cantidad_requerida = cantidad_requerida
        produccion.fecha_entrega      = fecha_entrega
        produccion.fecha_limite       = fecha_limite
        produccion.estado             = estado
        produccion.empleado_responsable = get_object_or_404(Empleado, id=emp_id)
        produccion.creado_por         = usuario_perfil
        produccion.save()
        messages.success(request, "Producción guardada correctamente.")

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
    query  = request.GET.get('q')
    estado = request.GET.get('estado')

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

    datos = [['Producto', 'Ingredientes', 'Cant. Requerida', 'Responsable', 'Fecha Entrega', 'Estado']]
    for p in lista:
        datos.append([
            p.producto,
            p.ingredientes,
            p.cantidad_requerida,
            p.empleado_responsable.nombre,
            str(p.fecha_entrega),
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

# ===================
# EXPORTACIONES
# ===================

def gestionar_exportaciones(request):

    q      = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    exportaciones = Exportacion.objects.all()

    if q:
        exportaciones = exportaciones.filter(destino__icontains=q)
    if estado:
        exportaciones = exportaciones.filter(estado=estado)

    producciones = Produccion.objects.filter(estado='En Proceso')

    return render(request, 'modulos/exportaciones/exportaciones.html', {
        'exportaciones': exportaciones,
        'producciones':  producciones,
        'q':             q,
        'estado_filtro': estado,
    })


@login_required(login_url='login')
def guardar_exportacion(request):
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

        exp_id        = request.POST.get('id')
        destino       = request.POST.get('destino')
        pais          = request.POST.get('pais', 'Colombia')
        producto      = request.POST.get('producto', '')
        fecha_envio   = request.POST.get('fecha_envio')
        fecha_entrega = request.POST.get('fecha_entrega')
        estado        = request.POST.get('estado')
        produccion_id = request.POST.get('produccion_id')

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
    busqueda      = request.GET.get('busqueda')
    estado        = request.GET.get('estado')

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
def guardar_lote(request):
    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')

        lote_id           = request.POST.get('id')
        codigo_lote       = request.POST.get('codigo_lote')
        cantidad          = request.POST.get('cantidad')
        fecha_produccion  = request.POST.get('fecha_produccion')
        fecha_vencimiento = request.POST.get('fecha_vencimiento')
        produccion_id     = request.POST.get('produccion_id')
        exportacion_id    = request.POST.get('exportacion_id')

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

# ===================
# BITACORA
# ===================

def bitacoras(request):

    query  = request.GET.get('q')
    estado = request.GET.get('estado')
    lista  = Bitacora.objects.select_related('supervisor', 'produccion', 'revisado_por').all()

    if query:
        lista = lista.filter(titulo__icontains=query)
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)

    producciones = Produccion.objects.all()

    return render(request, 'modulos/bitacora/bitacora.html', {
        'bitacoras':   lista,
        'producciones': producciones,
    })


@login_required(login_url='login')
def guardar_bitacora(request):
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

        bitacora_id         = request.POST.get('id')
        bitacora            = get_object_or_404(Bitacora, id=bitacora_id) if bitacora_id else Bitacora()

        titulo              = request.POST.get('titulo', '').strip()
        descripcion         = request.POST.get('descripcion', '').strip()
        tipo_reporte        = request.POST.get('tipo_reporte', '')
        observaciones       = request.POST.get('observaciones', '')
        unidades_producidas = request.POST.get('unidades_producidas', '')
        unidades_pendientes = request.POST.get('unidades_pendientes', '')
        estado              = request.POST.get('estado', 'Borrador')
        produccion_id       = request.POST.get('produccion_id')

        if not titulo or not descripcion or not tipo_reporte:
            messages.error(request, "Título, descripción y tipo son obligatorios.")
            return redirect('bitacoras')

        bitacora.titulo              = titulo
        bitacora.descripcion         = descripcion
        bitacora.tipo_reporte        = tipo_reporte
        bitacora.observaciones       = observaciones
        bitacora.unidades_producidas = unidades_producidas
        bitacora.unidades_pendientes = unidades_pendientes
        bitacora.estado              = estado
        bitacora.supervisor          = usuario_perfil
        bitacora.produccion          = Produccion.objects.filter(id=produccion_id).first() if produccion_id else None
        bitacora.save()
        messages.success(request, "Bitácora guardada correctamente.")

    return redirect('bitacoras')


@login_required(login_url='login')
def revisar_bitacora(request, id):
    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        usuario    = get_object_or_404(Usuario, id=usuario_id)

        bitacora                   = get_object_or_404(Bitacora, id=id)
        bitacora.estado            = request.POST.get('estado')
        bitacora.observacion_admin = request.POST.get('observacion_admin', '')
        bitacora.revisado_por      = usuario
        bitacora.fecha_revision    = timezone.now().date()
        bitacora.save()

        messages.success(request, f"Bitácora '{bitacora.titulo}' revisada correctamente.")

    return redirect('bitacoras')


@login_required(login_url='login')
def generar_reporte_bitacoras(request):

    lista  = Bitacora.objects.select_related('supervisor', 'produccion').all()
    estado = request.GET.get('estado')

    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)

    buffer    = BytesIO()
    doc       = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos   = getSampleStyleSheet()

    elementos.append(Paragraph("Reporte de Bitácoras - ChocoFlow", estilos['Title']))
    elementos.append(Spacer(1, 20))

    datos = [['Título', 'Tipo', 'Supervisor', 'Fecha', 'Estado', 'Unid. Producidas', 'Unid. Pendientes']]
    for b in lista:
        datos.append([
            b.titulo,
            b.tipo_reporte,
            b.supervisor.nombre,
            str(b.fecha_registro),
            b.estado,
            b.unidades_producidas or '0',
            b.unidades_pendientes or '0',
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
    response['Content-Disposition'] = 'attachment; filename="reporte_bitacoras.pdf"'
    response.write(pdf)
    return response

# ========================
# ASISTENTE IA CON GEMINI
# ========================

def consultar_ia(request):

    if not request.user.is_authenticated:
        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            return JsonResponse({'error': 'No autorizado.'}, status=401)

    if request.method == 'POST':

        pregunta = request.POST.get('pregunta', '').strip()

        if not pregunta:
            return JsonResponse({'error': 'La pregunta no puede estar vacía.'}, status=400)

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
            cliente   = genai.Client(api_key=os.getenv("AIzaSyAwbw7Vc_rZ7MAma33SG4GL4XbmJRQF778"))
            respuesta = cliente.models.generate_content(
                model    = "gemini-2.0-flash",
                contents = contexto
            )
            return JsonResponse({'respuesta': respuesta.text})

        except Exception as e:
            return JsonResponse({'error': f'Error al consultar la IA: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Método no permitido.'}, status=405)