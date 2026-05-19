from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas

from io import BytesIO
from dotenv import load_dotenv # IA
import os
import json
import re
load_dotenv()
from google import genai
from .models import (
    Usuario,
    Empleado,
    Turno,
    EmpTurno,
    Asignacion,
    Produccion,
    Lote,
    Exportacion,
    Bitacora
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
# INDEX — si no hay sesión, va al login
# ========================

def index(request):
    # Si ya tiene sesión activa, llevarlo a su dashboard
    if request.user.is_authenticated:
        rol = request.session.get('rol', '').strip()
        if rol == 'Administrador':
            return redirect('dashboard')
        elif rol == 'Supervisor':
            return redirect('dashboard_supervisor')

    # Si no tiene sesión, mostrar la página de inicio normalmente
    return render(request, 'index.html')

# ========================
# LOGIN
# ========================

def login_usuario(request):

    # Si ya hay sesión activa, redirigir según rol
    if request.user.is_authenticated:
        rol = request.session.get('rol', '').strip()
        if rol == 'Administrador':
            return redirect('dashboard')
        elif rol == 'Supervisor':
            return redirect('dashboard_supervisor')

    if request.method == 'POST':

        correo   = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        # Validar campos vacíos
        if not correo or not password:
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'auth/login.html')

        # Validar formato del correo
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
            telefono=0,
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
    asignaciones             = Asignacion.objects.select_related('empleado').order_by('-id')[:5]
    producciones_recientes   = Produccion.objects.select_related('empleado_responsable').order_by('-id')[:5]

    context = {
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
        'asignaciones':             asignaciones,
        'producciones_recientes':   producciones_recientes,
    }

    return render(request, 'dashboard.html', context)

@login_required(login_url='login')
def dashboard(request):

    # Obtener datos del usuario en sesión
    usuario_id = request.session.get('usuario_id')
    usuario_nombre = 'Administrador'
    usuario_rol    = 'Administrador'

    try:
        usuario_db     = Usuario.objects.get(id=usuario_id)
        usuario_nombre = usuario_db.nombre
        usuario_rol    = usuario_db.rol
    except Usuario.DoesNotExist:
        pass

    # ... resto de variables que ya tienes ...

    context = {
        # ... todo lo que ya tienes ...
        'usuario_nombre': usuario_nombre,
        'usuario_rol':    usuario_rol,
    }

    return render(request, 'dashboard.html', context)

# =======================
# DASHBOARD SUPERVISOR
# =======================

def dashboard_supervisor(request):

    empleados_activos       = Empleado.objects.filter(estado='Activo').count()
    turnos                  = Turno.objects.count()
    producciones_proceso    = Produccion.objects.filter(estado='En Proceso').count()
    producciones_pendientes = Produccion.objects.filter(estado='Pendiente').count()
    asignaciones            = Asignacion.objects.select_related('empleado').order_by('-id')[:10]
    lotes                   = Lote.objects.order_by('-fecha_vencimiento')[:5]

    context = {
        'empleados_activos':       empleados_activos,
        'turnos':                  turnos,
        'producciones_proceso':    producciones_proceso,
        'producciones_pendientes': producciones_pendientes,
        'asignaciones':            asignaciones,
        'lotes':                   lotes,
    }

    return render(request, 'dashboard_supervisor.html', context)

# ===================
# EMPLEADOS — función única y unificada
# ===================

def empleados(request):

    query  = request.GET.get('q') or request.GET.get('busqueda')
    estado = request.GET.get('estado')

    lista = Empleado.objects.all()

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
            messages.error(request, "Sesión inválida. Inicia sesión nuevamente.")
            return redirect('login')

        try:
            usuario_perfil = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            messages.error(request, "No se encontró tu perfil de usuario.")
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
    empleado = get_object_or_404(Empleado, id=id)
    empleado.estado = 'Inactivo'
    empleado.save()
    messages.success(request, f"{empleado.nombre} fue inactivado.")
    return redirect('empleados')

# ==============================
# REPORTE PDF DE EMPLEADOS
# ==============================

def generar_reporte_empleados(request):

    lista    = Empleado.objects.all()
    busqueda = request.GET.get('busqueda')
    estado   = request.GET.get('estado')

    if busqueda:
        lista = lista.filter(nombre__icontains=busqueda)

    if estado and estado != 'Todos':
        lista = lista.filter(estado=estado)

    buffer = BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos   = getSampleStyleSheet()

    elementos.append(Paragraph("Reporte de Empleados - ChocoFlow", estilos['Title']))
    elementos.append(Spacer(1, 20))

    datos = [['Cédula', 'Nombre', 'Email', 'Telefono', 'Estado']]
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
# ASIGNACIONES
# ===================

def asignaciones(request):

    query = request.GET.get('q')
    lista = Asignacion.objects.select_related(
        'empleado', 'turno', 'asignado_por'
    ).filter(empleado__estado='Activo')

    if query:
        lista = lista.filter(
            Q(tarea__icontains=query) |
            Q(empleado__nombre__icontains=query)
        )

    empleados = Empleado.objects.filter(estado='Activo')
    turnos    = Turno.objects.all()

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
            messages.error(request, "Sesión inválida. Inicia sesión nuevamente.")
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

        if not tarea or not fecha or not emp_id or not turno_id:
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('asignaciones')

        asignacion.tarea            = tarea
        asignacion.fecha_asignacion = fecha
        asignacion.empleado         = get_object_or_404(Empleado, id=emp_id)
        asignacion.turno            = get_object_or_404(Turno, id=turno_id)
        asignacion.asignado_por     = usuario_perfil
        asignacion.estado           = 'Activo'

        asignacion.save()
        messages.success(request, "Asignación guardada correctamente.")

    return redirect('asignaciones')


@login_required(login_url='login')
def inactivar_asignacion(request, id):
    asignacion = get_object_or_404(Asignacion, id=id)
    asignacion.estado = 'Inactivo'
    asignacion.save()
    messages.success(request, "Asignación inactivada.")
    return redirect('asignaciones')

# ==============================
# REPORTE PDF DE ASIGNACIONES
# ==============================

@login_required(login_url='login')
def generar_reporte_asignaciones(request):

    lista  = Asignacion.objects.select_related('empleado', 'turno', 'asignado_por').all()
    query  = request.GET.get('q')

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

    datos = [['Tarea', 'Empleado', 'Turno', 'Fecha', 'Asignado por']]
    for a in lista:
        datos.append([
            a.tarea,
            a.empleado.nombre,
            a.turno.horario,
            str(a.fecha_asignacion),
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
# TURNOS
# ===================

@login_required(login_url='login')
def turnos(request):

    fecha_filtro = request.GET.get('fecha')
    lista = Turno.objects.select_related('creado_por').prefetch_related('empturno_set__empleado').order_by('-id')

    if fecha_filtro:
        lista = lista.filter(fecha=fecha_filtro)

    empleados = Empleado.objects.filter(estado='Activo')

    return render(request, 'modulos/turnos/turnos.html', {
        'turnos':    lista,
        'empleados': empleados
    })


@login_required(login_url='login')
def guardar_turno(request):

    if request.method == 'POST':

        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida.")
            return redirect('login')

        try:
            usuario = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            messages.error(request, "Usuario no encontrado.")
            return redirect('login')

        turno_id     = request.POST.get('id')
        fecha        = request.POST.get('fecha')
        horario      = request.POST.get('horario')
        empleado_ids = request.POST.getlist('empleado_ids')  # ← corregido

        if not fecha or not horario:
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('turnos')

        # Crear o editar
        if turno_id:
            turno = get_object_or_404(Turno, id=turno_id)
            turno.fecha   = fecha
            turno.horario = horario
            turno.save()
            # Actualizar empleados
            EmpTurno.objects.filter(turno=turno).delete()
        else:
            turno = Turno.objects.create(
                fecha=fecha,
                horario=horario,
                creado_por=usuario
            )

        # Asignar empleados
        for emp_id in empleado_ids:
            try:
                empleado = Empleado.objects.get(id=emp_id)
                EmpTurno.objects.create(empleado=empleado, turno=turno)
            except Empleado.DoesNotExist:
                pass

        messages.success(request, "Turno guardado correctamente.")

    return redirect('turnos')


@login_required(login_url='login')
def inactivar_turno(request, id):
    turno = get_object_or_404(Turno, id=id)
    EmpTurno.objects.filter(turno=turno).delete()
    turno.delete()
    messages.success(request, "Turno eliminado correctamente.")
    return redirect('turnos')

# ==============================
# REPORTE PDF DE TURNOS
# ==============================

@login_required(login_url='login')
def generar_reporte_turnos(request):

    lista = Turno.objects.select_related('creado_por').prefetch_related('empturno_set__empleado').all()
    fecha = request.GET.get('fecha')

    if fecha:
        lista = lista.filter(fecha=fecha)

    buffer    = BytesIO()
    doc       = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos   = getSampleStyleSheet()

    elementos.append(Paragraph("Reporte de Turnos - ChocoFlow", estilos['Title']))
    elementos.append(Spacer(1, 20))

    datos = [['Fecha', 'Horario', 'Empleados', 'Creado por']]
    for t in lista:
        empleados_turno = ', '.join([
            rel.empleado.nombre for rel in t.empturno_set.all()
        ]) or 'Sin empleados'

        datos.append([
            str(t.fecha),
            t.horario,
            empleados_turno,
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



# ==============================
# LOGICA DE EXPORTACIONES
# ==============================
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Exportacion, Usuario

@login_required(login_url='login')
def gestionar_exportaciones(request):
    q      = request.GET.get('q', '')
    estado = request.GET.get('estado', '')

    exportaciones = Exportacion.objects.select_related('creado_por').all()

    if q:
        # Filtra solo por destino (es nacional, no hay país)
        exportaciones = exportaciones.filter(destino__icontains=q)

    if estado:
        exportaciones = exportaciones.filter(estado=estado)

    return render(request, 'modulos/exportaciones/exportaciones.html', {
        'exportaciones': exportaciones,
        'q': q,
        'estado_filtro': estado,
    })


@login_required(login_url='login')
def guardar_exportacion(request):
    if request.method == 'POST':

        # Obtener el Usuario personalizado desde la sesión (igual que en empleados)
        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida. Inicia sesión nuevamente.")
            return redirect('login')

        try:
            usuario_perfil = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            messages.error(request, "No se encontró tu perfil de usuario.")
            return redirect('login')

        id            = request.POST.get('id')
        destino       = request.POST.get('destino')
        fecha_envio   = request.POST.get('fecha_envio')
        fecha_entrega = request.POST.get('fecha_entrega')
        estado        = request.POST.get('estado')

        # Validación de fechas
        if fecha_entrega < fecha_envio:
            messages.error(request, 'La fecha de entrega no puede ser anterior a la de envío.')
            return redirect('gestionar_exportaciones')

        if id:  # ✏️ Editar
            exp               = get_object_or_404(Exportacion, pk=id)
            exp.destino       = destino
            exp.fecha_envio   = fecha_envio
            exp.fecha_entrega = fecha_entrega
            exp.estado        = estado
            exp.save()
            messages.success(request, 'Exportación actualizada correctamente.')

        else:   # ➕ Crear
            Exportacion.objects.create(
                destino       = destino,
                fecha_envio   = fecha_envio,
                fecha_entrega = fecha_entrega,
                estado        = estado,
                creado_por    = usuario_perfil,  # ← igual que en guardar_empleado
            )
            messages.success(request, 'Exportación creada correctamente.')

    return redirect('gestionar_exportaciones')


@login_required(login_url='login')
def inactivar_exportacion(request, id):
    exp        = get_object_or_404(Exportacion, pk=id)
    exp.estado = 'Cancelado'  # No borra, solo cambia el estado
    exp.save()
    messages.success(request, 'Exportación cancelada correctamente.')
    return redirect('gestionar_exportaciones')


@login_required(login_url='login')
def generar_reporte_exportaciones(request):

    exportaciones = Exportacion.objects.select_related('creado_por').all()

    busqueda = request.GET.get('busqueda')
    estado   = request.GET.get('estado')

    if busqueda:
        exportaciones = exportaciones.filter(destino__icontains=busqueda)

    if estado and estado != "Todos":
        exportaciones = exportaciones.filter(estado=estado)

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter)

    elementos = []
    estilos   = getSampleStyleSheet()

    titulo = Paragraph("Reporte de Exportaciones - ChocoFlow", estilos['Title'])
    elementos.append(titulo)
    elementos.append(Spacer(1, 20))

    datos = [['Destino', 'Fecha Envío', 'Fecha Entrega', 'Estado', 'Creado por']]

    for exp in exportaciones:
        datos.append([
            exp.destino,
            str(exp.fecha_envio),
            str(exp.fecha_entrega),
            exp.estado,
            str(exp.creado_por),
        ])

    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#603C1C')),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('GRID',       (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_exportaciones.pdf"'
    response.write(pdf)
    return response

# ==============================
# LOGICA DE LOTES
# ==============================
@login_required(login_url='login')
def gestionar_lotes(request):

    # Lee el filtro de búsqueda que viene de la URL
    q = request.GET.get('q', '')

    # Trae todos los lotes junto con su producción y exportación relacionadas
    lotes = Lote.objects.select_related('produccion', 'exportacion').all()

    # Si escribió algo en el buscador, filtra por código de lote
    if q:
        lotes = lotes.filter(codigo_lote__icontains=q)

    # Trae producciones y exportaciones para los selectores del modal
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

        # Obtener el Usuario personalizado desde la sesión
        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, "Sesión inválida. Inicia sesión nuevamente.")
            return redirect('login')

        # Recoge los datos enviados desde el formulario del modal
        lote_id          = request.POST.get('id')
        codigo_lote      = request.POST.get('codigo_lote')
        cantidad         = request.POST.get('cantidad')
        fecha_produccion = request.POST.get('fecha_produccion')
        fecha_vencimiento= request.POST.get('fecha_vencimiento')
        produccion_id    = request.POST.get('produccion_id')
        exportacion_id   = request.POST.get('exportacion_id')

        # Validación: todos los campos son obligatorios
        if not all([codigo_lote, cantidad, fecha_produccion, fecha_vencimiento, produccion_id, exportacion_id]):
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('gestionar_lotes')

        # Validación de fechas
        if fecha_vencimiento < fecha_produccion:
            messages.error(request, "La fecha de vencimiento no puede ser anterior a la de producción.")
            return redirect('gestionar_lotes')

        # Trae los objetos relacionados desde la BD
        produccion  = get_object_or_404(Produccion,  pk=produccion_id)
        exportacion = get_object_or_404(Exportacion, pk=exportacion_id)

        if lote_id:  # ✏️ Editar lote existente
            lote                  = get_object_or_404(Lote, pk=lote_id)
            lote.codigo_lote      = codigo_lote
            lote.cantidad         = cantidad
            lote.fecha_produccion = fecha_produccion
            lote.fecha_vencimiento= fecha_vencimiento
            lote.produccion       = produccion
            lote.exportacion      = exportacion
            lote.save()
            messages.success(request, f"Lote '{codigo_lote}' actualizado correctamente.")

        else:  # ➕ Crear lote nuevo
            # Verifica que el código de lote no esté duplicado
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

    # Busca el lote o retorna 404 si no existe
    lote = get_object_or_404(Lote, pk=id)
    codigo = lote.codigo_lote  # Guarda el código antes de eliminar para el mensaje
    lote.delete()              # Elimina el registro de la BD definitivamente
    messages.success(request, f"Lote '{codigo}' eliminado correctamente.")
    return redirect('gestionar_lotes')


@login_required(login_url='login')
def generar_reporte_lotes(request):

    # Trae todos los lotes con sus relaciones
    lotes = Lote.objects.select_related('produccion', 'exportacion').all()

    # Aplica filtro de búsqueda si viene en la URL
    busqueda = request.GET.get('busqueda', '')
    if busqueda:
        lotes = lotes.filter(codigo_lote__icontains=busqueda)

    # Crea el PDF en memoria
    buffer = BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=letter)

    elementos = []
    estilos   = getSampleStyleSheet()

    # Título del reporte
    titulo = Paragraph("Reporte de Lotes - ChocoFlow", estilos['Title'])
    elementos.append(titulo)
    elementos.append(Spacer(1, 20))

    # Primera fila = encabezados de la tabla
    datos = [['Código Lote', 'Cantidad', 'Fecha Producción', 'Fecha Vencimiento', 'Producción', 'Exportación']]

    # Una fila por cada lote
    for lote in lotes:
        datos.append([
            lote.codigo_lote,
            str(lote.cantidad),
            str(lote.fecha_produccion),
            str(lote.fecha_vencimiento),
            str(lote.produccion),   # usa el __str__ de Produccion
            str(lote.exportacion),  # usa el __str__ de Exportacion
        ])

    # Construye y estiliza la tabla
    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#603C1C')), # encabezado chocolate
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),               # texto blanco
        ('GRID',       (0,0), (-1,-1), 1, colors.black),           # bordes negros
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),           # negrita en encabezado
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),              # fondo beige en datos
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    # Extrae el PDF y lo manda al navegador como descarga
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_lotes.pdf"'
    response.write(pdf)
    return response

##dashboard supervisor
def dashboard_supervisor(request):
    """
    Vista principal del supervisor.
    Consulta el conteo de cada módulo y los envía
    al template para mostrarlos en las tarjetas de resumen.
    """

    # Total de empleados registrados en el sistema
    total_empleados = Empleado.objects.count()

    # Solo los empleados que tienen estado 'Activo'
    empleados_activos = Empleado.objects.filter(estado='Activo').count()

    # Total de turnos registrados
    total_turnos = Turno.objects.count()

    # Total de asignaciones de tareas registradas
    total_asignaciones = Asignacion.objects.count()

    # Solo las exportaciones que aún están en estado 'Pendiente'
    exportaciones_pendientes = Exportacion.objects.filter(estado='Pendiente').count()

    # Total de lotes registrados
    total_lotes = Lote.objects.count()

    # Total de entradas registradas en la bitácora de producción
    total_bitacora = Bitacora.objects.count()

    # Se empaquetan todos los datos en un diccionario
    # para que el template pueda acceder a ellos con {{ variable }}
    context = {
        'total_empleados':          total_empleados,
        'empleados_activos':        empleados_activos,
        'total_turnos':             total_turnos,
        'total_asignaciones':       total_asignaciones,
        'exportaciones_pendientes': exportaciones_pendientes,
        'total_lotes':              total_lotes,
        'total_bitacora':           total_bitacora,
    }

    return render(request, 'dashboardsuper.html', context)


# ===================
# PRODUCCION
# ===================

@login_required(login_url='login')
def producciones(request):

    query  = request.GET.get('q')
    estado = request.GET.get('estado')

    lista = Produccion.objects.select_related(
        'empleado_responsable', 'creado_por'
    ).all()

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

        produccion_id = request.POST.get('id')
        produccion    = get_object_or_404(Produccion, id=produccion_id) if produccion_id else Produccion()

        producto             = request.POST.get('producto', '').strip()
        ingredientes         = request.POST.get('ingredientes', '').strip()
        cantidad_planificada = request.POST.get('cantidad_planificada', '').strip()
        cantidad_producida   = request.POST.get('cantidad_producida', '').strip()
        fecha_inicio         = request.POST.get('fecha_inicio', '').strip()
        fecha_fin            = request.POST.get('fecha_fin', '').strip()
        fecha_entrega        = request.POST.get('fecha_entrega', '').strip()
        fecha_limite         = request.POST.get('fecha_limite', '').strip()
        estado               = request.POST.get('estado', '').strip()
        emp_id               = request.POST.get('empleado_responsable')

        if not producto or not emp_id or not fecha_inicio or not fecha_fin:
            messages.error(request, "Los campos obligatorios no pueden estar vacíos.")
            return redirect('producciones')

        produccion.producto             = producto
        produccion.ingredientes         = ingredientes
        produccion.cantidad_planificada = cantidad_planificada
        produccion.cantidad_producida   = cantidad_producida
        produccion.fecha_inicio         = fecha_inicio
        produccion.fecha_fin            = fecha_fin
        produccion.fecha_entrega        = fecha_entrega
        produccion.fecha_limite         = fecha_limite
        produccion.estado               = estado
        produccion.empleado_responsable = get_object_or_404(Empleado, id=emp_id)
        produccion.creado_por           = usuario_perfil

        produccion.save()
        messages.success(request, "Producción guardada correctamente.")

    return redirect('producciones')


@login_required(login_url='login')
def inactivar_produccion(request, id):
    produccion = get_object_or_404(Produccion, id=id)
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

    datos = [['Producto', 'Responsable', 'Cant. Producida', 'Fecha Inicio', 'Fecha Fin', 'Estado']]
    for p in lista:
        datos.append([
            p.producto,
            p.empleado_responsable.nombre,
            p.cantidad_producida,
            str(p.fecha_inicio),
            str(p.fecha_fin),
            p.estado
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


# ========================
# ASISTENTE IA CON GEMINI
# ========================
import google.generativeai as genai 

def consultar_ia(request):

    # Verificar sesión manualmente
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

Con base en estos datos reales, responde la siguiente pregunta del administrador:
{pregunta}
        """

        try:
            # ✅ ahora
            cliente   = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            respuesta = cliente.models.generate_content(
            model="gemini-2.0-flash",
            contents=contexto
        )
            return JsonResponse({'respuesta': respuesta.text})

        except Exception as e:
            return JsonResponse({'error': f'Error al consultar la IA: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Método no permitido.'}, status=405)