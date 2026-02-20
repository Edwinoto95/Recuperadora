from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from io import BytesIO
import json

from .models import Empresa, Producto, CierreDia, RegistroDescargue, ItemDescargue


def _agrupar_por_empresa(registros):
    data = {}
    for reg in registros:
        key = reg.empresa_id or 0
        if key not in data:
            data[key] = {'empresa': reg.empresa, 'registros': [], 'subtotal_palets': 0}
        data[key]['registros'].append(reg)
        data[key]['subtotal_palets'] = round(data[key]['subtotal_palets'] + reg.total_palets, 2)
    return list(data.values())


# ── DASHBOARD ─────────────────────────────────

def dashboard(request):
    hoy = timezone.localdate()
    cierre, _ = CierreDia.objects.get_or_create(fecha=hoy)
    registros = (RegistroDescargue.objects
                 .filter(cierre=cierre)
                 .select_related('empresa')
                 .prefetch_related('items__producto')
                 .order_by('-hora'))
    total_palets = round(sum(r.total_palets for r in registros), 2)
    return render(request, 'descargue.html', {
        'cierre': cierre,
        'registros': registros,
        'total_palets': total_palets,
        'hoy': hoy,
        'cierres_anteriores': CierreDia.objects.exclude(fecha=hoy).order_by('-fecha')[:15],
    })


# ── EMPRESAS ──────────────────────────────────

@csrf_exempt
def agregar_empresa(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    data = json.loads(request.body)
    nombre = data.get('nombre', '').strip()
    if not nombre:
        return JsonResponse({'ok': False, 'error': 'El nombre es requerido'})
    emp, created = Empresa.objects.get_or_create(
        nombre__iexact=nombre, defaults={'nombre': nombre}
    )
    return JsonResponse({'ok': True, 'id': emp.id, 'nombre': emp.nombre, 'nuevo': created})


def lista_empresas(request):
    q = request.GET.get('q', '').strip()
    qs = Empresa.objects.filter(activo=True)
    if q:
        qs = qs.filter(nombre__icontains=q)
    return JsonResponse({'empresas': list(qs.values('id', 'nombre').order_by('nombre')[:50])})


# ── PRODUCTOS ─────────────────────────────────

@csrf_exempt
def agregar_producto(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    data = json.loads(request.body)
    nombre = data.get('nombre', '').strip()
    if not nombre:
        return JsonResponse({'ok': False, 'error': 'El nombre es requerido'})
    prod, created = Producto.objects.get_or_create(
        nombre__iexact=nombre,
        defaults={
            'nombre': nombre,
            'categoria': data.get('categoria', 'otros'),
            'unidades_por_capa': int(data.get('unidades_por_capa', 8)),
            'capas_por_palet': int(data.get('capas_por_palet', 8)),
        }
    )
    return JsonResponse({
        'ok': True, 'id': prod.id, 'nombre': prod.nombre,
        'unidades_palet': prod.unidades_palet_completo,
        'upc': prod.unidades_por_capa, 'cpp': prod.capas_por_palet,
        'nuevo': created,
    })


def lista_productos(request):
    qs = Producto.objects.filter(activo=True).order_by('categoria', 'nombre')
    return JsonResponse({'productos': [{
        'id': p.id, 'nombre': p.nombre,
        'upc': p.unidades_por_capa, 'cpp': p.capas_por_palet,
        'unidades_palet': p.unidades_palet_completo,
    } for p in qs]})


# ── REGISTRAR DESCARGUE (con múltiples productos) ─────────

@csrf_exempt
def registrar_descargue(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    data = json.loads(request.body)
    hoy = timezone.localdate()
    cierre, _ = CierreDia.objects.get_or_create(fecha=hoy)
    if cierre.estado == 'cerrado':
        return JsonResponse({'ok': False, 'error': 'El día ya está cerrado.'})

    try:
        empresa = Empresa.objects.get(id=data['empresa_id'])
    except (Empresa.DoesNotExist, KeyError):
        return JsonResponse({'ok': False, 'error': 'Empresa no válida.'})

    items_data = data.get('items', [])
    if not items_data:
        return JsonResponse({'ok': False, 'error': 'Agrega al menos un producto.'})

    # Validar que todos los productos existan
    productos = {}
    for item in items_data:
        try:
            p = Producto.objects.get(id=item['producto_id'])
            productos[item['producto_id']] = p
        except (Producto.DoesNotExist, KeyError):
            return JsonResponse({'ok': False, 'error': f'Producto ID {item.get("producto_id")} no válido.'})

    duracion = int(data.get('duracion_minutos', 30))
    reg = RegistroDescargue.objects.create(
        cierre=cierre,
        empresa=empresa,
        chofer_nombre=data.get('chofer_nombre', '').strip(),
        chofer_telefono=data.get('chofer_telefono', '').strip(),
        placa=data.get('placa', '').upper().strip(),
        tipo=data.get('tipo', 'completo'),
        observacion=data.get('observacion', ''),
        duracion_minutos=duracion,
    )

    items_creados = []
    for item in items_data:
        prod = productos[item['producto_id']]
        it = ItemDescargue.objects.create(
            registro=reg,
            producto=prod,
            palets_completos=int(item.get('palets_completos', 0)),
            unidades_sueltas=int(item.get('unidades_sueltas', 0)),
        )
        items_creados.append({
            'id': it.id,
            'producto': prod.nombre,
            'palets_completos': it.palets_completos,
            'unidades_sueltas': it.unidades_sueltas,
            'palets_eq': it.palets_equivalentes,
        })

    return JsonResponse({
        'ok': True,
        'id': reg.id,
        'empresa': empresa.nombre,
        'chofer': reg.chofer_nombre,
        'telefono': reg.chofer_telefono,
        'placa': reg.placa,
        'tipo': reg.get_tipo_display(),
        'total_palets': reg.total_palets,
        'hora': reg.hora.strftime('%H:%M'),
        'hora_fin': reg.hora_fin_estimada.strftime('%H:%M') if reg.hora_fin_estimada else '—',
        'duracion': duracion,
        'observacion': reg.observacion,
        'items': items_creados,
    })


@csrf_exempt
def eliminar_registro(request, pk):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    reg = get_object_or_404(RegistroDescargue, pk=pk)
    if reg.cierre.estado == 'cerrado':
        return JsonResponse({'ok': False, 'error': 'Cierre cerrado.'})
    reg.delete()
    return JsonResponse({'ok': True})


# ── FACTURA CHOFER ────────────────────────────

def factura_registro(request, pk):
    reg = get_object_or_404(
        RegistroDescargue.objects.select_related('empresa', 'cierre').prefetch_related('items__producto'),
        pk=pk
    )
    return render(request, 'factura_chofer.html', {
        'reg': reg,
        'empresa_nombre': 'Recuperadora Logística Integral',
    })


# ── RESUMEN ───────────────────────────────────

def resumen_dia(request):
    hoy = timezone.localdate()
    cierre, _ = CierreDia.objects.get_or_create(fecha=hoy)
    registros = (RegistroDescargue.objects
                 .filter(cierre=cierre)
                 .select_related('empresa')
                 .prefetch_related('items__producto')
                 .order_by('-hora'))
    total_palets = round(sum(r.total_palets for r in registros), 2)
    return JsonResponse({
        'estado': cierre.estado,
        'total_palets': total_palets,
        'registros': [{
            'id': r.id,
            'hora': r.hora.strftime('%H:%M'),
            'empresa': r.empresa.nombre if r.empresa else '—',
            'chofer': r.chofer_nombre,
            'placa': r.placa,
            'tipo': r.get_tipo_display(),
            'total_palets': r.total_palets,
            'hora_fin': r.hora_fin_estimada.strftime('%H:%M') if r.hora_fin_estimada else '—',
            'items': [{'producto': i.producto.nombre, 'palets_eq': i.palets_equivalentes} for i in r.items.all()],
        } for r in registros],
    })


# ── CIERRE ────────────────────────────────────

@csrf_exempt
def cerrar_dia(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    data = json.loads(request.body)
    cierre = get_object_or_404(CierreDia, fecha=timezone.localdate())
    if cierre.estado == 'cerrado':
        return JsonResponse({'ok': False, 'error': 'Ya está cerrado.'})
    cierre.recalcular()
    cierre.estado = 'cerrado'
    cierre.hora_cierre = timezone.now()
    cierre.observaciones = data.get('observaciones', '')
    cierre.save()
    return JsonResponse({'ok': True, 'total_palets': float(cierre.total_palets)})


@csrf_exempt
def reabrir_dia(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    cierre = get_object_or_404(CierreDia, fecha=timezone.localdate())
    cierre.estado = 'abierto'
    cierre.hora_cierre = None
    cierre.save()
    return JsonResponse({'ok': True})


# ── VER CIERRE ────────────────────────────────

def ver_cierre(request, fecha):
    from datetime import date
    try:
        fecha_obj = date.fromisoformat(fecha)
    except ValueError:
        return HttpResponse("Fecha inválida", status=400)
    cierre = get_object_or_404(CierreDia, fecha=fecha_obj)
    registros = (RegistroDescargue.objects
                 .filter(cierre=cierre)
                 .select_related('empresa')
                 .prefetch_related('items__producto')
                 .order_by('empresa__nombre', 'hora'))
    empresas_data = _agrupar_por_empresa(registros)
    total_registros = sum(len(e['registros']) for e in empresas_data)
    return render(request, 'cierre_detalle.html', {
        'cierre': cierre,
        'empresas_data': empresas_data,
        'total_empresas': len(empresas_data),
        'total_registros': total_registros,
        'empresa_nombre': 'Recuperadora Logística Integral',
    })


# ── PDF ───────────────────────────────────────

def generar_pdf(request, fecha):
    from datetime import date
    try:
        fecha_obj = date.fromisoformat(fecha)
    except ValueError:
        return HttpResponse("Fecha inválida", status=400)
    cierre = get_object_or_404(CierreDia, fecha=fecha_obj)
    registros = (RegistroDescargue.objects
                 .filter(cierre=cierre)
                 .select_related('empresa')
                 .prefetch_related('items__producto')
                 .order_by('empresa__nombre', 'hora'))
    context = {
        'cierre': cierre,
        'empresas_data': _agrupar_por_empresa(registros),
        'empresa_nombre': 'Recuperadora Logística Integral',
        'total_registros': registros.count(),
        'total_empresas': len(set(r.empresa_id for r in registros)),
    }
    try:
        from xhtml2pdf import pisa
        html_bytes = render(request, 'cierre_pdf.html', context).content
        result = BytesIO()
        pisa.CreatePDF(BytesIO(html_bytes), dest=result)
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="descargue_{fecha}.pdf"'
        return response
    except ImportError:
        return render(request, 'cierre_pdf.html', context)