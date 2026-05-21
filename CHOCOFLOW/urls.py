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

    # EMPLEADOS
    path('empleados/', views.empleados, name='empleados'),
    path('empleados/guardar/', views.guardar_empleado, name='guardar_empleado'),
    path('empleados/inactivar/<int:id>/', views.inactivar_empleado, name='inactivar_empleado'),
    path('empleados/reporte/', views.generar_reporte_empleados, name='reporte_empleados'),

    # TURNOS
    path('turnos/', views.turnos, name='turnos'),
    path('turnos/guardar-rotacion/', views.guardar_rotacion, name='guardar_rotacion'),
    path('turnos/eliminar-rotacion/<int:id>/', views.eliminar_rotacion, name='eliminar_rotacion'),
    path('turnos/reporte/', views.generar_reporte_turnos, name='reporte_turnos'),

    # ROTACION TURNOS
    path('rotacion/', views.rotacion_turnos, name='rotacion_turnos'),
    path('rotacion/reporte/', views.generar_reporte_rotacion, name='reporte_rotacion'),

    # SOLICITUDES
    path('solicitudes/', views.solicitudes, name='solicitudes'),
    path('solicitudes/guardar/', views.guardar_solicitud, name='guardar_solicitud'),
    path('solicitudes/revisar/<int:id>/', views.revisar_solicitud, name='revisar_solicitud'),
    path('solicitudes/reporte/', views.generar_reporte_solicitudes, name='reporte_solicitudes'),

    # ASIGNACIONES
    path('asignaciones/', views.asignaciones, name='asignaciones'),
    path('asignaciones/guardar/', views.guardar_asignacion, name='guardar_asignacion'),
    path('asignaciones/inactivar/<int:id>/', views.inactivar_asignacion, name='inactivar_asignacion'),
    path('asignaciones/reporte/', views.generar_reporte_asignaciones, name='reporte_asignaciones'),

    # PRODUCCION
    path('producciones/', views.producciones, name='producciones'),
    path('producciones/guardar/', views.guardar_produccion, name='guardar_produccion'),
    path('producciones/inactivar/<int:id>/', views.inactivar_produccion, name='inactivar_produccion'),
    path('producciones/reporte/', views.generar_reporte_producciones, name='reporte_producciones'),

    # EXPORTACIONES
    path('exportaciones/', views.gestionar_exportaciones, name='gestionar_exportaciones'),
    path('exportaciones/guardar/', views.guardar_exportacion, name='guardar_exportacion'),
    path('exportaciones/inactivar/<int:id>/', views.inactivar_exportacion, name='inactivar_exportacion'),
    path('exportaciones/reporte/', views.generar_reporte_exportaciones, name='reporte_exportaciones'),

    # LOTES
    path('lotes/', views.gestionar_lotes, name='gestionar_lotes'),
    path('lotes/guardar/', views.guardar_lote, name='guardar_lote'),
    path('lotes/eliminar/<int:id>/', views.eliminar_lote, name='eliminar_lote'),
    path('lotes/reporte/', views.generar_reporte_lotes, name='reporte_lotes'),
    

    # SOLICITUDES
    path('solicitudes/', views.solicitudes, name='solicitudes'),
    path('solicitudes/guardar/', views.guardar_solicitud, name='guardar_solicitud'),
    path('solicitudes/revisar/<int:id>/', views.revisar_solicitud, name='revisar_solicitud'),
    path('solicitudes/reporte/pdf/', views.generar_reporte_solicitudes,name='generar_reporte_solicitudes'),

    # BITACORA
    path('bitacoras/', views.bitacoras, name='bitacoras'),
    path('bitacoras/guardar/', views.guardar_bitacora, name='guardar_bitacora'),
    path('bitacoras/revisar/<int:id>/', views.revisar_bitacora, name='revisar_bitacora'),
    path('bitacoras/reporte/', views.generar_reporte_bitacoras, name='reporte_bitacoras'),
]