from django.urls import path
from . import views

app_name = 'Descargue'

urlpatterns = [
    path('',                            views.dashboard,           name='dashboard'),
    path('empresa/agregar/',            views.agregar_empresa,     name='agregar_empresa'),
    path('empresa/lista/',              views.lista_empresas,      name='lista_empresas'),
    path('producto/agregar/',           views.agregar_producto,    name='agregar_producto'),
    path('producto/lista/',             views.lista_productos,     name='lista_productos'),
    path('registrar/',                  views.registrar_descargue, name='registrar'),
    path('registro/<int:pk>/eliminar/', views.eliminar_registro,   name='eliminar_registro'),
    path('registro/<int:pk>/factura/',  views.factura_registro,    name='factura_registro'),
    path('resumen/',                    views.resumen_dia,         name='resumen'),
    path('cerrar/',                     views.cerrar_dia,          name='cerrar'),
    path('reabrir/',                    views.reabrir_dia,         name='reabrir'),
    path('cierre/<str:fecha>/',         views.ver_cierre,          name='ver_cierre'),
    path('cierre/<str:fecha>/pdf/',     views.generar_pdf,         name='pdf'),
]