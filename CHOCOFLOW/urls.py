from django.contrib import admin
from django.urls import path
from myApp import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.index, name='index'),
    path('login/', views.login_usuario, name='login'),
    path('registro/', views.registro, name='registro'),
    path('logout/', views.cerrar_sesion, name='logout'),

    # DASHBOARDS
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/ia/', views.consultar_ia, name='consultar_ia'),
    path('supervisor/', views.dashboard_supervisor, name='dashboard_supervisor'),
    path('supervisor/stats/', views.api_stats_supervisor, name='api_stats_supervisor'),

    # SUPERVISORES
    path('supervisores/', views.gestionar_supervisores, name='gestionar_supervisores'),
    path('supervisores/turno/<int:supervisor_id>/', views.asignar_turno_supervisor, name='asignar_turno_supervisor'),
    path('supervisores/editar/', views.editar_supervisor, name='editar_supervisor'),
    path('supervisores/inactivar/<int:supervisor_id>/', views.inactivar_supervisor, name='inactivar_supervisor'),
    path('supervisores/carga-masiva/', views.carga_masiva_supervisores, name='carga_masiva_supervisores'),
    path('supervisores/reporte/', views.reporte_supervisores, name='reporte_supervisores'),

    # EMPLEADOS
    path('empleados/', views.empleados, name='empleados'),
    path('empleados/guardar/', views.guardar_empleado, name='guardar_empleado'),
    path('empleados/inactivar/<int:id>/', views.inactivar_empleado, name='inactivar_empleado'),
    path('empleados/reporte/', views.generar_reporte_empleados, name='reporte_empleados'),
    path('empleados/supervisor/', views.empleados_supervisor, name='empleados_supervisor'),

    # TURNOS
    path('turnos/', views.turnos, name='turnos'),
    path('turnos/guardar-rotacion/', views.guardar_rotacion, name='guardar_rotacion'),
    path('turnos/eliminar-rotacion/<int:id>/', views.eliminar_rotacion, name='eliminar_rotacion'),
    path('turnos/reporte/', views.generar_reporte_turnos, name='reporte_turnos'),
    path('turnos/supervisor/', views.turnos_supervisor, name='turnos_supervisor'),

    # ROTACION TURNOS
    path('rotacion/', views.rotacion_turnos, name='rotacion_turnos'),
    path('rotacion/reporte/', views.generar_reporte_rotacion, name='reporte_rotacion'),

    # SOLICITUDES
    path('solicitudes/', views.solicitudes, name='solicitudes'),
    path('solicitudes/guardar/', views.guardar_solicitud, name='guardar_solicitud'),
    path('solicitudes/revisar/<int:id>/', views.revisar_solicitud, name='revisar_solicitud'),
    # Dos names para el reporte: el nuestro y el que usa el template
    path('solicitudes/reporte/', views.generar_reporte_solicitudes, name='reporte_solicitudes'),
    path('solicitudes/reporte/pdf/', views.generar_reporte_solicitudes, name='generar_reporte_solicitudes'),

    # ASIGNACIONES
    path('asignaciones/', views.asignaciones, name='asignaciones'),
    path('asignaciones/guardar/', views.guardar_asignacion, name='guardar_asignacion'),
    path('asignaciones/inactivar/<int:id>/', views.inactivar_asignacion, name='inactivar_asignacion'),
    path('asignaciones/reporte/', views.generar_reporte_asignaciones, name='reporte_asignaciones'),
    path('supervisor/asignaciones/', views.asignaciones_supervisor, name='asignaciones_supervisor'),
    path('supervisor/asignaciones/guardar/', views.guardar_asignacion_supervisor, name='guardar_asignacion_supervisor'),

    # PRODUCCION
    path('producciones/', views.producciones, name='producciones'),
    path('producciones/guardar/', views.guardar_produccion, name='guardar_produccion'),
    path('producciones/inactivar/<int:id>/', views.inactivar_produccion, name='inactivar_produccion'),
    path('producciones/reporte/', views.generar_reporte_producciones, name='reporte_producciones'),
    path('produccion/supervisor/', views.producciones_supervisor, name='producciones_supervisor'),
    path('guardar-produccion-supervisor/', views.guardar_produccion_supervisor, name='guardar_produccion_supervisor'),

    # EXPORTACIONES — sin select_related('creado_por') porque el modelo no tiene ese campo
    path('exportaciones/', views.gestionar_exportaciones, name='gestionar_exportaciones'),
    path('exportaciones/guardar/', views.guardar_exportacion, name='guardar_exportacion'),
    path('exportaciones/inactivar/<int:id>/', views.inactivar_exportacion, name='inactivar_exportacion'),
    path('exportaciones/reporte/', views.generar_reporte_exportaciones, name='reporte_exportaciones'),
    path('supervisor/exportaciones/', views.exportaciones_supervisor, name='exportaciones_supervisor'),

    # LOTES
    path('lotes/', views.gestionar_lotes, name='gestionar_lotes'),
    path('lotes/guardar/', views.guardar_lote, name='guardar_lote'),
    path('lotes/eliminar/<int:id>/', views.eliminar_lote, name='eliminar_lote'),
    path('lotes/reporte/', views.generar_reporte_lotes, name='reporte_lotes'),
    path('supervisor/lotes/', views.lotes_supervisor, name='lotes_supervisor'),

    # BITACORA
    path('bitacora/crear/', views.bitacora_supervisor, name='bitacora_supervisor'),
    path('bitacora/mis-bitacoras/', views.listar_bitacoras_supervisor, name='listar_bitacoras_supervisor'),
    path('bitacora/enviar/<int:id>/', views.enviar_bitacora, name='enviar_bitacora'),
    path('bitacora/admin/', views.listar_bitacoras, name='listar_bitacoras'),
    path('bitacora/revisar/<int:id>/', views.revisar_bitacora, name='revisar_bitacora'),
    
    #CORREOS
    path('correos/', views.correos_vista, name='correos_vista'),
    path('correos/enviar/', views.enviar_correos_masivos, name='enviar_correos_masivos'),
]