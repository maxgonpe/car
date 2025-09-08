from decimal import Decimal
from datetime import date, timedelta
from django.conf import settings
from django.http import Http404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.templatetags.static import static
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Sum
from django.db.models import Q
from .models import Diagnostico, Cliente, Vehiculo,\
                    Componente, Accion, ComponenteAccion,\
                    DiagnosticoComponenteAccion, Repuesto, VehiculoVersion,\
                    DiagnosticoRepuesto
from .forms import ComponenteForm, ClienteForm, VehiculoForm,\
                   DiagnosticoForm, AccionForm, ComponenteAccionForm


import json
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


@transaction.atomic
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

            # 🔹 Relación M2M con componentes
            diagnostico.componentes.set(selected_componentes_ids)

            # ====================================================
            # 🔹 Acciones por componente desde hidden JSON
            acciones_json = (request.POST.get("acciones_componentes_json") or "").strip()
            if acciones_json:
                try:
                    items = json.loads(acciones_json)
                    for it in items:
                        try:
                            comp_id = int(it.get("componente_id"))
                            acc_id = int(it.get("accion_id"))
                        except (TypeError, ValueError):
                            continue

                        precio = (it.get("precio") or "").strip()

                        if not diagnostico.componentes.filter(id=comp_id).exists():
                            continue  # ignora acciones de componentes no seleccionados

                        dca = DiagnosticoComponenteAccion(
                            diagnostico=diagnostico,
                            componente_id=comp_id,
                            accion_id=acc_id,
                        )
                        if precio and precio not in ("0", "0.00"):
                            dca.precio_mano_obra = precio
                        dca.save()
                except json.JSONDecodeError:
                    pass
            
            # ====================================================

            # ====================================================
            # 🔹 Repuestos seleccionados desde hidden JSON
            # ====================================================
            # 🔹 Repuestos seleccionados desde hidden JSON
            repuestos_json = (request.POST.get("repuestos_json") or "").strip()
            print("1 Antesss")
            print("2 DEBUG repuestos_json:", repr(repuestos_json))
            if repuestos_json:
                try:
                    repuestos_data = json.loads(repuestos_json)
                    for r in repuestos_data:
                        try:
                            repuesto_id = int(r.get("id"))
                            repuesto = Repuesto.objects.get(pk=repuesto_id)

                            stock_id_raw = r.get("repuesto_stock_id")
                            repuesto_stock = None
                            if stock_id_raw:
                                try:
                                    repuesto_stock = RepuestoEnStock.objects.get(pk=int(stock_id_raw))
                                except (ValueError, RepuestoEnStock.DoesNotExist):
                                    repuesto_stock = None

                            cantidad = int(r.get("cantidad", 1))
                            precio = float(r.get("precio_unitario", repuesto.precio_venta or 0))

                            DiagnosticoRepuesto.objects.create(
                                diagnostico=diagnostico,
                                repuesto=repuesto,
                                repuesto_stock=repuesto_stock,
                                cantidad=cantidad,
                                precio_unitario=precio,
                                subtotal=cantidad * precio
                            )
                            print("DEBUG repuestos_json:", repr(repuestos_json))
                        except (ValueError, Repuesto.DoesNotExist, KeyError):
                            continue
                except json.JSONDecodeError:
                    print("3 pasando por el pass")
                    print("4 DEBUG repuestos_json:", repr(repuestos_json))
                    pass
            print("5 DEBUG repuestos_json:", repr(repuestos_json))
# ====================================================

            # ====================================================

            messages.success(request, "Ingreso guardado correctamente.")
            return redirect('panel_principal')

        # else → si hay errores, sigue abajo y vuelve a renderizar

    else:
        cliente_form = ClienteForm(prefix='cliente')
        vehiculo_form = VehiculoForm(prefix='vehiculo')
        diagnostico_form = DiagnosticoForm(prefix='diag')

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
        'vehiculos_existentes': vehiculos_existentes,
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
    diagnosticos = Diagnostico.objects.all().select_related('vehiculo__cliente').prefetch_related(
        'componentes',
        'acciones_componentes__accion',
        'acciones_componentes__componente'
    ).order_by('-fecha')

    # Anotar total por cada diagnóstico
    diagnosticos = diagnosticos.annotate(
        total_mano_obra=Sum('acciones_componentes__precio_mano_obra')
    )
    return render(request, 'car/diagnostico_lista.html', {'diagnosticos': diagnosticos})

def eliminar_diagnostico(request, pk):
    diagnostico = get_object_or_404(Diagnostico, pk=pk)
    if request.method == 'POST':

        diagnostico.delete()
        
        return redirect('lista_diagnosticos')
    return render(request, 'car/diagnostico_eliminar.html', {'diagnostico': diagnostico})

@require_GET
def acciones_por_componente(request, componente_id: int):
    """
    Devuelve las acciones disponibles para un componente dado,
    con el precio base (catálogo) si existe en ComponenteAccion.
    """
    qs = (ComponenteAccion.objects
          .select_related("accion", "componente")
          .filter(componente_id=componente_id)
          .order_by("accion__nombre"))

    data = [
        {
            "accion_id": ca.accion_id,
            "accion_nombre": ca.accion.nombre,
            "precio_base": str(ca.precio_mano_obra),
        }
        for ca in qs
    ]

    # Si no hay catálogo cargado, al menos devolvemos la lista de acciones globales
    if not data:
        acciones = Accion.objects.all().order_by("nombre")
        data = [
            {"accion_id": a.id, "accion_nombre": a.nombre, "precio_base": None}
            for a in acciones
        ]

    return JsonResponse({"ok": True, "acciones": data})


# ---- EJEMPLO de handler de guardado (adaptar al tuyo actual) ----
# Supone que tu formulario ya crea el Diagnostico y guarda M2M de componentes.
# Solo añadimos la lectura del hidden JSON para poblar DiagnosticoComponenteAccion.
def guardar_diagnostico(request):
    if request.method == "POST":
        # ... tu lógica existente para Cliente/Vehiculo/Diagnostico ...
        # Supongamos que al final tienes el objeto diagnostico creado:
        # diagnostico = Diagnostico.objects.create(...)

        acciones_json = request.POST.get("acciones_componentes_json", "").strip()  # hidden input
        if acciones_json:
            try:
                payload = json.loads(acciones_json)
                # Estructura esperada:
                # [
                #   {"componente_id": 1, "accion_id": 3, "precio": "200.00"},
                #   {"componente_id": 2, "accion_id": 1, "precio": ""}  # vacío => autocompleta
                # ]
                with transaction.atomic():
                    for item in payload:
                        comp_id = int(item.get("componente_id"))
                        acc_id = int(item.get("accion_id"))
                        precio = item.get("precio")

                        dca = DiagnosticoComponenteAccion(
                            diagnostico=diagnostico,
                            componente_id=comp_id,
                            accion_id=acc_id,
                        )
                        # Si precio viene vacío o "0", el save() del modelo lo autocompleta desde ComponenteAccion
                        if precio and str(precio).strip() not in ("0", "0.00", ""):
                            dca.precio_mano_obra = precio
                        dca.save()
            except Exception:
                # Puedes loguear el error si quieres
                pass

        # ... redirección o response ...

# ----- ACCION -----
def accion_list(request):
    q = (request.GET.get("q") or "").strip()
    acciones = Accion.objects.all().order_by("nombre")
    if q:
        acciones = acciones.filter(nombre__icontains=q)
    return render(request, "car/accion_list.html", {"acciones": acciones, "q": q})

def accion_create(request):
    if request.method == "POST":
        form = AccionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Acción creada correctamente.")
            return redirect("accion_list")
    else:
        form = AccionForm()
    return render(request, "car/accion_form.html", {"form": form, "modo": "crear"})

def accion_update(request, pk):
    accion = get_object_or_404(Accion, pk=pk)
    if request.method == "POST":
        form = AccionForm(request.POST, instance=accion)
        if form.is_valid():
            form.save()
            messages.success(request, "Acción actualizada.")
            return redirect("accion_list")
    else:
        form = AccionForm(instance=accion)
    return render(request, "car/accion_form.html", {"form": form, "modo": "editar", "accion": accion})

def accion_delete(request, pk):
    accion = get_object_or_404(Accion, pk=pk)
    if request.method == "POST":
        accion.delete()
        messages.success(request, "Acción eliminada.")
        return redirect("accion_list")
    return render(request, "car/accion_confirm_delete.html", {"accion": accion})


# ----- COMPONENTE + ACCION (precios) -----
def comp_accion_list(request):
    q = (request.GET.get("q") or "").strip()
    items = ComponenteAccion.objects.select_related("componente", "accion").order_by("componente__nombre", "accion__nombre")
    if q:
        items = items.filter(
            Q(componente__nombre__icontains=q) | Q(accion__nombre__icontains=q)
        )
    return render(request, "car/comp_accion_list.html", {"items": items, "q": q})

def comp_accion_create(request):
    if request.method == "POST":
        form = ComponenteAccionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Precio de mano de obra registrado.")
            return redirect("comp_accion_list")
    else:
        form = ComponenteAccionForm()
    return render(request, "car/comp_accion_form.html", {"form": form, "modo": "crear"})

def comp_accion_update(request, pk):
    obj = get_object_or_404(ComponenteAccion, pk=pk)
    if request.method == "POST":
        form = ComponenteAccionForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Precio de mano de obra actualizado.")
            return redirect("comp_accion_list")
    else:
        form = ComponenteAccionForm(instance=obj)
    return render(request, "car/comp_accion_form.html", {"form": form, "modo": "editar", "obj": obj})

def comp_accion_delete(request, pk):
    obj = get_object_or_404(ComponenteAccion, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Registro eliminado.")
        return redirect("comp_accion_list")
    return render(request, "car/comp_accion_confirm_delete.html", {"obj": obj})

# funciones adicionales para incluir repuestos


def sugerir_repuestos(request, diagnostico_id=None):
    """
    Vista única:
    - Si viene diagnostico_id: usa los datos guardados en la BD.
    - Si NO viene diagnostico_id: usa los datos enviados por el request (preview).
    """
    print("entrando a buscar repuestos")

    componentes_ids = []
    veh_marca = veh_modelo = None
    veh_anio = None

    if diagnostico_id:  # 🔹 MODO "DIAGNÓSTICO GUARDADO"
        diag = get_object_or_404(Diagnostico, pk=diagnostico_id)
        veh = diag.vehiculo
        veh_marca, veh_modelo, veh_anio = veh.marca, veh.modelo, veh.anio
        componentes_ids = list(diag.componentes.values_list('id', flat=True))

    else:  # 🔹 MODO "PREVIEW" (sin diagnóstico guardado)
        componentes_ids = request.GET.getlist("componentes_ids", [])
        veh_marca = request.GET.get("marca")
        veh_modelo = request.GET.get("modelo")
        veh_anio = request.GET.get("anio")

    # 1) buscar repuestos vinculados directamente a los componentes
    repuestos_comp = Repuesto.objects.filter(
        componenterepuesto__componente_id__in=componentes_ids
    ).distinct()
    print("buscando en punto 1 ",repuestos_comp)

    # 2) compatibilidad con versión del vehículo
    candidates = repuestos_comp
    if veh_marca and veh_modelo and veh_anio:
        version = VehiculoVersion.objects.filter(
            marca__iexact=veh_marca.strip(),
            modelo__iexact=veh_modelo.strip(),
            anio_desde__lte=veh_anio,
            anio_hasta__gte=veh_anio
        ).first()
        if version:
            repuestos_by_version = Repuesto.objects.filter(aplicaciones__version=version).distinct()
            candidates = (repuestos_comp | repuestos_by_version).distinct()

    print("resultado del punto 2 ",candidates)        
    # 3) enriquecer con stock y precio
    resultados = []
    for r in candidates.select_related().order_by("nombre")[:60]:
        stock_obj = r.stocks.order_by('-ultima_actualizacion').first()
        resultados.append({
            "id": r.id,
            "sku": r.sku,
            "oem": r.oem,
            "nombre": r.nombre,
            "posicion": r.posicion,
            "precio_venta": float(r.precio_venta or 0),
            "stock": stock_obj.stock if stock_obj else 0,
            "disponible": stock_obj.disponible if stock_obj else 0,
            "repuesto_stock_id": stock_obj.id if stock_obj else None,
        })
    print("resultados del punto 3 ",resultados)
    return JsonResponse({"repuestos": resultados})



@csrf_exempt
def agregar_repuesto(request, diagnostico_id):
    """
    Agrega un repuesto al diagnóstico y, si hay stock, lo reserva.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    diag = get_object_or_404(Diagnostico, pk=diagnostico_id)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    repuesto_id = data.get("repuesto_id")
    stock_id = data.get("repuesto_stock_id")
    cantidad = int(data.get("cantidad", 1))

    rep = get_object_or_404(Repuesto, pk=repuesto_id)

    with transaction.atomic():
        repstk = None
        if stock_id:
            repstk = RepuestoEnStock.objects.select_for_update().get(pk=stock_id)
            if repstk.disponible < cantidad:
                return JsonResponse({"error": "Stock insuficiente"}, status=400)
            # Reservar
            repstk.reservado = (repstk.reservado or 0) + cantidad
            repstk.save()
            StockMovimiento.objects.create(
                repuesto_stock=repstk, tipo='reserva', cantidad=cantidad,
                motivo='Reserva desde diagnóstico',
                referencia=f'DIAG-{diag.id}', usuario=request.user if request.user.is_authenticated else None
            )

        dr = DiagnosticoRepuesto.objects.create(
            diagnostico=diag,
            repuesto=rep,
            repuesto_stock=repstk,
            cantidad=cantidad,
            precio_unitario=repstk.precio_venta if repstk and repstk.precio_venta else rep.precio_venta,
            subtotal=(repstk.precio_venta if repstk and repstk.precio_venta else rep.precio_venta or 0) * cantidad,
            reservado=bool(repstk)
        )

    return JsonResponse({"ok": True, "dr_id": dr.id})


def listar_repuestos_diagnostico(request, diagnostico_id):
    """
    Devuelve los repuestos ya agregados a un diagnóstico en formato JSON.
    """
    diag = get_object_or_404(Diagnostico, pk=diagnostico_id)
    drs = DiagnosticoRepuesto.objects.filter(diagnostico=diag).select_related("repuesto")

    repuestos = []
    total = 0

    for dr in drs:
        subtotal = (dr.precio_unitario or 0) * dr.cantidad
        total += subtotal
        repuestos.append({
            "id": dr.id,
            "repuesto_id": dr.repuesto.id,
            "nombre": dr.repuesto.nombre,
            "oem": dr.repuesto.oem,
            "cantidad": dr.cantidad,
            "precio_unitario": float(dr.precio_unitario or 0),
            "subtotal": subtotal,
        })

    return JsonResponse({
        "repuestos": repuestos,
        "total": total
    })
