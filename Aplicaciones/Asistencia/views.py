from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime
from .models import Empleado, Asistencia

def inicio(request):
    empleados = Empleado.objects.filter(activo=True)
    hoy = timezone.now().date()
    asistencias_hoy = Asistencia.objects.filter(fecha=hoy)
    
    return render(request, 'inicio.html', {
        'fecha_actual': hoy,
        'total_empleados': empleados.count(),
        'total_presentes': asistencias_hoy.count(),
    })

def asistencia_view(request):
    hoy = timezone.now().date()
    
    # Obtener IDs de empleados que YA tienen asistencia registrada hoy
    empleados_registrados_ids = Asistencia.objects.filter(fecha=hoy).values_list('empleado_id', flat=True)
    
    # Mostrar solo empleados que NO están registrados hoy
    empleados = Empleado.objects.filter(activo=True).exclude(id__in=empleados_registrados_ids).order_by('apellidos', 'nombres')
    
    # Obtener todas las asistencias del día para mostrar en la tabla
    asistencias_dict = {a.empleado.id: a for a in Asistencia.objects.filter(fecha=hoy).select_related('empleado')}
    
    return render(request, 'asistencia.html', {
        'empleados': empleados,
        'asistencias_dict': asistencias_dict,
        'fecha_actual': hoy,
        'total_empleados': Empleado.objects.filter(activo=True).count(),
        'total_presentes': len(asistencias_dict),
    })

def seleccionar_trabajadores(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        empleados_ids = request.POST.getlist('empleados_ids[]')
        hora_entrada = request.POST.get('hora_entrada')
        hoy = timezone.now().date()
        
        if not empleados_ids or not hora_entrada:
            return JsonResponse({'success': False, 'message': 'Faltan datos'})
        
        hora_obj = datetime.strptime(hora_entrada, '%H:%M').time()
        
        registros_creados = 0
        empleados_ya_registrados = []
        
        for emp_id in empleados_ids:
            empleado = Empleado.objects.get(id=emp_id)
            
            # Verificar si ya existe una asistencia para este empleado en este día
            asistencia_existente = Asistencia.objects.filter(
                empleado=empleado,
                fecha=hoy
            ).first()
            
            if asistencia_existente:
                # Si ya existe, agregar a la lista de ya registrados
                empleados_ya_registrados.append(empleado.nombre_completo)
            else:
                # Si no existe, crear nuevo registro
                Asistencia.objects.create(
                    empleado=empleado,
                    fecha=hoy,
                    hora_entrada=hora_obj
                )
                registros_creados += 1
        
        # Construir mensaje de respuesta
        if registros_creados > 0 and len(empleados_ya_registrados) > 0:
            mensaje = f'✓ {registros_creados} empleados registrados con éxito.<br>'
            mensaje += f'⚠️ {len(empleados_ya_registrados)} ya estaban registrados: {", ".join(empleados_ya_registrados[:3])}'
            if len(empleados_ya_registrados) > 3:
                mensaje += f' y {len(empleados_ya_registrados) - 3} más...'
        elif registros_creados > 0:
            mensaje = f'✓ {registros_creados} empleados registrados con entrada a las {hora_entrada}'
        else:
            mensaje = f'⚠️ Todos los empleados seleccionados ya estaban registrados para hoy'
        
        return JsonResponse({
            'success': True,
            'message': mensaje
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

def marcar_salida(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        empleado_id = request.POST.get('empleado_id')
        hora_salida = request.POST.get('hora_salida')
        hoy = timezone.now().date()
        
        empleado = get_object_or_404(Empleado, id=empleado_id, activo=True)
        asistencia = Asistencia.objects.filter(empleado=empleado, fecha=hoy).first()
        
        if not asistencia:
            return JsonResponse({
                'success': False,
                'message': f'⚠️ {empleado.nombre_completo} no está registrado para hoy'
            })
        
        if asistencia.hora_salida:
            return JsonResponse({
                'success': False,
                'message': f'⚠️ {empleado.nombre_completo} ya marcó salida a las {asistencia.hora_salida.strftime("%H:%M")}'
            })
        
        asistencia.hora_salida = datetime.strptime(hora_salida, '%H:%M').time()
        asistencia.save()
        
        return JsonResponse({
            'success': True,
            'tipo': 'salida',
            'message': f'✓ SALIDA REGISTRADA<br><strong>{empleado.nombre_completo}</strong><br>Hora: {hora_salida}<br>Duración: {asistencia.duracion_jornada()}'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

def listar_empleados(request):
    empleados = Empleado.objects.all().order_by('apellidos')
    data = [{
        'id': e.id,
        'cedula': e.cedula,
        'nombres': e.nombres,
        'apellidos': e.apellidos,
        'nombre_completo': e.nombre_completo,
        'cargo': e.cargo,
        'telefono': e.telefono,
        'email': e.email or '',
        'fecha_ingreso': e.fecha_ingreso.strftime('%Y-%m-%d'),
        'activo': e.activo,
    } for e in empleados]
    return JsonResponse({'data': data})

def obtener_empleado(request, empleado_id):
    try:
        e = get_object_or_404(Empleado, id=empleado_id)
        return JsonResponse({
            'success': True,
            'data': {
                'id': e.id,
                'cedula': e.cedula,
                'nombres': e.nombres,
                'apellidos': e.apellidos,
                'cargo': e.cargo,
                'telefono': e.telefono,
                'email': e.email or '',
                'fecha_ingreso': e.fecha_ingreso.strftime('%Y-%m-%d'),
                'activo': e.activo,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

def guardar_empleado(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        empleado_id = request.POST.get('empleado_id')
        empleado = Empleado.objects.get(id=empleado_id) if empleado_id else Empleado()
        
        empleado.cedula = request.POST.get('cedula')
        empleado.nombres = request.POST.get('nombres')
        empleado.apellidos = request.POST.get('apellidos')
        empleado.cargo = request.POST.get('cargo')
        empleado.telefono = request.POST.get('telefono')
        empleado.email = request.POST.get('email')
        empleado.fecha_ingreso = request.POST.get('fecha_ingreso')
        empleado.activo = request.POST.get('activo') == 'true'
        empleado.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Empleado {empleado.nombre_completo} guardado exitosamente'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

def eliminar_empleado(request, empleado_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        empleado = get_object_or_404(Empleado, id=empleado_id)
        nombre = empleado.nombre_completo
        empleado.delete()
        return JsonResponse({'success': True, 'message': f'Empleado {nombre} eliminado'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

def listar_asistencias(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    asistencias = Asistencia.objects.all().select_related('empleado')
    if fecha_inicio:
        asistencias = asistencias.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        asistencias = asistencias.filter(fecha__lte=fecha_fin)
    
    data = [{
        'id': a.id,
        'empleado': a.empleado.nombre_completo,
        'cedula': a.empleado.cedula,
        'cargo': a.empleado.cargo,
        'fecha': a.fecha.strftime('%Y-%m-%d'),
        'hora_entrada': a.hora_entrada.strftime('%H:%M'),
        'hora_salida': a.hora_salida.strftime('%H:%M') if a.hora_salida else '',
        'duracion': a.duracion_jornada(),
        'observaciones': a.observaciones or '',
    } for a in asistencias]
    
    return JsonResponse({'data': data})

def eliminar_asistencia(request, asistencia_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        asistencia = get_object_or_404(Asistencia, id=asistencia_id)
        empleado = asistencia.empleado.nombre_completo
        fecha = asistencia.fecha
        asistencia.delete()
        return JsonResponse({
            'success': True,
            'message': f'Asistencia de {empleado} del {fecha} eliminada'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

        from django.shortcuts import render

def inicio(request):
    return render(request, 'inicio.html')  # o tu plantilla principal
