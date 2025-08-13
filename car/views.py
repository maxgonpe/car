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
from django.template.loader import render_to_string
from .models import Presupuesto, RepuestoRecomendado,\
					Diagnostico, Cliente, Vehiculo,\
                    Componente
from .forms import ComponenteForm, ClienteForm, VehiculoForm,\
                   DiagnosticoForm

import pathlib



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
    # listas para los selects
    clientes_existentes = Cliente.objects.all().order_by('nombre')
    vehiculos_existentes = Vehiculo.objects.all().order_by('placa')  # o .order_by('marca')

    # valores por defecto para re-renderizar selección si hubo POST
    selected_cliente = None
    selected_vehiculo = None

    if request.method == 'POST':
        # instanciar forms con prefix (para evitar colisiones)
        cliente_form = ClienteForm(request.POST, prefix='cliente')
        vehiculo_form = VehiculoForm(request.POST, prefix='vehiculo')
        diagnostico_form = DiagnosticoForm(request.POST, prefix='diag')

        cliente_id = request.POST.get('cliente_existente')  # viene del select
        vehiculo_id = request.POST.get('vehiculo_existente')

        # --- Cliente: existente o nuevo ---
        cliente = None
        if cliente_id:
            try:
                cliente = Cliente.objects.get(pk=cliente_id)
                selected_cliente = cliente.pk
            except Cliente.DoesNotExist:
                cliente = None
                cliente_form.add_error(None, "El cliente seleccionado no existe.")
        else:
            # nuevo cliente vía form
            if cliente_form.is_valid():
                cliente = cliente_form.save()
                selected_cliente = cliente.pk
            # si no es válido, dejaremos que los errores se muestren en template

        # --- Vehículo: existente o nuevo ---
        vehiculo = None
        if vehiculo_id:
            try:
                vehiculo = Vehiculo.objects.get(pk=vehiculo_id)
                selected_vehiculo = vehiculo.pk
            except Vehiculo.DoesNotExist:
                vehiculo = None
                vehiculo_form.add_error(None, "El vehículo seleccionado no existe.")
        else:
            # nuevo vehiculo vía form, necesita cliente asignado
            if vehiculo_form.is_valid() and cliente:
                vehiculo = vehiculo_form.save(commit=False)
                vehiculo.cliente = cliente
                vehiculo.save()
                selected_vehiculo = vehiculo.pk
            else:
                # si el form no es válido, quedan errores para mostrar
                pass

        # --- Diagnóstico ---
        if diagnostico_form.is_valid() and vehiculo:
            diagnostico = diagnostico_form.save(commit=False)
            diagnostico.vehiculo = vehiculo
            diagnostico.save()

            messages.success(request, "Ingreso guardado correctamente.")
            return redirect('panel_principal')  # ajusta URL a tu nombre real
        else:
            # si diagnostico inválido, mostramos errores
            pass

    else:
        # GET: crear forms vacíos (con prefix)
        cliente_form = ClienteForm(prefix='cliente')
        vehiculo_form = VehiculoForm(prefix='vehiculo')
        diagnostico_form = DiagnosticoForm(prefix='diag')

    # render con todo (incluimos selected_* para preseleccionar en template)
    return render(request, 'car/ingreso.html', {
        'cliente_form': cliente_form,
        'vehiculo_form': vehiculo_form,
        'diagnostico_form': diagnostico_form,
        'clientes_existentes': clientes_existentes,
        'vehiculos_existentes': vehiculos_existentes,
        'selected_cliente': selected_cliente,
        'selected_vehiculo': selected_vehiculo,
    })



def ingreso_view2(request):
    clientes_existentes = Cliente.objects.all()
    vehiculos_existentes = Vehiculo.objects.all()

    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_existente')
        vehiculo_id = request.POST.get('vehiculo_existente')

        cliente_form = ClienteForm(request.POST, prefix='cliente')
        vehiculo_form = VehiculoForm(request.POST, prefix='vehiculo')
        diagnostico_form = DiagnosticoForm(request.POST, prefix='diag')

        # Cliente existente o nuevo
        if cliente_id:
            cliente = Cliente.objects.get(id=cliente_id)
        elif cliente_form.is_valid():
            cliente = cliente_form.save()
        else:
            cliente = None

        # Vehiculo existente o nuevo
        if vehiculo_id:
            vehiculo = Vehiculo.objects.get(id=vehiculo_id)
        elif vehiculo_form.is_valid() and cliente:
            vehiculo = vehiculo_form.save(commit=False)
            vehiculo.cliente = cliente
            vehiculo.save()
        else:
            vehiculo = None

        if diagnostico_form.is_valid() and vehiculo:
            diagnostico = diagnostico_form.save(commit=False)
            diagnostico.vehiculo = vehiculo
            diagnostico.save()
            return redirect('car/ingreso_exitoso')

    else:
        cliente_form = ClienteForm(prefix='cliente')
        vehiculo_form = VehiculoForm(prefix='vehiculo')
        diagnostico_form = DiagnosticoForm(prefix='diag')

    return render(request, 'car/ingreso.html', {
        'cliente_form': cliente_form,
        'vehiculo_form': vehiculo_form,
        'diagnostico_form': diagnostico_form,
        'clientes_existentes': clientes_existentes,
        'vehiculos_existentes': vehiculos_existentes
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



def componente_list3(request):
    q = request.GET.get('q', '').strip()
    componentes = Componente.objects.all().order_by('codigo')
    
    if q:
        componentes = componentes.filter(nombre__icontains=q)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        data = [{
            'id': c.id,
            'nombre': c.nombre,
            'codigo': c.codigo,
            'activo': c.activo,
            'padre': c.padre.nombre if c.padre else 'Principal',
            'padre_id': c.padre.id if c.padre else None
        } for c in componentes]
        return JsonResponse({'componentes': data})

    return render(request, 'car/componentes_list.html', {
        'componentes': componentes.filter(padre__isnull=True),  # Solo los principales para el árbol
        'q': q,
    })

def componente_list2(request):
    q = request.GET.get('q', '').strip()
    componentes = Componente.objects.all().order_by('codigo')
    if q:
        componentes = componentes.filter(nombre__icontains=q)
    paginator = Paginator(componentes, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'car/componentes_list.html', {
        'page_obj': page_obj,
        'q': q,
    })

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


def panel_principal2(request):
    from .models import Cliente
    clientes = Cliente.objects.prefetch_related('vehiculos')
    return render(request, 'car/panel_principal.html', {'clientes': clientes})


def mostrar_plano(request):
    svg_path = pathlib.Path(settings.BASE_DIR) / 'static' / 'images' / 'vehiculo-desde-abajo.svg'
    svg_content = svg_path.read_text(encoding='utf-8')
    return render(request, 'car/plano_interactivo.html', {'svg': svg_content})

def componentes_lookup2(request):
    part = request.GET.get('part')
    if not part:
        return JsonResponse({'error': 'missing part'}, status=400)

    # BUSCA por codigo (ideal) o por nombre
    # supongamos que tus data-part coinciden con codigo (slug) o nombre
    try:
        comp = Componente.objects.get(codigo=part)
    except Componente.DoesNotExist:
        # intentar por nombre
        comp = Componente.objects.filter(nombre__iexact=part).first()

    if not comp:
        return JsonResponse({'found': False})

    hijos = list(comp.hijos.values('id','nombre','codigo'))
    parent = {'id': comp.id, 'nombre': comp.nombre, 'codigo': comp.codigo}
    return JsonResponse({'found': True, 'parent': parent, 'children': hijos})


def componentes_lookup3(request):
    part = request.GET.get('part')
    if not part:
        return JsonResponse({'error': 'missing part'}, status=400)

    try:
        comp = Componente.objects.get(codigo=part)
    except Componente.DoesNotExist:
        comp = Componente.objects.filter(nombre__iexact=part).first()

    if not comp:
        return JsonResponse({'found': False})

    hijos = list(comp.hijos.values('id', 'nombre', 'codigo'))

    # Si tienes un campo imagen en el modelo
    if hasattr(comp, 'imagen') and comp.imagen:
        imagen_url = comp.imagen.url
    else:
        # Si quieres deducirlo por el código
        imagen_url = f"{settings.STATIC_URL}images/{comp.codigo}.svg"
        print( "si hay imagen ",imagen_url)
    parent = {
        'id': comp.id,
        'nombre': comp.nombre,
        'codigo': comp.codigo,
        'imagen_url': imagen_url
    }

    print("parent ",parent)
    return JsonResponse({
        'found': True,
        'parent': parent,
        'children': hijos
    })


def componentes_lookup(request):
    part = (request.GET.get('part') or '').strip()
    if not part:
        return JsonResponse({'error': 'missing part'}, status=400)

    # normaliza búsqueda
    part_norm = part.lower()

    # evita ids tipo 'g8' (capas de inkscape)
    import re
    if re.match(r'^g\d+$', part_norm):
        return JsonResponse({'found': False})

    try:
        comp = Componente.objects.get(codigo__iexact=part_norm)
    except Componente.DoesNotExist:
        comp = Componente.objects.filter(nombre__iexact=part_norm).first()

    if not comp:
        return JsonResponse({'found': False})

    hijos = list(comp.hijos.values('id', 'nombre', 'codigo'))

    # construir URL de imagen de forma segura
    if hasattr(comp, 'imagen') and comp.imagen:
        imagen_url = comp.imagen.url
    else:
        # si usas staticfiles: usa staticfiles_storage para resolver URL
        try:
            imagen_url = staticfiles_storage.url(f'images/{comp.codigo}.svg')
        except Exception:
            imagen_url = settings.STATIC_URL + f'images/{comp.codigo}.svg'

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