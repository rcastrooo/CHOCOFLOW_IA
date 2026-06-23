from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import date, datetime, timedelta, time
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import resend # carga de correos
from io import BytesIO
from dotenv import load_dotenv
load_dotenv()
from google import genai
import os
import time
import json
import re
import pandas as pd 
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import IsolationForest
import numpy as np
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors

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
    HistorialCorreo,
)

# ========================
# FUNCIÓN AUXILIAR — parsear body JSON
# ========================

def parse_body(request):
    try:
        return json.loads(request.body)
    except Exception:
        return {}


# ========================
# FUNCIONES AUXILIARES — turno supervisor
# ========================

def get_turno_supervisor(usuario_id):
    """
    Retorna el string del horario del turno asignado al supervisor
    (campo Usuario.turno), o None si no tiene turno asignado.
    Ejemplo de retorno: 'Mañana 6:00am - 12:00pm'
    """
    supervisor = Usuario.objects.filter(id=usuario_id, rol='Supervisor').first()
    if not supervisor or not supervisor.turno:
        return None
    return supervisor.turno


def get_empleados_de_turno_supervisor(turno_horario):
    """
    Retorna un QuerySet de IDs de empleados que tienen RotacionTurno
    en la semana ISO actual con el turno que coincide con turno_horario.
    Al rotar la semana, automáticamente refleja los nuevos empleados del turno.
    """
    semana_actual = date.today().isocalendar()[1]
    return RotacionTurno.objects.filter(
        semana=semana_actual,
        turno__horario=turno_horario,
    ).values_list('empleado_id', flat=True)


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

                horario_fijo = request.session.get('horario_fijo', '')

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
        telefono       = request.POST.get('telefono', '').strip()
        direccion      = request.POST.get('direccion', '').strip()
        password       = request.POST.get('password', '').strip()
        rol            = request.POST.get('rol', '').strip()
        estado         = request.POST.get('estado', 'Activo').strip()
        turno          = request.POST.get('turno', '').strip()

        # ── Validaciones ──────────────────────────────────────────
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

        # ── Validación turno (obligatorio si es Supervisor) ───────
        turnos_validos = ['Mañana 6:00am - 2:00pm', 'Tarde 2:00pm - 10:00pm']
        if rol == 'Supervisor':
            if not turno:
                messages.error(request, "Debes seleccionar un turno para el supervisor.")
                return redirect('registro')
            if turno not in turnos_validos:
                messages.error(request, "Turno no válido.")
                return redirect('registro')

        # ── Crear usuario Django ──────────────────────────────────
        User.objects.create_user(
            username   = identificacion,
            first_name = nombre,
            email      = correo,
            password   = password
        )

        # ── Crear perfil Usuario ──────────────────────────────────
        Usuario.objects.create(
            nombre     = nombre,
            email      = correo,
            telefono   = telefono or None,
            direccion  = direccion if direccion else 'Sin dirección',
            contrasena = password,
            rol        = rol,
            estado     = estado,
            turno      = turno if rol == 'Supervisor' else None,
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


# ======================================================
# HELPERS DE TURNO SUPERVISOR
# ======================================================

def get_turno_supervisor(usuario_id):
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        return usuario.turno  # ej: 'Mañana 6:00am - 2:00pm'
    except Usuario.DoesNotExist:
        return None


def get_empleados_de_turno_supervisor(turno_horario):
    from datetime import timedelta
    hoy     = timezone.now().date()
    lunes   = hoy - timedelta(days=hoy.weekday())
    domingo = lunes + timedelta(days=6)

    try:
        turno_obj = Turno.objects.get(horario=turno_horario)
    except Turno.DoesNotExist:
        return []

    ids = RotacionTurno.objects.filter(
        turno=turno_obj,
        fecha_inicio__lte=domingo,
        fecha_fin__gte=lunes,
    ).values_list('empleado_id', flat=True)

    return list(ids)


# ======================================================
# GESTIÓN DE SUPERVISORES
# ======================================================

@login_required(login_url='login')
def gestionar_supervisores(request):
    qs = Usuario.objects.filter(rol='Supervisor')

    q      = request.GET.get('q', '').strip()
    turno  = request.GET.get('turno', '').strip()
    estado = request.GET.get('estado', '').strip()

    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(email__icontains=q))

    if turno == 'Sin asignar':
        qs = qs.filter(Q(turno__isnull=True) | Q(turno=''))
    elif turno:
        qs = qs.filter(turno=turno)

    if estado:
        qs = qs.filter(estado=estado)

    return render(request, 'modulos/supervisores/gestionar_supervisores.html', {
        'supervisores': qs,
    })


@login_required(login_url='login')
def asignar_turno_supervisor(request, supervisor_id):
    if request.method != 'POST':
        return redirect('gestionar_supervisores')

    supervisor = get_object_or_404(Usuario, id=supervisor_id, rol='Supervisor')
    turno      = request.POST.get('turno', '').strip()

    TURNOS_VALIDOS = ('Mañana 6:00am - 2:00pm', 'Tarde 2:00pm - 10:00pm')
    if turno not in TURNOS_VALIDOS:
        messages.error(request, 'Turno no válido.')
        return redirect('gestionar_supervisores')

    supervisor.turno = turno if turno else None
    supervisor.save()

    etiqueta = turno if turno else 'Sin asignar'
    messages.success(
        request,
        f'Turno actualizado a "{etiqueta}" para {supervisor.nombre}.'
    )
    return redirect('gestionar_supervisores')


@login_required(login_url='login')
def editar_supervisor(request):
    if request.method != 'POST':
        return redirect('gestionar_supervisores')

    sup_id     = request.POST.get('id', '').strip()
    supervisor = get_object_or_404(Usuario, id=sup_id, rol='Supervisor')

    nombre    = request.POST.get('nombre', '').strip()
    email     = request.POST.get('email', '').strip()
    telefono  = request.POST.get('telefono', '').strip()
    direccion = request.POST.get('direccion', '').strip()
    estado    = request.POST.get('estado', '').strip()
    turno     = request.POST.get('turno', '').strip()

    if not nombre or not email or not estado:
        messages.error(request, 'Nombre, email y estado son obligatorios.')
        return redirect('gestionar_supervisores')

    patron_correo = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
    if not re.match(patron_correo, email):
        messages.error(request, 'El correo no tiene un formato válido.')
        return redirect('gestionar_supervisores')

    if telefono and not re.fullmatch(r'\d{10}', telefono):
        messages.error(request, 'El teléfono debe contener solo números (10 dígitos).')
        return redirect('gestionar_supervisores')

    if Usuario.objects.filter(email=email).exclude(id=sup_id).exists():
        messages.error(request, 'Ya existe otro usuario con ese correo electrónico.')
        return redirect('gestionar_supervisores')

    estados_validos = ['Activo', 'Inactivo', 'Suspendido', 'Incapacitado']
    if estado not in estados_validos:
        messages.error(request, 'Estado no válido.')
        return redirect('gestionar_supervisores')

    turnos_validos = ('Mañana 6:00am - 2:00pm', 'Tarde 2:00pm - 10:00pm')
    if turno and turno not in turnos_validos:
        messages.error(request, 'Turno no válido.')
        return redirect('gestionar_supervisores')

    supervisor.nombre    = nombre
    supervisor.email     = email
    supervisor.telefono  = telefono or None
    supervisor.direccion = direccion or 'Sin dirección'
    supervisor.estado    = estado
    supervisor.turno     = turno or None
    supervisor.save()

    messages.success(request, f'Supervisor "{nombre}" actualizado correctamente.')
    return redirect('gestionar_supervisores')


@login_required(login_url='login')
def inactivar_supervisor(request, supervisor_id):
    supervisor        = get_object_or_404(Usuario, id=supervisor_id, rol='Supervisor')
    supervisor.estado = 'Inactivo'
    supervisor.save()
    messages.warning(
        request,
        f'Supervisor "{supervisor.nombre}" marcado como Inactivo.'
    )
    return redirect('gestionar_supervisores')


@login_required(login_url='login')
def carga_masiva_supervisores(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        return JsonResponse({'error': 'No se recibió ningún archivo.'}, status=400)

    if not csv_file.name.endswith('.csv'):
        return JsonResponse({'error': 'El archivo debe ser .csv'}, status=400)

    try:
        contenido = csv_file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            csv_file.seek(0)
            contenido = csv_file.read().decode('latin-1')
        except Exception:
            return JsonResponse(
                {'error': 'No se pudo leer el archivo. Usa codificación UTF-8.'},
                status=400
            )

    import csv as csv_module
    reader  = csv_module.DictReader(
        BytesIO(contenido.encode()).read().decode().__class__(contenido).splitlines()
    )
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]

    REQUERIDOS = ['nombre', 'email', 'contrasena', 'estado']
    faltantes  = [r for r in REQUERIDOS if r not in headers]
    if faltantes:
        return JsonResponse(
            {'error': f'Faltan columnas requeridas: {", ".join(faltantes)}'},
            status=400
        )

    ESTADOS_VALIDOS = {'Activo', 'Inactivo', 'Suspendido', 'Incapacitado'}
    TURNOS_VALIDOS  = {'Mañana 6:00am - 2:00pm', 'Tarde 2:00pm - 10:00pm'}
    patron_correo   = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'

    creados  = 0
    omitidos = 0
    errores  = []

    for num_fila, row in enumerate(reader, start=2):

        fila_info = f'Fila {num_fila}'
        row       = {k.strip().lower(): v.strip() for k, v in row.items() if k}

        nombre     = row.get('nombre', '')
        email      = row.get('email', '')
        telefono   = row.get('telefono', '')
        direccion  = row.get('direccion', 'Sin dirección')
        contrasena = row.get('contrasena', '')
        estado     = row.get('estado', 'Activo')
        turno      = row.get('turno', '')

        if not nombre:
            errores.append({'fila': fila_info, 'motivo': 'Nombre vacío'}); continue
        if not email:
            errores.append({'fila': fila_info, 'motivo': 'Email vacío'}); continue
        if not re.match(patron_correo, email):
            errores.append({'fila': fila_info, 'motivo': f'Email inválido: "{email}"'}); continue
        if not contrasena:
            errores.append({'fila': fila_info, 'motivo': 'Contraseña vacía'}); continue
        if estado not in ESTADOS_VALIDOS:
            errores.append({'fila': fila_info, 'motivo': f'Estado inválido: "{estado}"'}); continue
        if turno and turno not in TURNOS_VALIDOS:
            errores.append({'fila': fila_info, 'motivo': f'Turno inválido: "{turno}"'}); continue

        if Usuario.objects.filter(email=email).exists():
            omitidos += 1
            continue

        # Crear usuario Django para el login
        if not User.objects.filter(email=email).exists():
            User.objects.create_user(
                username   = email,
                email      = email,
                password   = contrasena,
                first_name = nombre,
            )

        Usuario.objects.create(
            nombre     = nombre,
            email      = email,
            telefono   = telefono or None,
            direccion  = direccion,
            contrasena = contrasena,
            rol        = 'Supervisor',
            estado     = estado,
            turno      = turno or None,
        )
        creados += 1

    return JsonResponse({
        'creados':  creados,
        'omitidos': omitidos,
        'errores':  errores,
    })


@login_required(login_url='login')
def reporte_supervisores(request):
 
    supervisores = Usuario.objects.filter(rol='Supervisor').order_by('nombre')
 
    total_supervisores = supervisores.count()
    activos = supervisores.filter(estado='Activo').count()
    inactivos = supervisores.filter(estado='Inactivo').count()
 
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25
    )
 
    elementos = []
    estilos = getSampleStyleSheet()
 
    titulo_style = ParagraphStyle('Titulo', parent=estilos['Title'], fontName='Helvetica-Bold',
                                   fontSize=22, alignment=1, textColor=colors.HexColor('#3E2723'), spaceAfter=10)
    subtitulo_style = ParagraphStyle('Subtitulo', parent=estilos['Normal'], fontSize=10,
                                      alignment=1, textColor=colors.HexColor('#7A6A5D'))
    resumen_style = ParagraphStyle('Resumen', parent=estilos['Normal'], fontName='Helvetica-Bold',
                                    fontSize=13, alignment=1, textColor=colors.white)
    pie_style = ParagraphStyle('Pie', parent=estilos['Normal'], fontSize=8,
                                alignment=1, textColor=colors.HexColor('#8D6E63'))
 
    elementos.append(Paragraph("REPORTE DE SUPERVISORES", titulo_style))
    elementos.append(Paragraph("Sistema de Gestión ChocoFlow", subtitulo_style))
    elementos.append(Spacer(1, 15))
 
    resumen = Table([[
        Paragraph(f"<b>Total Supervisores</b><br/>{total_supervisores}", resumen_style),
        Paragraph(f"<b>Activos</b><br/>{activos}", resumen_style),
        Paragraph(f"<b>Inactivos</b><br/>{inactivos}", resumen_style),
    ]], colWidths=[250, 250, 250])
 
    resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#5D4037')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#6D4C41')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#8D6E63')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    elementos.append(resumen)
    elementos.append(Spacer(1, 20))
 
    datos = [['Nombre', 'Email', 'Teléfono', 'Dirección', 'Turno', 'Estado']]
    for s in supervisores:
        datos.append([
            s.nombre, s.email, s.telefono or '—',
            s.direccion or '—', s.turno or 'Sin asignar', s.estado,
        ])
 
    tabla = Table(datos, colWidths=[120, 190, 100, 160, 140, 42])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4E342E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#333333')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.6, colors.HexColor('#D7CCC8')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FAF7F2'), colors.HexColor('#F2ECE5')]),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("Documento generado automáticamente por ChocoFlow", pie_style))
 
    doc.build(elementos)
    pdf = buffer.getvalue()
    buffer.close()
 
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_supervisores.pdf"'
    response.write(pdf)
    return response

# =======================
# DASHBOARD SUPERVISOR
# =======================

@login_required(login_url='login')
def dashboard_supervisor(request):

    usuario_id    = request.session.get('usuario_id')
    turno_horario = get_turno_supervisor(usuario_id)

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
        'mi_turno':                 turno_horario or '',
    }

    return render(request, 'dashboard_supervisor.html', context)


# ========================
# API STATS SUPERVISOR
# ========================

@login_required(login_url='login')
def api_stats_supervisor(request):

    hoy           = timezone.now().date()
    usuario_id    = request.session.get('usuario_id')
    turno_horario = get_turno_supervisor(usuario_id)

    if turno_horario:
        ids_empleados = get_empleados_de_turno_supervisor(turno_horario)
    else:
        ids_empleados = []

    empleados_de_mi_turno = Empleado.objects.filter(id__in=ids_empleados)

    sin_turno = Empleado.objects.filter(
        estado='Activo'
    ).exclude(
        id__in=RotacionTurno.objects.values_list('empleado_id', flat=True)
    ).count()

    turno = Turno.objects.filter(horario=turno_horario).first() if turno_horario else None

    data = {
        'total_empleados':          empleados_de_mi_turno.count(),
        'empleados_activos':        empleados_de_mi_turno.filter(estado='Activo').count(),
        'asignaciones_hoy':         Asignacion.objects.filter(
                                        fecha_asignacion=hoy,
                                        empleado_id__in=ids_empleados
                                    ).count(),
        'sin_turno':                sin_turno,
        'lotes_totales':            Lote.objects.filter(
                                        produccion__empleado_responsable_id__in=ids_empleados
                                    ).count(),
        'exportaciones_pendientes': Exportacion.objects.filter(
                                        estado='Pendiente',
                                        produccion__empleado_responsable_id__in=ids_empleados
                                    ).count(),
        'exportaciones_enviadas':   Exportacion.objects.filter(
                                        estado='Enviado',
                                        produccion__empleado_responsable_id__in=ids_empleados
                                    ).count(),
        'bitacora_hoy':             Bitacora.objects.filter(
                                        fecha_registro=hoy,
                                        supervisor_id=usuario_id
                                    ).count(),
        'bitacora_pendientes':      Bitacora.objects.filter(
                                        fecha_registro=hoy,
                                        estado='Borrador',
                                        supervisor_id=usuario_id
                                    ).count(),
        'bitacora_enviados':        Bitacora.objects.filter(
                                        fecha_registro=hoy,
                                        estado='Enviado',
                                        supervisor_id=usuario_id
                                    ).count(),
        'turno_nombre':             turno.horario if turno else 'Sin turno asignado',
    }

    return JsonResponse(data)

# ========================
# API STATS SUPERVISOR
# ========================

@login_required(login_url='login')
def api_stats_supervisor(request):

    hoy           = timezone.now().date()
    usuario_id    = request.session.get('usuario_id')
    turno_horario = get_turno_supervisor(usuario_id)

    # IDs de empleados del turno del supervisor esta semana
    if turno_horario:
        ids_empleados = get_empleados_de_turno_supervisor(turno_horario)
    else:
        ids_empleados = []

    empleados_de_mi_turno = Empleado.objects.filter(id__in=ids_empleados)

    sin_turno = Empleado.objects.filter(
        estado='Activo'
    ).exclude(
        id__in=RotacionTurno.objects.values_list('empleado_id', flat=True)
    ).count()

    turno = Turno.objects.filter(horario=turno_horario).first() if turno_horario else None

    data = {
        'total_empleados':          empleados_de_mi_turno.count(),
        'empleados_activos':        empleados_de_mi_turno.filter(estado='Activo').count(),
        'asignaciones_hoy':         Asignacion.objects.filter(
                                        fecha_asignacion=hoy,
                                        empleado_id__in=ids_empleados
                                    ).count(),
        'sin_turno':                sin_turno,
        'lotes_totales':            Lote.objects.filter(
                                        produccion__empleado_responsable_id__in=ids_empleados
                                    ).count(),
        'exportaciones_pendientes': Exportacion.objects.filter(
                                        estado='Pendiente',
                                        produccion__empleado_responsable_id__in=ids_empleados
                                    ).count(),
        'exportaciones_enviadas':   Exportacion.objects.filter(
                                        estado='Enviado',
                                        produccion__empleado_responsable_id__in=ids_empleados
                                    ).count(),
        'bitacora_hoy':             Bitacora.objects.filter(
                                        fecha_registro=hoy,
                                        supervisor_id=usuario_id
                                    ).count(),
        'bitacora_pendientes':      Bitacora.objects.filter(
                                        fecha_registro=hoy,
                                        estado='Borrador',
                                        supervisor_id=usuario_id
                                    ).count(),
        'bitacora_enviados':        Bitacora.objects.filter(
                                        fecha_registro=hoy,
                                        estado='Enviado',
                                        supervisor_id=usuario_id
                                    ).count(),
        'turno_nombre':             turno.horario if turno else 'Sin turno asignado',
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

    usuario_id    = request.session.get('usuario_id')
    turno_horario = get_turno_supervisor(usuario_id)
    query         = request.GET.get('q', '')

    if turno_horario:
        ids_empleados = get_empleados_de_turno_supervisor(turno_horario)
        lista = Empleado.objects.filter(estado='Activo', id__in=ids_empleados)
    else:
        lista = Empleado.objects.none()
        messages.warning(request, "No tienes un turno asignado esta semana.")

    if query:
        lista = lista.filter(
            Q(nombre__icontains=query) |
            Q(cedula__icontains=query)  |
            Q(email__icontains=query)
        )

    return render(request, 'modulos/empleados/empleados_supervisor.html', {
        'empleados': lista,
        'horario':   turno_horario or '',
        'fecha_hoy': date.today(),
        'busqueda':  query,
        'mi_turno':  turno_horario or '',
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

        cedula    = request.POST.get('cedula',    '').strip()
        nombre    = request.POST.get('nombre',    '').strip()
        email     = request.POST.get('email',     '').strip()
        telefono  = request.POST.get('telefono',  '').strip()
        direccion = request.POST.get('direccion', '').strip()
        estado    = request.POST.get('estado',    '').strip()

        if not cedula or not nombre or not email or not estado:
            messages.error(request, "Cédula, nombre, email y estado son obligatorios.")
            return redirect('empleados')

        if not re.fullmatch(r'\d{6,12}', cedula):
            messages.error(request, "La cédula debe contener solo números (6–12 dígitos).")
            return redirect('empleados')

        if not re.fullmatch(r"[A-Za-záéíóúÁÉÍÓÚñÑüÜ\s\-']{2,80}", nombre):
            messages.error(request, "El nombre solo puede contener letras, espacios y guiones.")
            return redirect('empleados')

        if not re.fullmatch(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', email):
            messages.error(request, "El correo electrónico no tiene un formato válido.")
            return redirect('empleados')

        if telefono and not re.fullmatch(r'\d{10}', telefono):
            messages.error(request, "El teléfono debe contener solo números (10 dígitos).")
            return redirect('empleados')

        estados_validos = ['Activo', 'Inactivo', 'Suspendido', 'Incapacitado']
        if estado not in estados_validos:
            messages.error(request, "El estado seleccionado no es válido.")
            return redirect('empleados')

        qs_email = Empleado.objects.filter(email=email)
        if empleado_id:
            qs_email = qs_email.exclude(id=empleado_id)
        if qs_email.exists():
            messages.error(request, "Ya existe un empleado con ese correo.")
            return redirect('empleados')

        qs_cedula = Empleado.objects.filter(cedula=cedula)
        if empleado_id:
            qs_cedula = qs_cedula.exclude(id=empleado_id)
        if qs_cedula.exists():
            messages.error(request, "Ya existe un empleado con esa cédula.")
            return redirect('empleados')

        empleado.cedula     = cedula
        empleado.nombre     = nombre
        empleado.email      = email
        empleado.telefono   = telefono
        empleado.direccion  = direccion if direccion else 'Sin dirección'
        empleado.estado     = estado
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
 
    lista = Empleado.objects.all()
    busqueda = request.GET.get('busqueda', '')
    estado = request.GET.get('estado', '')
 
    if busqueda:
        lista = lista.filter(nombre__icontains=busqueda)
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)
 
    total_empleados = lista.count()
    empleados_activos = lista.filter(estado='Activo').count()
    empleados_inactivos = total_empleados - empleados_activos
 
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=25, leftMargin=25, topMargin=35, bottomMargin=25
    )
 
    elementos = []
    estilos = getSampleStyleSheet()
 
    empresa_style = ParagraphStyle('Empresa', parent=estilos['Title'], fontSize=24,
                                    leading=28, alignment=1, textColor=colors.HexColor('#4E342E'))
    subtitulo_style = ParagraphStyle('Subtitulo', parent=estilos['Normal'], alignment=1,
                                      fontSize=10, textColor=colors.HexColor('#7A6A5D'))
    titulo_style = ParagraphStyle('TituloReporte', parent=estilos['Heading1'], fontSize=16,
                                   alignment=1, textColor=colors.HexColor('#5D4037'))
    tarjeta_style = ParagraphStyle('Tarjeta', parent=estilos['Normal'], alignment=1,
                                    fontSize=11, fontName='Helvetica-Bold', textColor=colors.white)
    pie_style = ParagraphStyle('Pie', parent=estilos['Normal'], alignment=1,
                                fontSize=8, textColor=colors.HexColor('#7A6A5D'))
 
    elementos.append(Paragraph("CHOCOFLOW", empresa_style))
    elementos.append(Paragraph("Sistema Inteligente de Gestión de Producción y Exportación", subtitulo_style))
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph("REPORTE DE EMPLEADOS", titulo_style))
    elementos.append(Spacer(1, 15))
 
    kpi = Table([[
        Paragraph(f"<b>Total</b><br/>{total_empleados}", tarjeta_style),
        Paragraph(f"<b>Activos</b><br/>{empleados_activos}", tarjeta_style),
        Paragraph(f"<b>Inactivos</b><br/>{empleados_inactivos}", tarjeta_style),
    ]], colWidths=[230, 230, 230])
 
    kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#6D4C41')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#4E342E')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#8D6E63')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
    ]))
    elementos.append(kpi)
    elementos.append(Spacer(1, 20))
 
    datos = [['Cédula', 'Nombre', 'Email', 'Teléfono', 'Dirección', 'Estado']]
    for emp in lista:
        datos.append([
            emp.cedula or '—', emp.nombre, emp.email,
            emp.telefono or '—', emp.direccion or '—', emp.estado,
        ])
 
    # 6 columnas → 6 anchos. Suma = 740 (cabe en landscape letter: 792 - 50 márgenes)
    tabla = Table(datos, colWidths=[90, 140, 170, 90, 150, 80], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5D4037')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D7CCC8')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FAFAFA'), colors.HexColor('#F3F3F3')]),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("Documento generado automáticamente por ChocoFlow", pie_style))
 
    doc.build(elementos)
    pdf = buffer.getvalue()
    buffer.close()
 
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_empleados.pdf"'
    response.write(pdf)
    return response

@login_required(login_url='login')
def carga_masiva_empleados(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        return JsonResponse({'error': 'No se recibió ningún archivo.'}, status=400)

    if not csv_file.name.endswith('.csv'):
        return JsonResponse({'error': 'El archivo debe ser .csv'}, status=400)

    try:
        contenido = csv_file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        csv_file.seek(0)
        contenido = csv_file.read().decode('latin-1')

    import csv as csv_module
    reader  = csv_module.DictReader(contenido.splitlines())
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]

    REQUERIDOS = ['cedula', 'nombre', 'email', 'estado']
    faltantes  = [r for r in REQUERIDOS if r not in headers]
    if faltantes:
        return JsonResponse(
            {'error': f'Faltan columnas requeridas: {", ".join(faltantes)}'},
            status=400
        )

    ESTADOS_VALIDOS = {'Activo', 'Inactivo', 'Suspendido', 'Incapacitado'}
    patron_correo   = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'

    usuario_id = request.session.get('usuario_id')
    usuario_perfil = Usuario.objects.filter(id=usuario_id).first()

    creados, omitidos, errores = 0, 0, []

    for num_fila, row in enumerate(reader, start=2):
        fila_info = f'Fila {num_fila}'
        row = {k.strip().lower(): (v or '').strip() for k, v in row.items() if k}

        cedula    = row.get('cedula', '')
        nombre    = row.get('nombre', '')
        email     = row.get('email', '')
        telefono  = row.get('telefono', '')
        direccion = row.get('direccion', 'Sin dirección')
        estado    = row.get('estado', 'Activo')

        if not re.fullmatch(r'\d{6,12}', cedula):
            errores.append({'fila': fila_info, 'motivo': f'Cédula inválida: "{cedula}"'}); continue
        if not nombre:
            errores.append({'fila': fila_info, 'motivo': 'Nombre vacío'}); continue
        if not re.match(patron_correo, email):
            errores.append({'fila': fila_info, 'motivo': f'Email inválido: "{email}"'}); continue
        if estado not in ESTADOS_VALIDOS:
            errores.append({'fila': fila_info, 'motivo': f'Estado inválido: "{estado}"'}); continue

        if Empleado.objects.filter(email=email).exists() or Empleado.objects.filter(cedula=cedula).exists():
            omitidos += 1
            continue

        Empleado.objects.create(
            cedula     = cedula,
            nombre     = nombre,
            email      = email,
            telefono   = telefono or None,
            direccion  = direccion,
            estado     = estado,
            creado_por = usuario_perfil,
        )
        creados += 1

    return JsonResponse({'creados': creados, 'omitidos': omitidos, 'errores': errores})

# ===================
# TURNOS
# ===================

@login_required(login_url='login')
def turnos(request):

    horario_filtro = request.GET.get('horario', '')
    semana_filtro  = request.GET.get('semana', '')
    hoy            = date.today()
    semana_actual  = hoy.isocalendar()[1]

    lista = RotacionTurno.objects.select_related('empleado', 'turno').all()

    if horario_filtro:
        lista = lista.filter(turno__horario=horario_filtro)
    if semana_filtro:
        lista = lista.filter(semana=semana_filtro)

    semanas = []
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    for i in range(0, 53 - semana_actual + 1):
        lunes   = lunes_actual + timedelta(weeks=i)
        domingo = lunes + timedelta(days=6)
        semanas.append({
            'numero':  lunes.isocalendar()[1],
            'lunes':   lunes.isoformat(),
            'domingo': domingo.isoformat(),
            'label':   f"Semana del {lunes.day} {lunes.strftime('%b')} · {lunes.day}-{domingo.day} {domingo.strftime('%b')}",
        })

    return render(request, 'modulos/turnos/turnos.html', {
        'rotaciones':    lista,
        'semana_actual': semana_actual,
        'turnos':        Turno.objects.filter(activo=True),
        'empleados':     Empleado.objects.filter(estado='Activo'),
        'fecha_hoy':     hoy.isoformat(),
        'semanas':       semanas,
    })


@login_required(login_url='login')
def turnos_supervisor(request):

    usuario_id    = request.session.get('usuario_id')
    turno_horario = get_turno_supervisor(usuario_id)
    busqueda      = request.GET.get('q', '')

    if turno_horario:
        ids_empleados = get_empleados_de_turno_supervisor(turno_horario)
        lista = RotacionTurno.objects.select_related(
            'empleado', 'turno'
        ).filter(
            empleado_id__in=ids_empleados,
            turno__horario=turno_horario,
        ).order_by('-fecha_inicio')
    else:
        lista = RotacionTurno.objects.none()
        messages.warning(request, "No tienes un turno asignado esta semana.")

    if busqueda:
        lista = lista.filter(empleado__nombre__icontains=busqueda)

    return render(request, 'modulos/turnos/turnos_supervisor.html', {
        'turnos':    lista,
        'rol':       'Supervisor',
        'fecha_hoy': timezone.now().date(),
        'busqueda':  busqueda,
        'mi_turno':  turno_horario or '',
    })


@login_required(login_url='login')
def guardar_rotacion(request):
    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')

        rotacion_id    = request.POST.get('id', '').strip()
        empleado_id    = request.POST.get('empleado_id', '').strip()
        turno_id       = request.POST.get('turno_id', '').strip()
        fecha_inicio   = request.POST.get('fecha_inicio', '').strip()
        fecha_fin      = request.POST.get('fecha_fin', '').strip()
        semana         = request.POST.get('semana', '').strip()
        sabado         = request.POST.get('sabado_asignado') == 'on'
        horario_sabado = request.POST.get('horario_sabado', '').strip() or None
        estado         = request.POST.get('estado', 'Pendiente')

        if not all([empleado_id, turno_id, fecha_inicio, fecha_fin, semana]):
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('turnos')

        if sabado and not horario_sabado:
            messages.error(request, "Debes seleccionar el horario del sábado.")
            return redirect('turnos')

        try:
            semana_int = int(semana)
            if not (1 <= semana_int <= 53):
                raise ValueError
        except ValueError:
            messages.error(request, "El número de semana debe estar entre 1 y 53.")
            return redirect('turnos')

        hoy           = date.today()
        semana_actual = hoy.isocalendar()[1]

        if semana_int < semana_actual:
            messages.error(request, f"No puedes asignar turnos en semanas anteriores. Semana actual: {semana_actual}.")
            return redirect('turnos')

        try:
            fi = date.fromisoformat(fecha_inicio)
            ff = date.fromisoformat(fecha_fin)
        except ValueError:
            messages.error(request, "El formato de fecha no es válido.")
            return redirect('turnos')

        if not rotacion_id and fi < hoy:
            messages.error(request, "La fecha de inicio no puede ser anterior a hoy.")
            return redirect('turnos')

        if ff < fi:
            messages.error(request, "La fecha de fin no puede ser anterior a la de inicio.")
            return redirect('turnos')

        semana_de_fi = fi.isocalendar()[1]
        if semana_de_fi != semana_int:
            messages.error(request, f"La fecha de inicio pertenece a la semana {semana_de_fi}, no a la semana {semana_int}.")
            return redirect('turnos')

        estados_validos = ['Asignado', 'Completado', 'Pendiente']
        if estado not in estados_validos:
            messages.error(request, "Estado no válido.")
            return redirect('turnos')

        horarios_sabado_validos = ['Mañana 6:00am - 12:00pm', 'Tarde 12:00pm - 6:00pm']
        if horario_sabado and horario_sabado not in horarios_sabado_validos:
            messages.error(request, "Horario de sábado no válido.")
            return redirect('turnos')

        try:
            empleado = get_object_or_404(Empleado, id=empleado_id)
            turno    = get_object_or_404(Turno, id=turno_id)

            if rotacion_id:
                rot                 = get_object_or_404(RotacionTurno, id=rotacion_id)
                rot.empleado        = empleado
                rot.turno           = turno
                rot.fecha_inicio    = fi
                rot.fecha_fin       = ff
                rot.semana          = semana_int
                rot.sabado_asignado = sabado
                rot.horario_sabado  = horario_sabado if sabado else None
                rot.estado          = estado
                rot.save()
                messages.success(request, "Rotación actualizada correctamente.")
            else:
                if RotacionTurno.objects.filter(
                    empleado=empleado,
                    fecha_inicio=fi,
                    fecha_fin=ff
                ).exists():
                    messages.error(request, f"{empleado.nombre} ya tiene un turno asignado para ese período.")
                    return redirect('turnos')

                RotacionTurno.objects.create(
                    empleado        = empleado,
                    turno           = turno,
                    fecha_inicio    = fi,
                    fecha_fin       = ff,
                    semana          = semana_int,
                    sabado_asignado = sabado,
                    horario_sabado  = horario_sabado if sabado else None,
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
 
    # 👇 ahora SÍ respeta los filtros de la pantalla
    horario_filtro = request.GET.get('horario', '')
    estado_filtro  = request.GET.get('estado', '')
 
    lista = Turno.objects.all()
 
    if horario_filtro:
        lista = lista.filter(horario=horario_filtro)
    if estado_filtro == 'Activo':
        lista = lista.filter(activo=True)
    elif estado_filtro == 'Inactivo':
        lista = lista.filter(activo=False)
 
    total_turnos = lista.count()
    activos = lista.filter(activo=True).count()
    inactivos = lista.filter(activo=False).count()
 
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25
    )
 
    elementos = []
    estilos = getSampleStyleSheet()
 
    titulo_style = ParagraphStyle('Titulo', parent=estilos['Title'], fontName='Helvetica-Bold',
                                   fontSize=22, alignment=1, textColor=colors.HexColor('#3E2723'))
    subtitulo_style = ParagraphStyle('Subtitulo', parent=estilos['Normal'], alignment=1,
                                      fontSize=10, textColor=colors.HexColor('#7A6A5D'))
    resumen_style = ParagraphStyle('Resumen', parent=estilos['Normal'], alignment=1, fontSize=13,
                                    fontName='Helvetica-Bold', textColor=colors.white)
    pie_style = ParagraphStyle('Pie', parent=estilos['Normal'], alignment=1,
                                fontSize=8, textColor=colors.HexColor('#8D6E63'))
 
    elementos.append(Paragraph("REPORTE DE TURNOS", titulo_style))
    elementos.append(Paragraph("Sistema de Gestión ChocoFlow", subtitulo_style))
    elementos.append(Spacer(1, 15))
 
    resumen = Table([[
        Paragraph(f"<b>Total Turnos</b><br/>{total_turnos}", resumen_style),
        Paragraph(f"<b>Activos</b><br/>{activos}", resumen_style),
        Paragraph(f"<b>Inactivos</b><br/>{inactivos}", resumen_style),
    ]], colWidths=[230, 230, 230])
 
    resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#5D4037')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#6D4C41')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#8D6E63')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    elementos.append(resumen)
    elementos.append(Spacer(1, 20))
 
    datos = [['Horario', 'Estado']]
    for t in lista:
        datos.append([t.horario, 'Activo' if t.activo else 'Inactivo'])
 
    # 2 columnas, ancho total amplio porque ahora sobra espacio en horizontal
    tabla = Table(datos, colWidths=[550, 150])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4E342E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.6, colors.HexColor('#D7CCC8')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FAF7F2'), colors.HexColor('#F2ECE5')]),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("Documento generado automáticamente por ChocoFlow", pie_style))
 
    doc.build(elementos)
    pdf = buffer.getvalue()
    buffer.close()
 
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_turnos.pdf"'
    response.write(pdf)
    return response
 

@login_required(login_url='login')
def generar_reporte_rotacion(request):
 
    semana_filtro = request.GET.get('semana', '')
 
    lista = RotacionTurno.objects.select_related('empleado', 'turno').all()
 
    if semana_filtro:
        lista = lista.filter(semana=semana_filtro)
 
    total_rotaciones = lista.count()
    sabados = lista.filter(sabado_asignado=True).count()
    activas = lista.filter(estado='Asignado').count()
 
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=20, leftMargin=20, topMargin=25, bottomMargin=25
    )
 
    elementos = []
    estilos = getSampleStyleSheet()
 
    titulo_style = ParagraphStyle('Titulo', parent=estilos['Title'], fontName='Helvetica-Bold',
                                   fontSize=22, alignment=1, textColor=colors.HexColor('#3E2723'))
    subtitulo_style = ParagraphStyle('Subtitulo', parent=estilos['Normal'], alignment=1,
                                      fontSize=10, textColor=colors.HexColor('#7A6A5D'))
    resumen_style = ParagraphStyle('Resumen', parent=estilos['Normal'], alignment=1, fontSize=13,
                                    fontName='Helvetica-Bold', textColor=colors.white)
    pie_style = ParagraphStyle('Pie', parent=estilos['Normal'], alignment=1,
                                fontSize=8, textColor=colors.HexColor('#8D6E63'))
 
    elementos.append(Paragraph("REPORTE DE ROTACIÓN DE TURNOS", titulo_style))
    elementos.append(Paragraph("Sistema de Gestión ChocoFlow", subtitulo_style))
    elementos.append(Spacer(1, 15))
 
    resumen = Table([[
        Paragraph(f"<b>Total Rotaciones</b><br/>{total_rotaciones}", resumen_style),
        Paragraph(f"<b>Sábados Asignados</b><br/>{sabados}", resumen_style),
        Paragraph(f"<b>Asignadas</b><br/>{activas}", resumen_style),
    ]], colWidths=[250, 250, 250])
 
    resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#5D4037')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#6D4C41')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#8D6E63')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    elementos.append(resumen)
    elementos.append(Spacer(1, 20))
 
    datos = [['Empleado', 'Turno', 'Semana', 'Inicio', 'Fin', 'Sábado', 'Horario Sábado', 'Estado']]
    for r in lista:
        datos.append([
            r.empleado.nombre, r.turno.horario, str(r.semana),
            str(r.fecha_inicio), str(r.fecha_fin),
            'Sí' if r.sabado_asignado else 'No',
            r.horario_sabado or '—', r.estado,
        ])
 
    # 8 columnas → 8 anchos, suma = 752 (cabe en landscape letter)
    tabla = Table(datos, colWidths=[120, 110, 60, 80, 80, 60, 130, 112], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4E342E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.6, colors.HexColor('#D7CCC8')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FAF7F2'), colors.HexColor('#F2ECE5')]),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("Documento generado automáticamente por ChocoFlow", pie_style))
 
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
        'empleado', 'turno_actual', 'turno_solicitado'
    ).all()

    if query:
        lista = lista.filter(empleado__nombre__icontains=query)
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)

    turnos_activos    = Turno.objects.filter(activo=True)
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

        nuevo_estado    = request.POST.get('estado', '').strip()
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
 
    # 👇 ahora SÍ respeta los filtros de la pantalla
    query  = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
 
    lista = Solicitud.objects.select_related(
        'empleado', 'turno_actual', 'turno_solicitado'
    ).all()
 
    if query:
        lista = lista.filter(empleado__nombre__icontains=query)
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)
 
    total_solicitudes = lista.count()
    pendientes = lista.filter(estado='Pendiente').count()
    aprobadas = lista.filter(estado='Aprobado').count()
 
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=20, leftMargin=20, topMargin=25, bottomMargin=25
    )
 
    elementos = []
    estilos = getSampleStyleSheet()
 
    titulo_style = ParagraphStyle('Titulo', parent=estilos['Title'], fontName='Helvetica-Bold',
                                   fontSize=22, alignment=1, textColor=colors.HexColor('#3E2723'))
    subtitulo_style = ParagraphStyle('Subtitulo', parent=estilos['Normal'], fontSize=10,
                                      alignment=1, textColor=colors.HexColor('#7A6A5D'))
    resumen_style = ParagraphStyle('Resumen', parent=estilos['Normal'], fontSize=13, alignment=1,
                                    fontName='Helvetica-Bold', textColor=colors.white)
    pie_style = ParagraphStyle('Pie', parent=estilos['Normal'], fontSize=8, alignment=1,
                                textColor=colors.HexColor('#8D6E63'))
 
    elementos.append(Paragraph("REPORTE DE SOLICITUDES", titulo_style))
    elementos.append(Paragraph("Sistema de Gestión ChocoFlow", subtitulo_style))
    elementos.append(Spacer(1, 15))
 
    resumen = Table([[
        Paragraph(f"<b>Total Solicitudes</b><br/>{total_solicitudes}", resumen_style),
        Paragraph(f"<b>Pendientes</b><br/>{pendientes}", resumen_style),
        Paragraph(f"<b>Aprobadas</b><br/>{aprobadas}", resumen_style),
    ]], colWidths=[250, 250, 250])
 
    resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#5D4037')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#6D4C41')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#8D6E63')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    elementos.append(resumen)
    elementos.append(Spacer(1, 20))
 
    datos = [['Empleado', 'Turno Actual', 'Turno Solicitado', 'Motivo', 'Estado']]
    for s in lista:
        datos.append([
            s.empleado.nombre,
            s.turno_actual.horario,
            s.turno_solicitado.horario,
            (s.motivo[:80] + "...") if len(s.motivo) > 80 else s.motivo,
            s.estado,
        ])
 
    # 🛠️ FIX: 5 columnas → 5 anchos (antes tenías 6 anchos para 5 columnas)
    tabla = Table(datos, colWidths=[130, 140, 140, 280, 62], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4E342E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#333333')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.6, colors.HexColor('#D7CCC8')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FAF7F2'), colors.HexColor('#F2ECE5')]),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("Documento generado automáticamente por ChocoFlow", pie_style))
 
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
    ).exclude(estado='Finalizado')

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


def _validar_turno_empleado(empleado, turno, fecha):
    """
    Valida que el turno seleccionado coincida con la rotación activa
    del empleado para la fecha dada.
    Retorna (True, None) si es válido, o (False, mensaje) si no.
    """
    rotacion = RotacionTurno.objects.filter(
        empleado=empleado,
        fecha_inicio__lte=fecha,
        fecha_fin__gte=fecha,
    ).select_related('turno').first()

    if not rotacion:
        return False, f"El empleado {empleado.nombre} no tiene un turno asignado para esa fecha."

    if rotacion.turno.id != turno.id:
        return False, (
            f"El empleado {empleado.nombre} está en el turno "
            f"'{rotacion.turno.horario}' para esa fecha. "
            f"No se puede asignar una tarea en el turno '{turno.horario}'."
        )

    return True, None


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
    forzar        = request.POST.get('forzar', '0').strip()

    if not tarea or not fecha or not emp_id or not turno_id:
        messages.error(request, "Todos los campos son obligatorios.")
        return redirect('asignaciones')

    fecha_ingresada = date.fromisoformat(fecha)
    if fecha_ingresada < date.today():
        messages.error(request, "No se pueden asignar tareas en fechas anteriores a la actual.")
        return redirect('asignaciones')

    empleado = get_object_or_404(Empleado, id=emp_id)
    turno    = get_object_or_404(Turno, id=turno_id)

    valido, error_turno = _validar_turno_empleado(empleado, turno, fecha_ingresada)
    if not valido:
        messages.error(request, error_turno)
        return redirect('asignaciones')

    es_nueva = not asignacion_id
    if es_nueva and forzar != '1':
        tareas_del_dia = Asignacion.objects.filter(
            empleado=empleado,
            fecha_asignacion=fecha
        ).count()

        if tareas_del_dia >= 2:
            lista             = Asignacion.objects.select_related('empleado', 'turno', 'asignado_por').exclude(estado='Finalizado')
            empleados_activos = Empleado.objects.filter(estado='Activo')
            turnos_activos    = Turno.objects.filter(activo=True)

            return render(request, 'modulos/asignaciones/asignaciones.html', {
                'asignaciones':     lista,
                'empleados':        empleados_activos,
                'turnos':           turnos_activos,
                'confirmar_extra':  True,
                'extra_tarea':      tarea,
                'extra_fecha':      fecha,
                'extra_emp_id':     emp_id,
                'extra_turno_id':   turno_id,
                'extra_estado':     estado,
                'extra_emp_nombre': empleado.nombre,
            })

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


@login_required(login_url='login')
def inactivar_asignacion(request, id):
    asignacion        = get_object_or_404(Asignacion, id=id)
    asignacion.estado = 'Finalizado'
    asignacion.save()
    messages.success(request, "Asignación finalizada.")
    return redirect('asignaciones')


@login_required(login_url='login')
def asignaciones_supervisor(request):

    usuario_id    = request.session.get('usuario_id')
    turno_horario = get_turno_supervisor(usuario_id)
    busqueda      = request.GET.get('q', '')

    if turno_horario:
        ids_empleados = get_empleados_de_turno_supervisor(turno_horario)
        lista = Asignacion.objects.select_related(
            'empleado', 'turno', 'asignado_por'
        ).filter(
            empleado_id__in=ids_empleados
        ).order_by('-fecha_asignacion')
        empleados_activos = Empleado.objects.filter(estado='Activo', id__in=ids_empleados)
    else:
        lista             = Asignacion.objects.none()
        empleados_activos = Empleado.objects.none()
        messages.warning(request, "No tienes un turno asignado esta semana.")

    if busqueda:
        lista = lista.filter(
            Q(tarea__icontains=busqueda) |
            Q(empleado__nombre__icontains=busqueda)
        )

    turnos_activos = Turno.objects.filter(activo=True)

    return render(request, 'modulos/asignaciones/asignaciones_supervisor.html', {
        'asignaciones': lista,
        'busqueda':     busqueda,
        'empleados':    empleados_activos,
        'turnos':       turnos_activos,
        'fecha_hoy':    timezone.now().date(),
        'mi_turno':     turno_horario or '',
    })


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

    turno_horario = get_turno_supervisor(usuario_id)
    if not turno_horario:
        messages.error(request, "No tienes un turno asignado. No puedes crear asignaciones.")
        return redirect('asignaciones_supervisor')

    tarea    = request.POST.get('tarea', '').strip()
    fecha    = request.POST.get('fecha_asignacion', '').strip()
    emp_id   = request.POST.get('empleado_id', '').strip()
    turno_id = request.POST.get('turno_id', '').strip()

    if not tarea or not fecha or not emp_id or not turno_id:
        messages.error(request, "Todos los campos son obligatorios.")
        return redirect('asignaciones_supervisor')

    fecha_ingresada = date.fromisoformat(fecha)
    if fecha_ingresada < date.today():
        messages.error(request, "No se pueden asignar tareas en fechas anteriores a la actual.")
        return redirect('asignaciones_supervisor')

    empleado = get_object_or_404(Empleado, id=emp_id)
    turno    = get_object_or_404(Turno, id=turno_id)

    # Verificar que el empleado pertenece al turno del supervisor esta semana
    ids_empleados = get_empleados_de_turno_supervisor(turno_horario)
    if empleado.id not in list(ids_empleados):
        messages.error(request, f"El empleado {empleado.nombre} no pertenece a tu turno.")
        return redirect('asignaciones_supervisor')

    valido, error_turno = _validar_turno_empleado(empleado, turno, fecha_ingresada)
    if not valido:
        messages.error(request, error_turno)
        return redirect('asignaciones_supervisor')

    tareas_del_dia = Asignacion.objects.filter(
        empleado=empleado,
        fecha_asignacion=fecha
    ).count()

    if tareas_del_dia >= 2:
        messages.error(
            request,
            f"El empleado {empleado.nombre} ya tiene 2 tareas asignadas para esa fecha."
        )
        return redirect('asignaciones_supervisor')

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


@login_required(login_url='login')
def generar_reporte_asignaciones(request):
 
    query = request.GET.get('q', '')
 
    lista = Asignacion.objects.select_related(
        'empleado', 'turno', 'asignado_por'
    ).exclude(estado='Finalizado')
 
    if query:
        lista = lista.filter(
            Q(tarea__icontains=query) |
            Q(empleado__nombre__icontains=query)
        )
 
    total_asignaciones = lista.count()
 
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=25, leftMargin=25, topMargin=35, bottomMargin=25
    )
 
    elementos = []
    estilos = getSampleStyleSheet()
 
    titulo_style = ParagraphStyle('Titulo', parent=estilos['Title'], fontName='Helvetica-Bold',
                                   fontSize=22, leading=28, alignment=1, textColor=colors.HexColor('#3E2723'))
    subtitulo_style = ParagraphStyle('Subtitulo', parent=estilos['Normal'], fontSize=10,
                                      alignment=1, textColor=colors.HexColor('#8D6E63'))
    tarjeta_style = ParagraphStyle('Tarjeta', parent=estilos['Normal'], alignment=1,
                                    fontSize=11, textColor=colors.white)
    pie_style = ParagraphStyle('Pie', parent=estilos['Normal'], alignment=1,
                                fontSize=8, textColor=colors.HexColor('#8D6E63'))
 
    elementos.append(Paragraph("Reporte de Asignaciones", titulo_style))
    elementos.append(Paragraph("Sistema de Gestión ChocoFlow", subtitulo_style))
    elementos.append(Spacer(1, 15))
 
    resumen = Table([[
        Paragraph(f"<b>Total Asignaciones Activas</b><br/>{total_asignaciones}", tarjeta_style)
    ]], colWidths=[300])
    resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#6D4C41')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    elementos.append(resumen)
    elementos.append(Spacer(1, 20))
 
    datos = [['Tarea', 'Empleado', 'Turno', 'Fecha', 'Estado', 'Asignado Por']]
    for a in lista:
        datos.append([
            a.tarea, a.empleado.nombre, a.turno.horario,
            str(a.fecha_asignacion), a.estado, a.asignado_por.nombre,
        ])
 
    tabla = Table(datos, colWidths=[180, 120, 140, 90, 90, 132], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5D4037')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D7CCC8')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FAFAFA'), colors.HexColor('#F5F5F5')]),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("Documento generado automáticamente por ChocoFlow", pie_style))
 
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

        produccion_id      = request.POST.get('id', '').strip()
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

        # Validar que fecha_entrega no sea de una semana anterior a la actual
        hoy            = timezone.now().date()
        inicio_semana  = hoy - timedelta(days=hoy.weekday())  # lunes de esta semana
        fecha_entrega_date = date.fromisoformat(fecha_entrega)
        if fecha_entrega_date < inicio_semana:
            messages.error(request, "La fecha de entrega no puede ser de una semana anterior a la actual.")
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
    produccion = get_object_or_404(Produccion, id=id)

    if produccion.estado == 'Finalizado':
        messages.error(
            request,
            "No se puede cancelar una producción finalizada."
        )
        return redirect('producciones')

    produccion.estado = 'Cancelado'
    produccion.save()
    messages.success(request, "Producción cancelada.")
    return redirect('producciones')


@login_required(login_url='login')
def generar_reporte_producciones(request):
 
    lista = Produccion.objects.select_related('empleado_responsable').all()
 
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
 
    if query:
        lista = lista.filter(producto__icontains=query)
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)
 
    total_producciones = lista.count()
 
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=25, leftMargin=25, topMargin=35, bottomMargin=25
    )
 
    elementos = []
    estilos = getSampleStyleSheet()
 
    titulo_style = ParagraphStyle('Titulo', parent=estilos['Title'], fontName='Helvetica-Bold',
                                   fontSize=22, leading=28, alignment=1, textColor=colors.HexColor('#3E2723'))
    subtitulo_style = ParagraphStyle('Subtitulo', parent=estilos['Normal'], fontSize=10,
                                      alignment=1, textColor=colors.HexColor('#8D6E63'))
    tarjeta_style = ParagraphStyle('Tarjeta', parent=estilos['Normal'], alignment=1,
                                    fontSize=11, textColor=colors.white)
    pie_style = ParagraphStyle('Pie', parent=estilos['Normal'], alignment=1,
                                fontSize=8, textColor=colors.HexColor('#8D6E63'))
 
    elementos.append(Paragraph("Reporte de Producciones", titulo_style))
    elementos.append(Paragraph("Sistema de Gestión ChocoFlow", subtitulo_style))
    elementos.append(Spacer(1, 15))
 
    resumen = Table([[
        Paragraph(f"<b>Total Producciones</b><br/>{total_producciones}", tarjeta_style)
    ]], colWidths=[300])
    resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#6D4C41')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    elementos.append(resumen)
    elementos.append(Spacer(1, 20))
 
    datos = [['Producto', 'Responsable', 'Cantidad Requerida', 'Fecha Entrega', 'Fecha Límite', 'Estado']]
    for p in lista:
        datos.append([
            p.producto or '—', p.empleado_responsable.nombre, p.cantidad_requerida or '—',
            str(p.fecha_entrega), str(p.fecha_limite), p.estado,
        ])
 
    tabla = Table(datos, colWidths=[180, 150, 130, 110, 110, 92], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5D4037')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D7CCC8')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FAFAFA'), colors.HexColor('#F5F5F5')]),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("Documento generado automáticamente por ChocoFlow", pie_style))
 
    doc.build(elementos)
    pdf = buffer.getvalue()
    buffer.close()
 
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_producciones.pdf"'
    response.write(pdf)
    return response



@login_required(login_url='login')
def producciones_supervisor(request):

    usuario_id    = request.session.get('usuario_id')
    turno_horario = get_turno_supervisor(usuario_id)
    query         = request.GET.get('q', '')
    estado        = request.GET.get('estado', '')

    if turno_horario:
        ids_empleados = get_empleados_de_turno_supervisor(turno_horario)
        lista = Produccion.objects.select_related(
            'empleado_responsable'
        ).filter(empleado_responsable_id__in=ids_empleados)
        empleados = Empleado.objects.filter(estado='Activo', id__in=ids_empleados)
    else:
        lista     = Produccion.objects.none()
        empleados = Empleado.objects.none()
        messages.warning(request, "No tienes un turno asignado esta semana.")

    if query:
        lista = lista.filter(producto__icontains=query)
    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)

    return render(request, 'modulos/produccion/produccion_supervisor.html', {
        'producciones': lista,
        'empleados':    empleados,
        'fecha_hoy':    timezone.now().date(),
        'mi_turno':     turno_horario or '',
    })


@login_required(login_url='login')
def guardar_produccion_supervisor(request):
    if request.method == 'POST':

        # Validar sesión
        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')
        try:
            usuario_perfil = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            messages.error(request, "No se encontró tu perfil.")
            return redirect('login')

        produccion_id      = request.POST.get('id', '').strip()
        producto           = request.POST.get('producto', '').strip()
        ingredientes       = request.POST.get('ingredientes', '').strip()
        cantidad_requerida = request.POST.get('cantidad_requerida', '').strip()
        fecha_entrega      = request.POST.get('fecha_entrega', '').strip()
        fecha_limite       = request.POST.get('fecha_limite', '').strip()
        estado             = request.POST.get('estado', '').strip()
        emp_id             = request.POST.get('empleado_responsable', '').strip()

        # Campos obligatorios
        if not producto or not emp_id or not fecha_entrega or not fecha_limite or not estado:
            messages.error(request, "Los campos obligatorios no pueden estar vacíos.")
            return redirect('producciones_supervisor')

        # Ingredientes obligatorios
        if not ingredientes:
            messages.error(request, "Los ingredientes son obligatorios.")
            return redirect('producciones_supervisor')

        # Validar que fecha_limite no sea anterior a fecha_entrega
        if fecha_limite < fecha_entrega:
            messages.error(request, "La fecha límite no puede ser anterior a la fecha de entrega.")
            return redirect('producciones_supervisor')

        # Validar que fecha_entrega no sea de una semana anterior a la actual
        hoy                = timezone.now().date()
        inicio_semana      = hoy - timedelta(days=hoy.weekday())  # lunes de esta semana
        fecha_entrega_date = date.fromisoformat(fecha_entrega)
        if fecha_entrega_date < inicio_semana:
            messages.error(request, "La fecha de entrega no puede ser de una semana anterior a la actual.")
            return redirect('producciones_supervisor')

        empleado = get_object_or_404(Empleado, id=emp_id)

        if produccion_id:
            produccion = get_object_or_404(Produccion, id=produccion_id)
        else:
            produccion = Produccion()

        produccion.producto             = producto
        produccion.ingredientes         = ingredientes
        produccion.cantidad_requerida   = cantidad_requerida
        produccion.fecha_entrega        = fecha_entrega
        produccion.fecha_limite         = fecha_limite
        produccion.estado               = estado
        produccion.empleado_responsable = empleado
        produccion.creado_por           = usuario_perfil

        try:
            produccion.save()
            messages.success(request, "Producción guardada correctamente.")
        except Exception as e:
            messages.error(request, f"Error al guardar: {str(e)}")

    return redirect('producciones_supervisor')

# ===================
# EXPORTACIONES
# ===================

@login_required(login_url='login')
def gestionar_exportaciones(request):

    q      = request.GET.get('q', '')
    estado = request.GET.get('estado', '')

    exportaciones = Exportacion.objects.select_related('produccion', 'lote').all()

    if q:
        exportaciones = exportaciones.filter(destino__icontains=q)
    if estado:
        exportaciones = exportaciones.filter(estado=estado)

    producciones = Produccion.objects.filter(estado__in=['En Proceso', 'Pendiente'])
    lotes = Lote.objects.all()

    return render(request, 'modulos/exportaciones/exportaciones.html', {
        'exportaciones': exportaciones,
        'producciones':  producciones,
        'lotes':         lotes,
        'q':             q,
        'estado_filtro': estado,
    })


@login_required(login_url='login')
def exportaciones_supervisor(request):

    usuario_id    = request.session.get('usuario_id')
    turno_horario = get_turno_supervisor(usuario_id)
    busqueda      = request.GET.get('q', '')
    estado_filtro = request.GET.get('estado', '')

    if turno_horario:
        ids_empleados    = get_empleados_de_turno_supervisor(turno_horario)
        ids_producciones = Produccion.objects.filter(
            empleado_responsable_id__in=ids_empleados
        ).values_list('id', flat=True)
        lista = Exportacion.objects.filter(
            produccion_id__in=ids_producciones
        ).order_by('-fecha_envio')
    else:
        lista = Exportacion.objects.none()
        messages.warning(request, "No tienes un turno asignado esta semana.")

    if busqueda:
        lista = lista.filter(
            Q(destino__icontains=busqueda)
        )
    if estado_filtro and estado_filtro != 'Todos':
        lista = lista.filter(estado=estado_filtro)

    return render(request, 'modulos/exportaciones/exportaciones_supervisor.html', {
        'exportaciones': lista,
        'busqueda':      busqueda,
        'estado_filtro': estado_filtro,
        'fecha_hoy':     timezone.now().date(),
        'mi_turno':      turno_horario or '',
    })


@login_required(login_url='login')
def guardar_exportacion(request):
    if request.method == 'POST':

        import re
        from datetime import datetime
        from decimal import Decimal, InvalidOperation

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')

        try:
            Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            messages.error(request, "No se encontró tu perfil.")
            return redirect('login')

        exp_id               = request.POST.get('id', '').strip()
        destino              = request.POST.get('destino', '').strip()
        pais                 = request.POST.get('pais', '').strip()
        nombre_producto      = request.POST.get('nombre_producto', '').strip()
        fecha_envio          = request.POST.get('fecha_envio', '').strip()
        fecha_entrega        = request.POST.get('fecha_entrega', '').strip()
        estado               = request.POST.get('estado', '').strip()
        produccion_id        = request.POST.get('produccion_id', '').strip()
        lote_id              = request.POST.get('lote_id', '').strip()
        cantidad_cajas       = request.POST.get('cantidad_cajas', '').strip()
        unidades_por_caja    = request.POST.get('unidades_por_caja', '').strip()
        peso_caja            = request.POST.get('peso_caja', '').strip()
        peso_total           = request.POST.get('peso_total', '').strip()
        empresa_exportadora  = request.POST.get('empresa_exportadora', '').strip()
        numero_contenedor    = request.POST.get('numero_contenedor', '').strip()
        observaciones        = request.POST.get('observaciones', '').strip()

        if not all([destino, pais, fecha_envio, fecha_entrega, estado]):
            messages.error(request, "Los campos Destino, País, Fechas y Estado son obligatorios.")
            return redirect('gestionar_exportaciones')

        if not produccion_id:
            messages.error(request, "Debes seleccionar una producción asociada.")
            return redirect('gestionar_exportaciones')

        if not lote_id:
            messages.error(request, "Debes seleccionar un lote asociado.")
            return redirect('gestionar_exportaciones')

        patron_texto = r'^[A-Za-záéíóúÁÉÍÓÚñÑüÜ\s]+$'
        if not re.match(patron_texto, destino):
            messages.error(request, "El destino solo puede contener letras.")
            return redirect('gestionar_exportaciones')
        if not re.match(patron_texto, pais):
            messages.error(request, "El país solo puede contener letras.")
            return redirect('gestionar_exportaciones')
        if nombre_producto and not re.match(patron_texto, nombre_producto):
            messages.error(request, "El nombre del producto solo puede contener letras.")
            return redirect('gestionar_exportaciones')

        cantidad_cajas_val = None
        if cantidad_cajas:
            if not cantidad_cajas.isdigit() or int(cantidad_cajas) <= 0:
                messages.error(request, "La cantidad de cajas debe ser un número entero positivo.")
                return redirect('gestionar_exportaciones')
            cantidad_cajas_val = int(cantidad_cajas)

        unidades_por_caja_val = None
        if unidades_por_caja:
            if not unidades_por_caja.isdigit() or int(unidades_por_caja) <= 0:
                messages.error(request, "Las unidades por caja deben ser un número entero positivo.")
                return redirect('gestionar_exportaciones')
            unidades_por_caja_val = int(unidades_por_caja)

        peso_caja_val = None
        if peso_caja:
            try:
                peso_caja_val = Decimal(peso_caja)
                if peso_caja_val <= 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                messages.error(request, "El peso por caja debe ser un número decimal positivo.")
                return redirect('gestionar_exportaciones')

        peso_total_val = None
        if peso_total:
            try:
                peso_total_val = Decimal(peso_total)
                if peso_total_val <= 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                messages.error(request, "El peso total debe ser un número decimal positivo.")
                return redirect('gestionar_exportaciones')

        try:
            fecha_envio_obj   = datetime.strptime(fecha_envio, '%Y-%m-%d').date()
            fecha_entrega_obj = datetime.strptime(fecha_entrega, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Las fechas ingresadas no son válidas.")
            return redirect('gestionar_exportaciones')

        if fecha_entrega_obj < fecha_envio_obj:
            messages.error(request, "La fecha de entrega no puede ser anterior a la fecha de envío.")
            return redirect('gestionar_exportaciones')

        produccion = get_object_or_404(Produccion, pk=produccion_id)

        if fecha_envio_obj < produccion.fecha_entrega:
            messages.error(
                request,
                f"La fecha de envío ({fecha_envio_obj}) no puede ser anterior a la fecha "
                f"de entrega de la producción ({produccion.fecha_entrega})."
            )
            return redirect('gestionar_exportaciones')

        lote = get_object_or_404(Lote, pk=lote_id)

        if lote.produccion_id != produccion.id:
            messages.error(request, "El lote seleccionado no pertenece a la producción elegida.")
            return redirect('gestionar_exportaciones')

        if fecha_envio_obj < lote.fecha_produccion:
            messages.error(
                request,
                f"La fecha de envío ({fecha_envio_obj}) no puede ser anterior a la fecha "
                f"de producción del lote ({lote.fecha_produccion})."
            )
            return redirect('gestionar_exportaciones')

        if fecha_entrega_obj > lote.fecha_vencimiento:
            messages.error(
                request,
                f"La fecha de entrega ({fecha_entrega_obj}) no puede ser posterior a la fecha "
                f"de vencimiento del lote ({lote.fecha_vencimiento})."
            )
            return redirect('gestionar_exportaciones')

        if exp_id:
            exp = get_object_or_404(Exportacion, pk=exp_id)
        else:
            exp = Exportacion()

        exp.destino             = destino
        exp.pais                = pais
        exp.nombre_producto     = nombre_producto or None
        exp.fecha_envio         = fecha_envio_obj
        exp.fecha_entrega       = fecha_entrega_obj
        exp.estado              = estado
        exp.produccion          = produccion
        exp.lote                = lote
        exp.cantidad_cajas      = cantidad_cajas_val
        exp.unidades_por_caja   = unidades_por_caja_val
        exp.peso_caja           = peso_caja_val
        exp.peso_total          = peso_total_val
        exp.empresa_exportadora = empresa_exportadora or None
        exp.numero_contenedor   = numero_contenedor or None
        exp.observaciones       = observaciones or None
        exp.save()

        accion = "actualizada" if exp_id else "creada"
        messages.success(request, f"Exportación {accion} correctamente.")

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
 
    exportaciones = Exportacion.objects.select_related('lote', 'produccion').all()
 
    busqueda = request.GET.get('busqueda', '')
    estado = request.GET.get('estado', '')
 
    if busqueda:
        exportaciones = exportaciones.filter(destino__icontains=busqueda)
    if estado and estado != "Todos":
        exportaciones = exportaciones.filter(estado=estado)
 
    total_exportaciones = exportaciones.count()
 
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=20, leftMargin=20, topMargin=35, bottomMargin=25
    )
 
    elementos = []
    estilos = getSampleStyleSheet()
 
    titulo_style = ParagraphStyle('Titulo', parent=estilos['Title'], fontName='Helvetica-Bold',
                                   fontSize=22, leading=28, alignment=1, textColor=colors.HexColor('#3E2723'))
    subtitulo_style = ParagraphStyle('Subtitulo', parent=estilos['Normal'], fontSize=10,
                                      alignment=1, textColor=colors.HexColor('#8D6E63'))
    tarjeta_style = ParagraphStyle('Tarjeta', parent=estilos['Normal'], alignment=1,
                                    fontSize=11, textColor=colors.white)
    pie_style = ParagraphStyle('Pie', parent=estilos['Normal'], alignment=1,
                                fontSize=8, textColor=colors.HexColor('#8D6E63'))
 
    elementos.append(Paragraph("Reporte de Exportaciones", titulo_style))
    elementos.append(Paragraph("Sistema de Gestión ChocoFlow", subtitulo_style))
    elementos.append(Spacer(1, 15))
 
    resumen = Table([[
        Paragraph(f"<b>Total Exportaciones</b><br/>{total_exportaciones}", tarjeta_style)
    ]], colWidths=[300])
    resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#6D4C41')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    elementos.append(resumen)
    elementos.append(Spacer(1, 20))
 
    datos = [['Destino', 'País', 'Producto', 'Lote', 'Fecha Envío', 'Fecha Entrega', 'Estado']]
    for exp in exportaciones:
        # 🛠️ FIX: antes ponías "exp.lote or '-'", que imprime el objeto Lote completo.
        # Ahora mostramos el código real del lote.
        lote_txt = exp.lote.codigo_lote if exp.lote else '—'
        datos.append([
            exp.destino or '—', exp.pais or '—', exp.nombre_producto or '—', lote_txt,
            str(exp.fecha_envio), str(exp.fecha_entrega), exp.estado,
        ])
 
    # 🛠️ FIX: 7 columnas → 7 anchos (antes tenías solo 6 anchos para 7 columnas)
    tabla = Table(datos, colWidths=[105, 100, 110, 90, 100, 105, 92], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5D4037')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D7CCC8')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FAFAFA'), colors.HexColor('#F5F5F5')]),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("Documento generado automáticamente por ChocoFlow", pie_style))
 
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
    lotes = Lote.objects.select_related('produccion').all()  # ← quitado 'exportacion'

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

    usuario_id    = request.session.get('usuario_id')
    turno_horario = get_turno_supervisor(usuario_id)
    busqueda      = request.GET.get('q', '')

    if turno_horario:
        ids_empleados    = get_empleados_de_turno_supervisor(turno_horario)
        ids_producciones = Produccion.objects.filter(
            empleado_responsable_id__in=ids_empleados
        ).values_list('id', flat=True)
        lista = Lote.objects.select_related(
            'produccion'                          # ← quitado 'exportacion'
        ).filter(produccion_id__in=ids_producciones).order_by('-fecha_produccion')
    else:
        lista = Lote.objects.none()
        messages.warning(request, "No tienes un turno asignado esta semana.")

    if busqueda:
        lista = lista.filter(codigo_lote__icontains=busqueda)

    return render(request, 'modulos/lotes/lotes_supervisor.html', {
        'lotes':     lista,
        'busqueda':  busqueda,
        'fecha_hoy': timezone.now().date(),
        'mi_turno':  turno_horario or '',
    })


@login_required(login_url='login')
def guardar_lote(request):
    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')

        lote_id           = request.POST.get('id', '').strip()
        codigo_lote       = request.POST.get('codigo_lote', '').strip().upper()
        origen_cacao      = request.POST.get('origen_cacao', '').strip()
        cantidad          = request.POST.get('cantidad', '').strip()
        unidad            = request.POST.get('unidad', '').strip()
        nombre_producto   = request.POST.get('nombre_producto', '').strip()
        fecha_produccion  = request.POST.get('fecha_produccion', '').strip()
        fecha_vencimiento = request.POST.get('fecha_vencimiento', '').strip()
        produccion_id     = request.POST.get('produccion_id', '').strip()

        if not all([codigo_lote, cantidad, fecha_produccion, fecha_vencimiento, produccion_id]):
            messages.error(request, "Todos los campos obligatorios deben estar completos, incluyendo la producción.")
            return redirect('gestionar_lotes')

        if not re.fullmatch(r'[A-Z]{2}-\d{3}', codigo_lote):
            messages.error(request, "El código debe tener el formato XX-000 (2 letras y 3 números). Ej: CH-001, AB-123.")
            return redirect('gestionar_lotes')

        if not cantidad.isdigit():
            messages.error(request, "La cantidad debe contener únicamente números.")
            return redirect('gestionar_lotes')

        if unidad not in ['Kilogramos', 'Gramos', '']:
            messages.error(request, "La unidad seleccionada no es válida.")
            return redirect('gestionar_lotes')

        try:
            fecha_prod = datetime.strptime(fecha_produccion, '%Y-%m-%d').date()
            fecha_venc = datetime.strptime(fecha_vencimiento, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Las fechas ingresadas no son válidas.")
            return redirect('gestionar_lotes')

        produccion = get_object_or_404(Produccion, pk=produccion_id)

        if fecha_prod != produccion.fecha_entrega:
            messages.error(
                request,
                f"La fecha de producción del lote ({fecha_prod}) debe coincidir "
                f"con la fecha de entrega de la producción seleccionada ({produccion.fecha_entrega})."
            )
            return redirect('gestionar_lotes')

        if fecha_venc < fecha_prod:
            messages.error(request, "La fecha de vencimiento no puede ser anterior a la fecha de producción.")
            return redirect('gestionar_lotes')

        if lote_id:
            if Lote.objects.filter(codigo_lote=codigo_lote).exclude(pk=lote_id).exists():
                messages.error(request, f"Ya existe un lote con el código '{codigo_lote}'.")
                return redirect('gestionar_lotes')
            lote = get_object_or_404(Lote, pk=lote_id)
        else:
            if Lote.objects.filter(codigo_lote=codigo_lote).exists():
                messages.error(request, f"Ya existe un lote con el código '{codigo_lote}'.")
                return redirect('gestionar_lotes')
            lote = Lote()

        lote.codigo_lote       = codigo_lote
        lote.origen_cacao      = origen_cacao or None
        lote.cantidad          = cantidad
        lote.unidad            = unidad or None
        lote.nombre_producto   = nombre_producto or None
        lote.fecha_produccion  = fecha_prod
        lote.fecha_vencimiento = fecha_venc
        lote.produccion        = produccion
        lote.save()

        accion = "actualizado" if lote_id else "creado"
        messages.success(request, f"Lote '{codigo_lote}' {accion} correctamente.")

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
 
    lotes = Lote.objects.select_related('produccion').all()
 
    busqueda = request.GET.get('busqueda', '')
    if busqueda:
        lotes = lotes.filter(codigo_lote__icontains=busqueda)
 
    total_lotes = lotes.count()
 
    COLOR_PRIMARIO = colors.HexColor('#5D4037')
    COLOR_SECUNDARIO = colors.HexColor('#8D6E63')
    COLOR_CLARO = colors.HexColor('#F8F5F2')
    COLOR_BORDE = colors.HexColor('#D7CCC8')
    COLOR_TEXTO = colors.HexColor('#3E2723')
 
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=25, leftMargin=25, topMargin=35, bottomMargin=25
    )
 
    elementos = []
    estilos = getSampleStyleSheet()
 
    titulo_style = ParagraphStyle('Titulo', parent=estilos['Title'], fontName='Helvetica-Bold',
                                   fontSize=22, alignment=1, textColor=COLOR_PRIMARIO, spaceAfter=10)
    subtitulo_style = ParagraphStyle('Subtitulo', parent=estilos['Normal'], alignment=1,
                                      fontSize=10, textColor=colors.grey)
    pie_style = ParagraphStyle('Pie', parent=estilos['Normal'], alignment=1,
                                fontSize=8, textColor=COLOR_SECUNDARIO)
 
    elementos.append(Paragraph("📦 REPORTE DE LOTES", titulo_style))
    elementos.append(Paragraph("Sistema de Gestión ChocoFlow", subtitulo_style))
    elementos.append(Spacer(1, 20))
 
    resumen = Table([['Total Lotes', str(total_lotes)]], colWidths=[150, 150])
    resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), COLOR_PRIMARIO),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('BACKGROUND', (1, 0), (1, 0), COLOR_CLARO),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDE),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elementos.append(resumen)
    elementos.append(Spacer(1, 20))
 
    datos = [['Código', 'Cantidad', 'Fecha Producción', 'Fecha Vencimiento', 'Producción']]
    for lote in lotes:
        datos.append([
            lote.codigo_lote, str(lote.cantidad),
            str(lote.fecha_produccion), str(lote.fecha_vencimiento),
            str(lote.produccion),
        ])
 
    # 🛠️ FIX: 5 columnas → 5 anchos (antes tenías 6 anchos para 5 columnas)
    tabla = Table(datos, repeatRows=1, colWidths=[90, 80, 110, 110, 352])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARIO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_CLARO]),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(
        f"Documento generado automáticamente por ChocoFlow | Total registros: {total_lotes}",
        pie_style
    ))
 
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

@login_required(login_url='login')
def bitacora_supervisor(request):

    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    supervisor = Usuario.objects.filter(id=usuario_id, rol='Supervisor').first()
    if not supervisor:
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('login')

    producciones = Produccion.objects.all()

    if request.method == 'POST':

        titulo              = request.POST.get('titulo', '').strip()
        descripcion         = request.POST.get('descripcion', '').strip()
        tipo_reporte        = request.POST.get('tipo_reporte', '').strip()
        produccion_id       = request.POST.get('produccion', '').strip()
        unidades_producidas = request.POST.get('unidades_producidas', '').strip()
        unidades_pendientes = request.POST.get('unidades_pendientes', '').strip()
        observaciones       = request.POST.get('observaciones', '').strip()
        estado              = request.POST.get('estado', 'Borrador')

        ctx = {
            'producciones':       producciones,
            'today':              date.today(),
            'supervisor':         supervisor,
            'form_titulo':        titulo,
            'form_descripcion':   descripcion,
            'form_tipo':          tipo_reporte,
            'form_produccion':    produccion_id,
            'form_uds_prod':      unidades_producidas,
            'form_uds_pend':      unidades_pendientes,
            'form_observaciones': observaciones,
            'form_estado':        estado,
        }

        if not titulo or len(titulo) < 5:
            messages.error(request, "El título debe tener mínimo 5 caracteres.")
            return render(request, 'modulos/bitacora/bitacora_supervisor.html', ctx)

        if not descripcion or len(descripcion) < 20:
            messages.error(request, "La descripción debe tener mínimo 20 caracteres.")
            return render(request, 'modulos/bitacora/bitacora_supervisor.html', ctx)

        if not tipo_reporte:
            messages.error(request, "Seleccione un tipo de reporte.")
            return render(request, 'modulos/bitacora/bitacora_supervisor.html', ctx)

        if not produccion_id:
            messages.error(request, "Seleccione una producción.")
            return render(request, 'modulos/bitacora/bitacora_supervisor.html', ctx)

        if not unidades_producidas:
            messages.error(request, "Debe ingresar las unidades producidas.")
            return render(request, 'modulos/bitacora/bitacora_supervisor.html', ctx)

        if not unidades_pendientes:
            messages.error(request, "Debe ingresar las unidades pendientes.")
            return render(request, 'modulos/bitacora/bitacora_supervisor.html', ctx)

        produccion = Produccion.objects.filter(id=produccion_id).first()
        if not produccion:
            messages.error(request, "La producción seleccionada no existe.")
            return render(request, 'modulos/bitacora/bitacora_supervisor.html', ctx)

        if estado not in ['Borrador', 'Enviado']:
            estado = 'Borrador'

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

        if estado == 'Enviado':
            messages.success(request, "Bitácora enviada al administrador correctamente.")
        else:
            messages.success(request, "Bitácora guardada como borrador.")

        return redirect('listar_bitacoras_supervisor')

    return render(request, 'modulos/bitacora/bitacora_supervisor.html', {
        'producciones': producciones,
        'today':        date.today(),
        'supervisor':   supervisor,
    })


@login_required(login_url='login')
def enviar_bitacora(request, id):

    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    supervisor = Usuario.objects.filter(id=usuario_id, rol='Supervisor').first()
    if not supervisor:
        return redirect('login')

    bitacora = get_object_or_404(Bitacora, id=id, supervisor=supervisor)

    if bitacora.estado != 'Borrador':
        messages.error(request, "Solo puedes enviar bitácoras en estado Borrador.")
        return redirect('listar_bitacoras_supervisor')

    bitacora.estado = 'Enviado'
    bitacora.save()

    messages.success(request, f"Bitácora '{bitacora.titulo}' enviada al administrador.")
    return redirect('listar_bitacoras_supervisor')


@login_required(login_url='login')
def listar_bitacoras_supervisor(request):

    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    supervisor = Usuario.objects.filter(id=usuario_id, rol='Supervisor').first()
    if not supervisor:
        return redirect('login')

    bitacoras = Bitacora.objects.select_related(
        'produccion'
    ).filter(supervisor=supervisor).order_by('-fecha_registro')

    return render(request, 'modulos/bitacora/listar_bitacoras_supervisor.html', {
        'bitacoras':  bitacoras,
        'fecha_hoy':  date.today(),
        'supervisor': supervisor,
    })


@login_required(login_url='login')
def listar_bitacoras(request):

    bitacoras = Bitacora.objects.select_related(
        'supervisor', 'produccion'
    ).order_by('-fecha_registro')

    pendientes = bitacoras.filter(estado='Enviado').count()

    return render(request, 'modulos/bitacora/listar_bitacoras.html', {
        'bitacoras':  bitacoras,
        'pendientes': pendientes,
        'fecha_hoy':  date.today(),
    })


@login_required(login_url='login')
def revisar_bitacora(request, id):

    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')

        bitacora          = get_object_or_404(Bitacora, id=id)
        nuevo_estado      = request.POST.get('estado', '').strip()
        observacion_admin = request.POST.get('observacion_admin', '').strip()

        if nuevo_estado not in ['Aprobado', 'Rechazado']:
            messages.error(request, "Estado de revisión no válido.")
            return redirect('listar_bitacoras')

        if bitacora.estado != 'Enviado':
            messages.error(request, "Esta bitácora ya fue revisada.")
            return redirect('listar_bitacoras')

        bitacora.estado            = nuevo_estado
        bitacora.fecha_revision    = date.today()
        bitacora.observacion_admin = observacion_admin
        bitacora.save()

        accion = "aprobada" if nuevo_estado == "Aprobado" else "rechazada"
        messages.success(request, f"Bitácora '{bitacora.titulo}' {accion} correctamente.")

    return redirect('listar_bitacoras')

# ====================
# LOGICA DE CORREOS
# ====================
import os
import resend
from django.utils import timezone
from datetime import timedelta

resend.api_key = os.getenv("RESEND_API_KEY")

REMITENTE_CORREO = "ChocoFlow <onboarding@resend.dev>"  # 👈 cambia esto por tu dominio verificado en Resend


@login_required(login_url='login')
def correos_vista(request):
    from datetime import timedelta

    hoy     = timezone.now().date()
    lunes   = hoy - timedelta(days=hoy.weekday())
    domingo = lunes + timedelta(days=6)

    empleados = Empleado.objects.filter(estado='Activo').exclude(email='')
    historial = HistorialCorreo.objects.select_related('empleado').order_by('-fecha_envio')

    # Armar info de cada empleado para mostrar en la tabla
    empleados_info = []
    for emp in empleados:
        rotacion = RotacionTurno.objects.filter(
            empleado=emp,
            fecha_inicio__lte=domingo,
            fecha_fin__gte=lunes
        ).select_related('turno').first()

        asignaciones = Asignacion.objects.filter(
            empleado=emp,
            fecha_asignacion__range=(lunes, domingo)
        ).select_related('turno').order_by('fecha_asignacion')

        empleados_info.append({
            'empleado':    emp,
            'turno':       rotacion.turno.horario if rotacion else None,
            'asignaciones': asignaciones,
        })

    return render(request, 'modulos/correos/correos.html', {
        'historial':      historial,
        'empleados_info': empleados_info,
    })


@login_required(login_url='login')
def enviar_correos_masivos(request):
    if request.method != 'POST':
        return redirect('correos_vista')

    from datetime import timedelta

    hoy     = timezone.now().date()
    lunes   = hoy - timedelta(days=hoy.weekday())
    domingo = lunes + timedelta(days=6)

    # IDs seleccionados en el formulario
    ids_seleccionados = request.POST.getlist('empleados_ids')

    if not ids_seleccionados:
        messages.error(request, "No seleccionaste ningún empleado.")
        return redirect('correos_vista')

    empleados = Empleado.objects.filter(
        id__in=ids_seleccionados,
        estado='Activo'
    ).exclude(email='')

    enviados = 0
    errores  = 0

    for emp in empleados:
        try:
            rotacion = RotacionTurno.objects.filter(
                empleado=emp,
                fecha_inicio__lte=domingo,
                fecha_fin__gte=lunes
            ).select_related('turno').first()

            turno_txt = rotacion.turno.horario if rotacion else 'Sin turno asignado esta semana'

            asignaciones = Asignacion.objects.filter(
                empleado=emp,
                fecha_asignacion__range=(lunes, domingo)
            ).select_related('turno').order_by('fecha_asignacion')

            if asignaciones.exists():
                lista_asig = '\n'.join([
                    f"  - {a.fecha_asignacion.strftime('%d/%m/%Y')} | {a.tarea} | Turno: {a.turno.horario} | Estado: {a.estado}"
                    for a in asignaciones
                ])
            else:
                lista_asig = '  Sin asignaciones para esta semana.'

            asunto  = f"ChocoFlow - Tu turno y asignaciones del {lunes.strftime('%d/%m/%Y')} al {domingo.strftime('%d/%m/%Y')}"
            mensaje = (
                f"Hola {emp.nombre},\n\n"
                f"Te informamos tu turno y asignaciones para la semana "
                f"del {lunes.strftime('%d/%m/%Y')} al {domingo.strftime('%d/%m/%Y')}:\n\n"
                f"Turno asignado: {turno_txt}\n\n"
                f"Asignaciones de la semana:\n{lista_asig}\n\n"
                f"Si tienes alguna duda, comunicate con tu supervisor.\n\n"
                f"Saludos,\n"
                f"Equipo ChocoFlow"
            )

            resend.Emails.send({
                "from": REMITENTE_CORREO,
                "to": [emp.email],
                "subject": asunto,
                "text": mensaje,
            })

            HistorialCorreo.objects.create(
                empleado=emp,
                asunto=asunto,
                mensaje=mensaje,
                estado='Enviado',
            )
            enviados += 1

        except Exception as ex:
            HistorialCorreo.objects.create(
                empleado=emp,
                asunto=f"Intento semana {lunes.strftime('%d/%m/%Y')}",
                mensaje='',
                estado='Error',
                error_detalle=str(ex),
            )
            errores += 1

    if enviados:
        messages.success(request, f"✅ {enviados} correo(s) enviado(s) correctamente.")
    if errores:
        messages.warning(request, f"⚠️ {errores} correo(s) fallaron. Revisa el historial.")

    return redirect('correos_vista')

# ========================
# FUNCIONES DE ANÁLISIS IA
# ========================

def obtener_resumen_empresa():
    return {
        'empleados_activos':        Empleado.objects.filter(estado='Activo').count(),
        'empleados_suspendidos':    Empleado.objects.filter(estado='Suspendido').count(),
        'producciones_proceso':     Produccion.objects.filter(estado='En Proceso').count(),
        'producciones_finalizadas': Produccion.objects.filter(estado='Finalizado').count(),
        'exportaciones_pendientes': Exportacion.objects.filter(estado='Pendiente').count(),
        'total_lotes':              Lote.objects.count(),
    }


def detectar_alertas():
    alertas = []
    hoy = date.today()

    lotes_por_vencer = Lote.objects.filter(
        fecha_vencimiento__lte=hoy + timedelta(days=7),
        fecha_vencimiento__gte=hoy
    )
    for lote in lotes_por_vencer:
        alertas.append(f"⚠️ Lote {lote.codigo_lote} vence el {lote.fecha_vencimiento}.")

    lotes_vencidos = Lote.objects.filter(fecha_vencimiento__lt=hoy)
    for lote in lotes_vencidos:
        alertas.append(f"🚨 Lote {lote.codigo_lote} ya venció ({lote.fecha_vencimiento}).")

    exp_retrasadas = Exportacion.objects.filter(
        estado='Pendiente',
        fecha_envio__lt=hoy
    )
    for exp in exp_retrasadas:
        alertas.append(f"🚨 Exportación a {exp.destino} tenía fecha de envío {exp.fecha_envio} y sigue pendiente.")

    empleados_sin_turno = Empleado.objects.filter(
        estado='Activo'
    ).exclude(
        id__in=RotacionTurno.objects.values_list('empleado_id', flat=True)
    ).count()
    if empleados_sin_turno > 0:
        alertas.append(f"⚠️ {empleados_sin_turno} empleado(s) activo(s) sin turno asignado.")

    bitacoras = Bitacora.objects.filter(estado='Enviado').count()
    if bitacoras > 0:
        alertas.append(f"📋 {bitacoras} bitácora(s) pendiente(s) de revisión.")

    return alertas


def predecir_proxima_produccion():
    try:
        producciones = list(
            Produccion.objects.filter(
                estado='Finalizado'
            ).order_by('fecha_entrega').values('fecha_entrega', 'cantidad_requerida')
        )

        if len(producciones) < 2:
            return "Datos insuficientes para predicción."

        df = pd.DataFrame(producciones)
        df['fecha_num'] = pd.to_datetime(df['fecha_entrega']).map(pd.Timestamp.toordinal)
        df['cantidad_requerida'] = pd.to_numeric(df['cantidad_requerida'], errors='coerce').fillna(0)

        X = df[['fecha_num']].values
        y = df['cantidad_requerida'].values

        modelo = LinearRegression()
        modelo.fit(X, y)

        proxima_fecha = date.today() + timedelta(days=7)
        pred = modelo.predict([[proxima_fecha.toordinal()]])[0]

        return f"Cantidad estimada para {proxima_fecha}: {pred:.0f} unidades."

    except Exception as e:
        return f"No se pudo calcular la predicción: {str(e)}"


def detectar_vencimientos_lotes():
    hoy = date.today()
    alertas = []

    lotes = Lote.objects.filter(
        fecha_vencimiento__lte=hoy + timedelta(days=14)
    ).order_by('fecha_vencimiento')

    for lote in lotes:
        dias = (lote.fecha_vencimiento - hoy).days
        if dias < 0:
            alertas.append(f"🚨 Lote {lote.codigo_lote} venció hace {abs(dias)} día(s).")
        elif dias == 0:
            alertas.append(f"🚨 Lote {lote.codigo_lote} vence HOY.")
        else:
            alertas.append(f"⚠️ Lote {lote.codigo_lote} vence en {dias} día(s) ({lote.fecha_vencimiento}).")

    if not alertas:
        alertas.append("✅ No hay lotes próximos a vencer en los próximos 14 días.")

    return alertas


def detectar_retrasos_exportaciones():
    hoy = date.today()
    alertas = []

    retrasadas = Exportacion.objects.filter(
        estado='Pendiente',
        fecha_envio__lt=hoy
    ).order_by('fecha_envio')

    for exp in retrasadas:
        dias = (hoy - exp.fecha_envio).days
        alertas.append(
            f"🚨 Exportación a {exp.destino} ({exp.pais}) lleva {dias} día(s) de retraso "
            f"(fecha envío: {exp.fecha_envio})."
        )

    if not alertas:
        alertas.append("✅ No hay exportaciones retrasadas.")

    return alertas


def analizar_rendimiento():
    try:
        from django.db.models import Count

        resultado = (
            Produccion.objects.filter(estado='Finalizado')
            .values('empleado_responsable__nombre')
            .annotate(total=Count('id'))
            .order_by('-total')
            .first()
        )

        if resultado:
            return {
                'mejor_empleado':    resultado['empleado_responsable__nombre'],
                'producciones_mejor': resultado['total'],
            }
        return {
            'mejor_empleado':    'Sin datos',
            'producciones_mejor': 0,
        }

    except Exception:
        return {
            'mejor_empleado':    'Sin datos',
            'producciones_mejor': 0,
        }


def predecir_exportaciones():
    try:
        exportaciones = list(
            Exportacion.objects.order_by('fecha_envio').values('fecha_envio', 'estado')
        )

        if len(exportaciones) < 2:
            return "Datos insuficientes para predicción de exportaciones."

        df = pd.DataFrame(exportaciones)
        df['fecha_num'] = pd.to_datetime(df['fecha_envio']).map(pd.Timestamp.toordinal)
        df['es_enviado'] = (df['estado'] == 'Enviado').astype(int)

        X = df[['fecha_num']].values
        y = df['es_enviado'].values

        modelo = LinearRegression()
        modelo.fit(X, y)

        proxima = date.today() + timedelta(days=30)
        pred = modelo.predict([[proxima.toordinal()]])[0]
        prob = max(0, min(1, pred)) * 100

        return f"Probabilidad estimada de exportación exitosa en los próximos 30 días: {prob:.1f}%."

    except Exception as e:
        return f"No se pudo calcular la predicción de exportaciones: {str(e)}"


def detectar_anomalias():
    alertas = []
    try:
        producciones = list(
            Produccion.objects.filter(
                estado='Finalizado'
            ).values('cantidad_requerida')
        )

        if len(producciones) < 5:
            return ["⚠️ Datos insuficientes para detectar anomalías (se necesitan al menos 5 producciones finalizadas)."]

        df = pd.DataFrame(producciones)
        df['cantidad_requerida'] = pd.to_numeric(df['cantidad_requerida'], errors='coerce').fillna(0)

        modelo = IsolationForest(contamination=0.1, random_state=42)
        df['anomalia'] = modelo.fit_predict(df[['cantidad_requerida']])

        n_anomalias = (df['anomalia'] == -1).sum()

        if n_anomalias > 0:
            alertas.append(f"🔍 Se detectaron {n_anomalias} producción(es) con cantidades inusuales.")
        else:
            alertas.append("✅ No se detectaron anomalías en las cantidades de producción.")

    except Exception as e:
        alertas.append(f"No se pudo ejecutar análisis de anomalías: {str(e)}")

    return alertas

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

        # Análisis con Pandas
        resumen = obtener_resumen_empresa()
        alertas = detectar_alertas()

        # Predicción con Scikit-Learn
        prediccion = predecir_proxima_produccion()
        alertas_lotes = detectar_vencimientos_lotes()
        alertas_exportaciones = (detectar_retrasos_exportaciones())
        rendimiento = analizar_rendimiento()
        pred_exportaciones = (predecir_exportaciones())
        anomalias = detectar_anomalias()
        contexto = f"""
Eres un asistente experto en gestión de producción de chocolate llamado ChocoBot.
========================
RENDIMIENTO
========================

- Mejor empleado:
{rendimiento.get('mejor_empleado', 'N/A')}

- Producciones realizadas:
{rendimiento.get('producciones_mejor', 0)}

========================
PREDICCIÓN EXPORTACIONES
========================

- Exportaciones futuras estimadas:
{pred_exportaciones}

========================
ALERTAS LOTES
========================

{chr(10).join(alertas_lotes)}

========================
ALERTAS EXPORTACIONES
========================

{chr(10).join(alertas_exportaciones)}

========================
ANOMALÍAS
========================

{chr(10).join(anomalias)}
IMPORTANTE:
- Responde siempre en español.
- Sé claro, profesional y práctico.
- Usa los datos reales suministrados.
- Si detectas riesgos, explícalos.
- Si detectas oportunidades de mejora, menciónalas.
- Proporciona recomendaciones concretas.

========================
DATOS ACTUALES
========================

- Empleados activos: {empleados_activos}
- Empleados suspendidos: {empleados_suspendidos}
- Producciones en proceso: {producciones_proceso}
- Producciones finalizadas: {producciones_finalizadas}
- Exportaciones pendientes: {exportaciones_pendientes}
- Total de lotes: {total_lotes}
- Total de asignaciones: {total_asignaciones}
- Bitácoras pendientes de revisión: {bitacoras_pendientes}
- Próxima producción estimada: {prediccion}

========================
ANÁLISIS INTELIGENTE
========================

- Empleados activos detectados: {resumen['empleados_activos']}
- Empleados suspendidos detectados: {resumen['empleados_suspendidos']}
- Producciones en proceso detectadas: {resumen['producciones_proceso']}
- Producciones finalizadas detectadas: {resumen['producciones_finalizadas']}
- Exportaciones pendientes detectadas: {resumen['exportaciones_pendientes']}
- Total de lotes detectados: {resumen['total_lotes']}
prediccion = predecir_proxima_produccion()

========================
ALERTAS DETECTADAS
========================

{chr(10).join(['- ' + alerta for alerta in alertas]) if alertas else '- No se detectaron alertas importantes.'}

========================
INSTRUCCIONES PARA LA IA
========================

Analiza la situación actual de la empresa.

Cuando sea posible:
1. Identifica fortalezas.
2. Identifica riesgos.
3. Identifica cuellos de botella.
4. Propón mejoras operativas.
5. Sugiere acciones para mejorar la producción.
6. Sugiere acciones para mejorar las exportaciones.
7. Sugiere acciones para mejorar la gestión de empleados.

Pregunta del usuario:

{pregunta}
        """

        try:
            api_key = os.getenv("GEMINI_API_KEY")

            if not api_key:
                return JsonResponse(
                    {'error': 'API key de Gemini no configurada.'},
                    status=500
                )

            cliente = genai.Client(api_key=api_key)

            respuesta = None

            for intento in range(3):
                try:
                    respuesta = cliente.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=contexto
                    )
                    break

                except Exception as e:

                    if "503" in str(e) and intento < 2:
                        time.sleep(5)
                        continue

                    raise e

            return JsonResponse({
                'respuesta': respuesta.text
            })

        except Exception as e:

            error = str(e)

            if "503" in error:
                return JsonResponse({
                    'error': (
                        'La IA está temporalmente ocupada debido a una alta '
                        'demanda. Intenta nuevamente en unos segundos.'
                    )
                }, status=503)

            return JsonResponse({
                'error': f'Error al consultar la IA: {error}'
            }, status=500)

    return JsonResponse({
        'error': 'Método no permitido.'
    }, status=405)
