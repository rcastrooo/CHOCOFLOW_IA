from django.contrib import admin
from django.urls import path
from myApp import views  # ← importar el módulo completo

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.index, name='index'),

    path('login/', views.login_usuario, name='login'),
    path('registro/', views.registro, name='registro'),
    path('logout/', views.cerrar_sesion, name='logout'),
    
    # DASHBOARD ADMIN
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # IA EN EL DASHBOARD DEL ADMIN
    path('dashboard/ia/', views.consultar_ia, name='consultar_ia'),

    # DASHBOARD SUPERVISOR
    path('dashboard_supervisor/', views.dashboard_supervisor, name='dashboard_supervisor'),
    

    # EMPLEADOS
    path('empleados/', views.empleados, name='empleados'),
    path('empleados/guardar/', views.guardar_empleado, name='guardar_empleado'),
    path('empleados/inactivar/<int:id>/', views.inactivar_empleado, name='inactivar_empleado'),
    path('empleados/reporte/', views.generar_reporte_empleados, name='reporte_empleados'),

    # ASIGNACIONES
    path('asignaciones/', views.asignaciones, name='asignaciones'),
    path('asignaciones/guardar/', views.guardar_asignacion, name='guardar_asignacion'),
    path('asignaciones/eliminar/<int:id>/', views.eliminar_asignacion, name='eliminar_asignacion'),
]