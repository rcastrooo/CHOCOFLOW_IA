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
        correo   = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        # Validaciones básicas
        if not correo or not password:
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'auth/login.html')

        import re
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', correo):
            messages.error(request, "El correo no tiene un formato válido.")
            return render(request, 'auth/login.html')

        # Buscar el User de Django por email
        try:
            user_obj = User.objects.get(email=correo)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None

        if user:
            login(request, user)

            # Guardar el perfil personalizado en sesión
            try:
                perfil = Usuario.objects.get(email=correo)
                request.session['usuario_id'] = perfil.id
                request.session['usuario_rol'] = perfil.rol
                messages.success(request, f"Bienvenido, {perfil.nombre}")

                # ── Redirigir según el rol ──
                if perfil.rol == 'Administrador':
                    return redirect('dashboard_administrador')  # cambia por tu url real
                elif perfil.rol == 'Supervisor':
                    return redirect('dashboard_supervisor')     # cambia por tu url real
                else:
                    return redirect('index')

            except Usuario.DoesNotExist:
                messages.warning(request, "Sesión iniciada pero sin perfil asignado.")
                return redirect('index')

        else:
            messages.error(request, "Correo o contraseña incorrectos.")

    return render(request, 'auth/login.html')

# Importación de modelos actualizados
from .models import (
    Usuario, Turno, EmpTurno, Asignacion,
    Produccion, Lote, Exportacion,BitacoraProduccion
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
    total_bitacora = BitacoraProduccion.objects.count()

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

