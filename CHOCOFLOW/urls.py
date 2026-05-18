from django.contrib import admin
from django.urls import path
from myApp import views  # ← importar el módulo completo

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('login/', views.login_usuario, name='login'),
    path('registro/', views.registro, name='registro'),
    

    # EMPLEADOS
    path('empleados/', views.empleados, name='empleados'),
    path('empleados/guardar/', views.guardar_empleado, name='guardar_empleado'),
    path('empleados/inactivar/<int:id>/', views.inactivar_empleado, name='inactivar_empleado'),
    path('empleados/reporte/', views.generar_reporte_empleados, name='reporte_empleados'),
    
    # ASIGNACIONES
    path('asignaciones/', views.asignaciones, name='asignaciones'),
    path('asignaciones/guardar/', views.guardar_asignacion, name='guardar_asignacion'),
    path('asignaciones/eliminar/<int:id>/', views.eliminar_asignacion, name='eliminar_asignacion'),
    
    #EXPORTACIONES
    path('exportaciones/',views.gestionar_exportaciones, name='gestionar_exportaciones'),
    path('exportaciones/guardar/',views.guardar_exportacion,name='guardar_exportacion'),
    path('exportaciones/inactivar/<int:id>/',views.inactivar_exportacion,name='inactivar_exportacion'),
    path('exportaciones/reporte/',views.generar_reporte_exportaciones,name='reporte_exportaciones'),
    
    #LOTES
    # Lotes
    path('lotes/',views.gestionar_lotes,name='gestionar_lotes'),
    path('lotes/guardar/',views.guardar_lote,name='guardar_lote'),
    path('lotes/eliminar/<int:id>/',views.eliminar_lote,name='eliminar_lote'),
    path('lotes/reporte/',views.generar_reporte_lotes,name='reporte_lotes'),

    #DASHBOARD SUPERVISOR
    # Dashboard principal del supervisor
    path('supervisor/', views.dashboard_supervisor, name='dashboard_supervisor'),
    
    
]
