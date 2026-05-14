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
import json
import re

from .models import (
    Usuario,
    Empleado,
    Turno,
    EmpTurno,
    Asignacion,
    Produccion,
    Lote,
    Exportacion
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
        if rol == 'admin':
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

                if rol == 'admin':
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

    datos = [['Cédula', 'Nombre', 'Email', 'Estado']]
    for emp in lista:
        datos.append([emp.cedula, emp.nombre, emp.email, emp.estado])

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
    lista = Asignacion.objects.select_related('empleado', 'turno', 'asignado_por').all()

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

        asignacion.save()
        messages.success(request, "Asignación guardada correctamente.")

    return redirect('asignaciones')


@login_required(login_url='login')
def eliminar_asignacion(request, id):
    asignacion = get_object_or_404(Asignacion, id=id)
    asignacion.delete()
    messages.success(request, "Asignación eliminada.")
    return redirect('asignaciones')