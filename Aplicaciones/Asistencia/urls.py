from django.urls import path
from . import views

app_name = 'asistencia'

urlpatterns = [
    path('', views.inicio, name='inicio'),
   
    path('asistencia/', views.asistencia_view, name='asistencia'),
    path('seleccionar-trabajadores/', views.seleccionar_trabajadores, name='seleccionar_trabajadores'),
    path('marcar-salida/', views.marcar_salida, name='marcar_salida'),
    path('empleados/listar/', views.listar_empleados, name='listar_empleados'),
    path('empleados/obtener/<int:empleado_id>/', views.obtener_empleado, name='obtener_empleado'),
    path('empleados/guardar/', views.guardar_empleado, name='guardar_empleado'),
    path('empleados/eliminar/<int:empleado_id>/', views.eliminar_empleado, name='eliminar_empleado'),
    path('asistencias/listar/', views.listar_asistencias, name='listar_asistencias'),
    path('asistencias/eliminar/<int:asistencia_id>/', views.eliminar_asistencia, name='eliminar_asistencia'),
]