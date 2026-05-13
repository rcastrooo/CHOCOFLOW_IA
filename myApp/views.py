from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib import messages



def index(request):
    return HttpResponse("Inicio")

def login_usuario(request):
    return HttpResponse("Login")

def registro(request):
    return HttpResponse("Registro")

def registro(request):

    if request.method == 'POST':

        identificacion = request.POST['identificacion'].strip()
        nombre = request.POST['nombre'].strip()
        correo = request.POST['correo'].strip()
        password = request.POST['password'].strip()
        rol = request.POST['rol']
        estado = request.POST['estado']

        # ========================
        # VALIDACIONES DE CAMPOS
        # ========================

        # Identificación: solo números, mínimo 5 dígitos
        if not identificacion.isdigit():
            messages.error(request, "La identificación solo debe contener números.")
            return redirect('registro')

        if len(identificacion) < 5:
            messages.error(request, "La identificación debe tener al menos 5 dígitos.")
            return redirect('registro')

        # Nombre: solo letras y espacios, mínimo 3 caracteres
        if not all(c.isalpha() or c.isspace() for c in nombre):
            messages.error(request, "El nombre solo debe contener letras.")
            return redirect('registro')

        if len(nombre) < 3:
            messages.error(request, "El nombre debe tener al menos 3 caracteres.")
            return redirect('registro')

        # Correo: formato válido
        import re
        patron_correo = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
        if not re.match(patron_correo, correo):
            messages.error(request, "El correo no tiene un formato válido.")
            return redirect('registro')

        # Contraseña: mínimo 8 caracteres, una mayúscula y un número
        if len(password) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
            return redirect('registro')

        if not any(c.isupper() for c in password):
            messages.error(request, "La contraseña debe tener al menos una mayúscula.")
            return redirect('registro')

        if not any(c.isdigit() for c in password):
            messages.error(request, "La contraseña debe tener al menos un número.")
            return redirect('registro')

        # Rol y estado: no pueden estar vacíos
        if not rol:
            messages.error(request, "Debes seleccionar un rol.")
            return redirect('registro')

        if not estado:
            messages.error(request, "Debes seleccionar un estado.")
            return redirect('registro')

        # ========================
        # VALIDACIONES DE BD
        # ========================

        if User.objects.filter(username=identificacion).exists():
            messages.error(request, "Esa identificación ya está registrada.")
            return redirect('registro')

        if User.objects.filter(email=correo).exists():
            messages.error(request, "Ese correo ya está registrado.")
            return redirect('registro')

        # ========================
        # CREAR USUARIO
        # ========================
        User.objects.create_user(
            username=identificacion,
            first_name=nombre,
            email=correo,
            password=password
        )

        messages.success(request, "Usuario registrado correctamente ")
        return redirect('login')

    return render(request, 'auth/registro.html')


def login_usuario(request):
    if request.method == 'POST':
        correo = request.POST['username'].strip()
        password = request.POST['password'].strip()

        # ========================
        # VALIDACIONES
        # ========================

        # Campos vacíos
        if not correo or not password:
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'auth/login.html')

        # Formato correo
        import re
        patron_correo = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
        if not re.match(patron_correo, correo):
            messages.error(request, "El correo no tiene un formato válido.")
            return render(request, 'auth/login.html')

        # ========================
        # AUTENTICACIÓN
        # ========================
        from django.contrib.auth.models import User
        try:
            user_obj = User.objects.get(email=correo)
            user = authenticate(
                request,
                username=user_obj.username,
                password=password
            )
        except User.DoesNotExist:
            user = None

        if user:
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, "Correo o contraseña incorrectos ")

    return render(request, 'auth/login.html')

# Importación de modelos actualizados
from .models import (
    Usuario, Turno, EmpTurno, Asignacion,
    Produccion, Lote, Exportacion
)

# ========================
# FUNCIÓN AUXILIAR
# ========================
def parse_body(request):
    """
    Convierte el body de la petición (JSON) a diccionario Python.
    """
    try:
        return json.loads(request.body)
    except:
        return {}


# ========================
# USUARIOS
# ========================
@csrf_exempt
def usuarios(request):
    """
    GET  -> Lista todos los usuarios
    POST -> Crea un usuario (la contraseña se encripta automáticamente en el model)
    """

    # CONSULTAR
    if request.method == "GET":
        data = list(Usuario.objects.values())
        return JsonResponse(data, safe=False)

    # CREAR
    if request.method == "POST":
        body = parse_body(request)

        usuario = Usuario.objects.create(
            nombre=body.get("nombre"),
            email=body.get("email"),
            contrasena=body.get("contrasena"),  # Se encripta en save()
            rol=body.get("rol"),
            estado=body.get("estado", "Activo")
        )

        return JsonResponse({
            "mensaje": "Usuario creado correctamente",
            "id": usuario.id
        })


# ========================
# TURNOS
# ========================
@csrf_exempt
def turnos(request):
    """
    GET  -> Lista turnos
    POST -> Crea turno
    """

    if request.method == "GET":
        data = list(Turno.objects.values())
        return JsonResponse(data, safe=False)

    if request.method == "POST":
        body = parse_body(request)

        turno = Turno.objects.create(
            fecha=body.get("fecha"),
            horario=body.get("horario"),
            hora_inicio=body.get("hora_inicio"),
            hora_fin=body.get("hora_fin")
        )

        return JsonResponse({
            "mensaje": "Turno creado",
            "id": turno.id
        })


# ===================
# LOGICA DE ASIGNACIONES
# ===================
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Asignacion, Empleado, Turno, Usuario


@login_required(login_url='login')
def asignaciones(request):

    query = request.GET.get('q')
    estado_filtro = request.GET.get('estado')

    lista = Asignacion.objects.select_related(
        'empleado', 'turno', 'asignado_por'
    ).all()

    if query:
        lista = lista.filter(
            Q(tarea__icontains=query) |
            Q(empleado__nombre__icontains=query)
        )

    # Datos para el modal
    empleados = Empleado.objects.filter(estado='Activo')
    turnos    = Turno.objects.all()

    return render(request, 'modulos/asignaciones/asignaciones.html', {
        'asignaciones': lista,
        'empleados': empleados,
        'turnos': turnos,
    })


@login_required(login_url='login')
def guardar_asignacion(request):

    if request.method == 'POST':

        # Obtener usuario de sesión
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

        if asignacion_id:
            asignacion = get_object_or_404(Asignacion, id=asignacion_id)
        else:
            asignacion = Asignacion()

        # Validaciones básicas
        tarea      = request.POST.get('tarea', '').strip()
        fecha      = request.POST.get('fecha_asignacion', '').strip()
        emp_id     = request.POST.get('empleado_id')
        turno_id   = request.POST.get('turno_id')

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
# ========================
# PRODUCCIÓN
# ========================
@csrf_exempt
def producciones(request):
    """
    GET  -> Lista producciones
    POST -> Crea producción
    """

    if request.method == "GET":
        data = list(Produccion.objects.values())
        return JsonResponse(data, safe=False)

    if request.method == "POST":
        body = parse_body(request)

        produccion = Produccion.objects.create(
            producto=body.get("producto"),
            ingredientes=body.get("ingredientes"),
            cantidad_planificada=body.get("cantidad_planificada"),
            fecha_entrega=body.get("fecha_entrega"),
            fecha_limite=body.get("fecha_limite"),
            usuario_id=body.get("usuario_id"),  # opcional
            estado="Pendiente"
        )

        return JsonResponse({
            "mensaje": "Producción creada",
            "id": produccion.id
        })


# ========================
# INICIAR PRODUCCIÓN
# ========================
def iniciar_produccion(request, id):
    """
    Cambia estado de producción a 'En Proceso'
    """
    try:
        produccion = Produccion.objects.get(id=id)
        produccion.estado = "En Proceso"
        produccion.save()

        return JsonResponse({"mensaje": "Producción iniciada"})
    except Produccion.DoesNotExist:
        return JsonResponse({"error": "Producción no encontrada"}, status=404)


# ========================
# FINALIZAR PRODUCCIÓN
# ========================
@csrf_exempt
def finalizar_produccion(request, id):
    """
    Finaliza producción y crea lote automáticamente
    """
    try:
        produccion = Produccion.objects.get(id=id)
        body = parse_body(request)

        cantidad = body.get("cantidad_producida", 0)

        # Actualizar producción
        produccion.estado = "Finalizado"
        produccion.cantidad_producida = cantidad
        produccion.save()

        # Crear lote automáticamente (trazabilidad)
        lote = Lote.objects.create(
            codigo_lote=f"LOTE-{produccion.id}",
            cantidad=cantidad,
            fecha_produccion=produccion.fecha_inicio,
            fecha_vencimiento=produccion.fecha_limite,
            produccion=produccion
        )

        return JsonResponse({
            "mensaje": "Producción finalizada",
            "lote": lote.codigo_lote
        })

    except Produccion.DoesNotExist:
        return JsonResponse({"error": "Producción no encontrada"}, status=404)


# ========================
# LOTES
# ========================
def lotes(request):
    """
    GET -> Lista lotes
    """
    data = list(Lote.objects.values())
    return JsonResponse(data, safe=False)


# ========================
# EXPORTACIONES
# ========================
@csrf_exempt
def exportaciones(request):
    """
    GET  -> Lista exportaciones
    POST -> Crea exportación
    """

    if request.method == "GET":
        data = list(Exportacion.objects.values())
        return JsonResponse(data, safe=False)

    if request.method == "POST":
        body = parse_body(request)

        exportacion = Exportacion.objects.create(
            destino=body.get("destino"),
            pais=body.get("pais"),
            estado="Pendiente"
        )

        return JsonResponse({
            "mensaje": "Exportación creada",
            "id": exportacion.id
        })


# ========================
# ENVIAR EXPORTACIÓN
# ========================
def enviar_exportacion(request, id):
    """
    Cambia estado a 'Enviado'
    """
    try:
        exportacion = Exportacion.objects.get(id=id)
        exportacion.estado = "Enviado"
        exportacion.save()

        return JsonResponse({"mensaje": "Exportación enviada"})
    except Exportacion.DoesNotExist:
        return JsonResponse({"error": "Exportación no encontrada"}, status=404)


# ========================
# CONFIRMAR ENTREGA
# ========================
def confirmar_entrega(request, id):
    """
    Cambia estado a 'Entregado'
    """
    try:
        exportacion = Exportacion.objects.get(id=id)
        exportacion.estado = "Entregado"
        exportacion.save()

        return JsonResponse({"mensaje": "Entrega confirmada"})
    except Exportacion.DoesNotExist:
        return JsonResponse({"error": "Exportación no encontrada"}, status=404)

# -------------------------------------
# =======================
# LOGICA INDEX
# =======================
from .models import Empleado, Produccion, Exportacion, Lote, Asignacion

@login_required(login_url='login')
def index(request):

    total_empleados    = Empleado.objects.filter(estado='Activo').count()
    total_producciones = Produccion.objects.count()
    total_exportaciones = Exportacion.objects.count()
    total_lotes        = Lote.objects.count()

    # Porcentajes para las barras
    emp_total  = Empleado.objects.count()
    prod_total = Produccion.objects.count()
    exp_total  = Exportacion.objects.count()
    asig_total = Asignacion.objects.count()

    return render(request, 'index.html', {
        'total_empleados':     total_empleados,
        'total_producciones':  total_producciones,
        'total_exportaciones': total_exportaciones,
        'total_lotes':         total_lotes,

        'pct_empleados':    min(int((total_empleados / emp_total * 100) if emp_total else 0), 100),
        'pct_producciones': min(int((Produccion.objects.filter(estado='Finalizado').count() / prod_total * 100) if prod_total else 0), 100),
        'pct_exportaciones':min(int((Exportacion.objects.filter(estado='Entregado').count() / exp_total * 100) if exp_total else 0), 100),
        'pct_asignaciones': min(int((asig_total / 10 * 100) if asig_total else 0), 100),

        'producciones_recientes':  Produccion.objects.select_related('empleado_responsable').order_by('-id')[:5],
        'exportaciones_recientes': Exportacion.objects.order_by('-id')[:5],
    })

# ===================
# LOGICA DE EMPLEADOS
# ===================
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required(login_url='login')
def empleados(request):
    query = request.GET.get('q')
    estado = request.GET.get('estado')

    lista = Empleado.objects.all()

    if query:
        lista = lista.filter(
            Q(nombre__icontains=query) |
            Q(email__icontains=query) |
            Q(cedula__icontains=query)
        )

    if estado:
        lista = lista.filter(estado=estado)

    return render(request, 'modulos/empleados/empleados.html', {
        'empleados': lista
    })


@login_required(login_url='login')
def guardar_empleado(request):
    if request.method == 'POST':

        # Obtener el Usuario personalizado desde la sesión
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

        if empleado_id:
            empleado = get_object_or_404(Empleado, id=empleado_id)
        else:
            empleado = Empleado()

        empleado.cedula    = request.POST.get('cedula')
        empleado.nombre    = request.POST.get('nombre')
        empleado.email     = request.POST.get('email')
        empleado.telefono  = request.POST.get('telefono')
        empleado.direccion = request.POST.get('direccion')
        empleado.estado    = request.POST.get('estado')
        empleado.creado_por = usuario_perfil   # ← ya funciona correctamente

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
# LOGICA DE REPORTE DE EMPLEADOS
# ==============================
from django.shortcuts import render
from .models import Empleado

from django.http import HttpResponse

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from io import BytesIO


def empleados(request):

    empleados = Empleado.objects.all()

    busqueda = request.GET.get('busqueda')
    estado = request.GET.get('estado')

    if busqueda:
        empleados = empleados.filter(nombre__icontains=busqueda)

    if estado and estado != "Todos":
        empleados = empleados.filter(estado=estado)

    context = {
        'empleados': empleados
    }

    return render(
        request,
        'modulos/empleados/empleados.html',
        context
    )


def generar_reporte_empleados(request):

    empleados = Empleado.objects.all()

    busqueda = request.GET.get('busqueda')
    estado = request.GET.get('estado')

    if busqueda:
        empleados = empleados.filter(nombre__icontains=busqueda)

    if estado and estado != "Todos":
        empleados = empleados.filter(estado=estado)

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter
    )

    elementos = []

    estilos = getSampleStyleSheet()

    titulo = Paragraph(
        "Reporte de Empleados - ChocoFlow",
        estilos['Title']
    )

    elementos.append(titulo)
    elementos.append(Spacer(1, 20))

    datos = [
        [
            'Cédula',
            'Nombre',
            'Email',
            'Estado'
        ]
    ]

    for emp in empleados:

        datos.append([
            emp.cedula,
            emp.nombre,
            emp.email,
            emp.estado
        ])

    tabla = Table(datos)

    tabla.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#603C1C')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),

        ('GRID', (0,0), (-1,-1), 1, colors.black),

        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),

        ('BACKGROUND', (0,1), (-1,-1), colors.beige),

    ]))

    elementos.append(tabla)

    doc.build(elementos)

    pdf = buffer.getvalue()

    buffer.close()

    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        'attachment; filename="reporte_empleados.pdf"'
    )

    response.write(pdf)

    return response