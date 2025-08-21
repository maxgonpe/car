from decimal import Decimal
from datetime import date, timedelta
from django.conf import settings
from django.http import Http404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.templatetags.static import static
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from .models import Presupuesto, RepuestoRecomendado,\
					Diagnostico, Cliente, Vehiculo,\
                    Componente
from .forms import ComponenteForm, ClienteForm, VehiculoForm,\
                   DiagnosticoForm


import re
import pathlib
import os



def panel_principal(request):
    clientes = Cliente.objects.all()
    return render(request, 'car/panel_principal.html', {'clientes': clientes})


def componente_list(request):
    q = request.GET.get('q', '').strip()
    if q:
        componentes = Componente.objects.filter(nombre__icontains=q).order_by('codigo')
    else:
        componentes = Componente.objects.filter(padre__isnull=True).order_by('codigo')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('car/componentes_tree.html', {'componentes': componentes})
        return JsonResponse({'html': html})

    return render(request, 'car/componentes_list.html', {
        'componentes': componentes,
        'q': q,
    })


def ingreso_view(request):
    clientes_existentes = Cliente.objects.all().order_by('nombre')

    selected_cliente = None
    selected_vehiculo = None
    selected_componentes_ids = []

    if request.method == 'POST':
        cliente_form = ClienteForm(request.POST, prefix='cliente')
        vehiculo_form = VehiculoForm(request.POST, prefix='vehiculo')
        diagnostico_form = DiagnosticoForm(request.POST, prefix='diag')

        cliente_id = request.POST.get('cliente_existente')
        vehiculo_id = request.POST.get('vehiculo_existente')
        selected_componentes_ids = request.POST.getlist('componentes_seleccionados')

        # --- Cliente ---
        cliente = None
        if cliente_id:
            try:
                cliente = Cliente.objects.get(pk=cliente_id)
                selected_cliente = cliente.pk
            except Cliente.DoesNotExist:
                cliente_form.add_error(None, "El cliente seleccionado no existe.")
        else:
            if cliente_form.is_valid():
                cliente = cliente_form.save()
                selected_cliente = cliente.pk

        # --- Vehículo ---
        vehiculo = None
        if vehiculo_id:
            try:
                # Validar que pertenezca al cliente seleccionado
                vehiculo = Vehiculo.objects.get(pk=vehiculo_id, cliente=cliente)
                selected_vehiculo = vehiculo.pk
            except Vehiculo.DoesNotExist:
                vehiculo_form.add_error(None, "El vehículo seleccionado no existe o no pertenece al cliente.")
        else:
            if vehiculo_form.is_valid() and cliente:
                vehiculo = vehiculo_form.save(commit=False)
                vehiculo.cliente = cliente
                vehiculo.save()
                selected_vehiculo = vehiculo.pk

        # --- Diagnóstico ---
        if diagnostico_form.is_valid() and vehiculo:
            diagnostico = diagnostico_form.save(commit=False)
            diagnostico.vehiculo = vehiculo
            diagnostico.save()
            diagnostico.componentes.set(selected_componentes_ids)
            messages.success(request, "Ingreso guardado correctamente.")
            return redirect('panel_principal')
        else:
            # Opcional: debug
            # print("Form diag errors:", diagnostico_form.errors)
            pass

    else:
        cliente_form = ClienteForm(prefix='cliente')
        vehiculo_form = VehiculoForm(prefix='vehiculo')
        diagnostico_form = DiagnosticoForm(prefix='diag')

    # 🚫 Importante: en la carga inicial no mandes todos los vehículos.
    # Deja el select vacío y que el JS lo cargue según el cliente.
    vehiculos_existentes = Vehiculo.objects.none()

    
    # cargar motor.svg como string
    svg_path = os.path.join(settings.BASE_DIR, "static", "images", "vehiculo-desde-abajo.svg")
    svg_content = ""
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
    except FileNotFoundError:
        pass


    return render(request, 'car/ingreso.html', {
        'cliente_form': cliente_form,
        'vehiculo_form': vehiculo_form,
        'diagnostico_form': diagnostico_form,
        'clientes_existentes': clientes_existentes,
        'vehiculos_existentes': vehiculos_existentes,  # vacío; se llenará por AJAX
        'selected_cliente': selected_cliente,
        'selected_vehiculo': selected_vehiculo,
        'componentes': Componente.objects.filter(padre__isnull=True, activo=True),
        'selected_componentes_ids': selected_componentes_ids,
        'svg': svg_content,
    })




def ingreso_exitoso_view(request):
    return render(request, 'car/ingreso_exitoso.html')


def eliminar_diagnostico(request, pk):
    diag = get_object_or_404(Diagnostico, pk=pk)
    diag.delete()
    return redirect('ingreso')


def editar_diagnostico(request, pk):
    diag = get_object_or_404(Diagnostico, pk=pk)
    diagnostico_form = DiagnosticoForm(request.POST or None, instance=diag)
    if request.method == 'POST' and diagnostico_form.is_valid():
        diagnostico_form.save()
        return redirect('ingreso')
    return render(request, 'car/editar_diagnostico.html', {'form': diagnostico_form})


def componente_create(request):
    if request.method == 'POST':
        form = ComponenteForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Componente creado correctamente.')
                return redirect('componente_list')
            except (ValidationError, IntegrityError) as e:
                # Muestra el error en el form sin 500
                #form.add_error(None, getattr(e, 'message', str(e)))
                messages.error(request, 'El componente ya existe. Por favor, use un nombre o código diferente.')
        else:
            # Manejar errores de validación del formulario
            messages.error(request, 'Por favor, corrija los errores en el formulario.')

    else:
        form = ComponenteForm()
    return render(request, 'car/componentes_form.html', {
        'form': form,
        'titulo': 'Nuevo Componente',
        'submit_label': 'Crear',
    })

def componente_update(request, pk):
    componente = get_object_or_404(Componente, pk=pk)
    if request.method == 'POST':
        form = ComponenteForm(request.POST, instance=componente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Componente actualizado.')
            return redirect('componente_list')
    else:
        form = ComponenteForm(instance=componente)
    return render(request, 'car/componentes_form.html', {
        'form': form,
        'titulo': 'Editar Componente',
        'submit_label': 'Guardar cambios',
    })

def componente_delete(request, pk):
    componente = get_object_or_404(Componente, pk=pk)
    if request.method == 'POST':
        componente.delete()
        messages.success(request, 'Componente eliminado.')
        return redirect('componente_list')
    return render(request, 'car/componentes_confirm_delete.html', {
        'componente': componente
    })



def mostrar_plano(request):
    svg_path = pathlib.Path(settings.BASE_DIR) / 'static' / 'images' / 'vehiculo-desde-abajo.svg'
    svg_content = svg_path.read_text(encoding='utf-8')
    return render(request, 'car/plano_interactivo.html', {'svg': svg_content})


def componentes_lookup(request):
    part = (request.GET.get('part') or '').strip()
    if not part:
        return JsonResponse({'error': 'missing part'}, status=400)

    part_norm = part.lower()

    import re
    if re.match(r'^(g\d+|svg\d+)$', part_norm):
        return JsonResponse({'found': False})

    try:
        comp = Componente.objects.get(codigo__iexact=part_norm)
    except Componente.DoesNotExist:
        comp = Componente.objects.filter(nombre__iexact=part_norm).first()

    if not comp:
        return JsonResponse({'found': False})

    hijos = list(comp.hijos.values('id', 'nombre', 'codigo'))

    # 🔹 buscar imagen en este componente o en su cadena de padres
    imagen_url = None
    current = comp
    while current and not imagen_url:
        try:
            if hasattr(current, 'imagen') and current.imagen:
                imagen_url = current.imagen.url
            else:
                imagen_url = staticfiles_storage.url(f'images/{current.codigo}.svg')
        except Exception:
            imagen_url = settings.STATIC_URL + f'images/{current.codigo}.svg'

        # si tampoco existe, subir al padre
        if not current.padre_id:  
            break
        current = current.padre

    parent = {
        'id': comp.id,
        'nombre': comp.nombre,
        'codigo': comp.codigo,
        'imagen_url': imagen_url
    }

    return JsonResponse({'found': True, 'parent': parent, 'children': hijos})







def seleccionar_componente(request, codigo):
    try:
        comp = Componente.objects.get(codigo=codigo)
    except Componente.DoesNotExist:
        raise Http404("Componente nox encontrado")

    hijos = list(comp.hijos.values('id', 'nombre', 'codigo'))
    return JsonResponse({
        'id': comp.id,
        'nombre': comp.nombre,
        'codigo': comp.codigo,
        'hijos': hijos
    })


def get_vehiculos_por_cliente(request, cliente_id):
    vehiculos = Vehiculo.objects.filter(cliente_id=cliente_id).order_by('placa')
    data = [
        {
            "id": v.id,
            "placa": v.placa,
            "marca": v.marca,
            "modelo": v.modelo,
            "anio": v.anio,
        }
        for v in vehiculos
    ]
    return JsonResponse(data, safe=False)


def lista_diagnosticos(request):
    diagnosticos = Diagnostico.objects.all().order_by('-fecha')
    return render(request, 'car/diagnostico_lista.html', {'diagnosticos': diagnosticos})
