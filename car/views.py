from decimal import Decimal,InvalidOperation
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
from django.http import HttpResponse
from django.db.models import Sum
from django.db.models import Q
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from reportlab.lib.styles import ParagraphStyle
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now



from .models import Diagnostico, Cliente, Vehiculo,\
                    Componente, Accion, ComponenteAccion,\
                    DiagnosticoComponenteAccion, Repuesto, VehiculoVersion,\
                    DiagnosticoRepuesto, Trabajo, Mecanico, TrabajoFoto,TrabajoRepuesto,\
                    TrabajoAccion, Venta, VentaItem, RepuestoEnStock, StockMovimiento
from django.forms import modelformset_factory
from django.forms import inlineformset_factory
from .forms import ComponenteForm, ClienteForm, VehiculoForm,\
                   DiagnosticoForm, AccionForm, ComponenteAccionForm,\
                   MecanicoForm, AsignarMecanicosForm, SubirFotoForm,\
                   VentaForm, VentaItemForm


import datetime
import requests
import json
import openpyxl
import re
import pathlib
import os


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("panel_principal")  # cámbialo al dashboard que quieras
    else:
        form = AuthenticationForm()
    return render(request, "registration/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def panel_principal(request):
    clientes = Cliente.objects.all()
    return render(request, 'car/panel_principal.html', {'clientes': clientes})

@login_required
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


@login_required
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





@login_required
def ingreso_exitoso_view(request):
    return render(request, 'car/ingreso_exitoso.html')

@login_required
def eliminar_diagnostico(request, pk):
    diag = get_object_or_404(Diagnostico, pk=pk)
    diag.delete()
    return redirect('ingreso')

@login_required
def editar_diagnostico(request, pk):
    diag = get_object_or_404(Diagnostico, pk=pk)
    diagnostico_form = DiagnosticoForm(request.POST or None, instance=diag)
    if request.method == 'POST' and diagnostico_form.is_valid():
        diagnostico_form.save()
        return redirect('ingreso')
    return render(request, 'car/editar_diagnostico.html', {'form': diagnostico_form})

@login_required
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

@login_required
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

@login_required
def componente_delete(request, pk):
    componente = get_object_or_404(Componente, pk=pk)
    if request.method == 'POST':
        componente.delete()
        messages.success(request, 'Componente eliminado.')
        return redirect('componente_list')
    return render(request, 'car/componentes_confirm_delete.html', {
        'componente': componente
    })


@login_required
def mostrar_plano(request):
    svg_path = pathlib.Path(settings.BASE_DIR) / 'static' / 'images' / 'vehiculo-desde-abajo.svg'
    svg_content = svg_path.read_text(encoding='utf-8')
    return render(request, 'car/plano_interactivo.html', {'svg': svg_content})

@login_required
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

@login_required
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


@login_required
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

@login_required
def lista_diagnosticos(request):
    diagnosticos = Diagnostico.objects.all().select_related(
        'vehiculo__cliente'
    ).prefetch_related(
        'componentes',
        'acciones_componentes__accion',
        'acciones_componentes__componente',
        'repuestos'
    ).order_by('-fecha')

    # Agregar campos calculados manualmente
    for diag in diagnosticos:
        diag.total_mano_obra = sum(dca.precio_mano_obra or 0 for dca in diag.acciones_componentes.all())
        diag.total_repuestos = sum(dr.subtotal or (dr.cantidad * (dr.precio_unitario or 0)) for dr in diag.repuestos.all())
        diag.total_presupuesto = diag.total_mano_obra + diag.total_repuestos

    return render(request, 'car/diagnostico_lista.html', {
        'diagnosticos': diagnosticos
    })

@login_required
def eliminar_diagnostico(request, pk):
    diagnostico = get_object_or_404(Diagnostico, pk=pk)
    if request.method == 'POST':

        diagnostico.delete()
        
        return redirect('lista_diagnosticos')
    return render(request, 'car/diagnostico_eliminar.html', {'diagnostico': diagnostico})

@login_required
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

@login_required
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

@login_required
def accion_list(request):
    q = (request.GET.get("q") or "").strip()
    acciones = Accion.objects.all().order_by("nombre")
    if q:
        acciones = acciones.filter(nombre__icontains=q)
    return render(request, "car/accion_list.html", {"acciones": acciones, "q": q})

@login_required
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

@login_required
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

@login_required
def accion_delete(request, pk):
    accion = get_object_or_404(Accion, pk=pk)
    if request.method == "POST":
        accion.delete()
        messages.success(request, "Acción eliminada.")
        return redirect("accion_list")
    return render(request, "car/accion_confirm_delete.html", {"accion": accion})


# ----- COMPONENTE + ACCION (precios) -----
@login_required
def comp_accion_list(request):
    q = (request.GET.get("q") or "").strip()
    items = ComponenteAccion.objects.select_related("componente", "accion").order_by("componente__nombre", "accion__nombre")
    if q:
        items = items.filter(
            Q(componente__nombre__icontains=q) | Q(accion__nombre__icontains=q)
        )
    return render(request, "car/comp_accion_list.html", {"items": items, "q": q})

@login_required
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

@login_required
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

@login_required
def comp_accion_delete(request, pk):
    obj = get_object_or_404(ComponenteAccion, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Registro eliminado.")
        return redirect("comp_accion_list")
    return render(request, "car/comp_accion_confirm_delete.html", {"obj": obj})

# funciones adicionales para incluir repuestos


@login_required
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


@login_required
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

@login_required
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

@login_required
def exportar_diagnosticos_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Diagnósticos"

    # Encabezados
    ws.append([
        "Fecha", "Cliente", "Teléfono", "Vehículo", "Diagnóstico",
        "Acciones", "Total Mano de Obra",
        "Repuestos", "Total Repuestos",
        "Total Presupuesto"
    ])

    for diag in Diagnostico.objects.all():
        acciones = ", ".join([f"{dca.componente.nombre} - {dca.accion.nombre}" for dca in diag.acciones_componentes.all()])
        repuestos = ", ".join([f"{dr.repuesto.nombre} (x{dr.cantidad})" for dr in diag.repuestos.all()])
        total_mo = diag.total_mano_obra or 0
        total_repuestos = sum([dr.subtotal for dr in diag.repuestos.all()])
        total = total_mo + total_repuestos

        ws.append([
            diag.fecha.strftime("%d-%m-%Y"),
            diag.vehiculo.cliente.nombre,
            diag.vehiculo.cliente.telefono,
            str(diag.vehiculo),
            diag.descripcion_problema,
            acciones,
            total_mo,
            repuestos,
            total_repuestos,
            total
        ])

    # Preparar respuesta HTTP
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="diagnosticos.xlsx"'
    wb.save(response)
    return response


@login_required
def exportar_diagnostico_excel(request, pk):
    diag = get_object_or_404(Diagnostico, pk=pk)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Diagnóstico {diag.pk}"

    ws.append(["Fecha", diag.fecha.strftime("%d-%m-%Y")])
    ws.append(["Cliente", diag.vehiculo.cliente.nombre])
    ws.append(["Teléfono", diag.vehiculo.cliente.telefono])
    ws.append(["Vehículo", str(diag.vehiculo)])
    ws.append(["Descripción", diag.descripcion_problema])
    ws.append([])

    # Acciones
    ws.append(["Acciones realizadas", "Precio"])
    total_mo = 0
    for dca in diag.acciones_componentes.all():
        ws.append([f"{dca.componente.nombre} — {dca.accion.nombre}", dca.precio_mano_obra or 0])
        total_mo += dca.precio_mano_obra or 0
    ws.append(["Total Mano de Obra", total_mo])
    ws.append([])

    # Repuestos
    ws.append(["Repuestos", "Cantidad", "Precio Unitario", "Subtotal"])
    total_rep = 0
    for dr in diag.repuestos.all():
        subtotal = dr.subtotal or (dr.cantidad * (dr.precio_unitario or 0))
        ws.append([dr.repuesto.nombre, dr.cantidad, dr.precio_unitario, subtotal])
        total_rep += subtotal
    ws.append(["Total Repuestos", "", "", total_rep])
    ws.append([])

    ws.append(["TOTAL PRESUPUESTO", total_mo + total_rep])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="diagnostico_{diag.pk}.xlsx"'
    wb.save(response)
    return response

@login_required
def exportar_diagnosticos_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="diagnosticos.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>Reporte de Diagnósticos</b>", styles["Title"]))
    elements.append(Spacer(1, 12))

    data = [["Fecha", "Cliente", "Vehículo","VIN", "Diagnóstico", "Total Presupuesto"]]

    for diag in Diagnostico.objects.all():
        total_mo = diag.total_mano_obra or 0
        total_repuestos = sum([dr.subtotal for dr in diag.repuestos.all()])
        total = total_mo + total_repuestos

        data.append([
            diag.fecha.strftime("%d-%m-%Y"),
            diag.vehiculo.cliente.nombre,
            str(diag.vehiculo),
            diag.vehiculo.vin,
            diag.descripcion_problema,
            f"${total:,}"
        ])

    table = Table(data, colWidths=[80, 100, 120, 150, 80])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)
    return response



@login_required
def exportar_diagnostico_pdf(request, pk):
    diag = get_object_or_404(Diagnostico, pk=pk)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="diagnostico_{diag.pk}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    # Define un nuevo estilo para el texto rojo
    red_text_style = ParagraphStyle(
    name='RedText',
    fontName='Helvetica',
    fontSize=10,
    textColor=colors.red,  # Cambia el color a rojo
    
)
    elements = []

    elements.append(Paragraph(f"<b>Diagnóstico #{diag.pk}</b>", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Fecha:</b> {diag.fecha.strftime('%d-%m-%Y')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Cliente:</b> {diag.vehiculo.cliente.nombre}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Vehículo:</b> {diag.vehiculo}", styles["Normal"]))
    elements.append(Paragraph(f"<b>VIN:</b> {diag.vehiculo.vin}", red_text_style))
    elements.append(Paragraph(f"<b>Descripción:</b> {diag.descripcion_problema}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # Tabla de Acciones
    acciones_data = [["Mano de Obra", "Precio"]]
    total_mo = 0
    for dca in diag.acciones_componentes.all():
        acciones_data.append([f"{dca.componente.nombre} — {dca.accion.nombre}", f"${dca.precio_mano_obra or 0:,}"])
        total_mo += dca.precio_mano_obra or 0
    acciones_data.append(["Total Mano de Obra", f"${total_mo:,}"])

    acciones_table = Table(acciones_data, colWidths=[290, 100])  # Ajustar colWidths
    acciones_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('SIZE', (0, 0), (-1, 0), 14),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(acciones_table)
    elements.append(Spacer(1, 12))

    # Tabla de Repuestos
    repuestos_data = [["Repuesto", "Cantidad", "Unitario", "Precio"]]
    total_rep = 0
    for dr in diag.repuestos.all():
        subtotal = dr.subtotal or (dr.cantidad * (dr.precio_unitario or 0))
        repuestos_data.append([dr.repuesto.nombre, dr.cantidad, f"${dr.precio_unitario:,}", f"${subtotal:,}"])
        total_rep += subtotal
    repuestos_data.append(["Total Repuestos", "", "", f"${total_rep:,}"])

    repuestos_table = Table(repuestos_data, colWidths=[150, 70, 70, 100])  # Ajustar colWidths
    repuestos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('SIZE', (0, 0), (-1, 0), 14),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(repuestos_table)
    elements.append(Spacer(1, 12))

    # Total Presupuesto
    total_presupuesto = total_mo + total_rep
    elements.append(Paragraph(f"<b>TOTAL PRESUPUESTO: ${total_presupuesto:,}</b>", styles["Heading2"]))

    doc.build(elements)
    return response


# ---- CLIENTES ----
class ClienteListView(ListView):
    model = Cliente
    template_name = "car/cliente_list.html"
    context_object_name = "clientes"

class ClienteCreateView(CreateView):
    model = Cliente
    fields = ["nombre", "telefono"]
    template_name = "car/cliente_form.html"
    success_url = reverse_lazy("cliente_list")

class ClienteUpdateView(UpdateView):
    model = Cliente
    fields = ["nombre", "telefono"]
    template_name = "car/cliente_form.html"
    success_url = reverse_lazy("cliente_list")

class ClienteDeleteView(DeleteView):
    model = Cliente
    template_name = "car/cliente_confirm_delete.html"
    success_url = reverse_lazy("cliente_list")

# ---- VEHICULOS ----
class VehiculoListView(ListView):
    model = Vehiculo
    template_name = "car/vehiculo_list.html"
    context_object_name = "vehiculos"

class VehiculoCreateView(CreateView):
    model = Vehiculo
    fields = ["cliente", "placa", "marca", "modelo", "anio", "vin", "descripcion_motor"]
    template_name = "car/vehiculo_form.html"
    success_url = reverse_lazy("vehiculo_list")

class VehiculoUpdateView(UpdateView):
    model = Vehiculo
    fields = ["cliente", "placa", "marca", "modelo", "anio", "vin", "descripcion_motor"]
    template_name = "car/vehiculo_form.html"
    success_url = reverse_lazy("vehiculo_list")

class VehiculoDeleteView(DeleteView):
    model = Vehiculo
    template_name = "car/vehiculo_confirm_delete.html"
    success_url = reverse_lazy("vehiculo_list")

# ---- MecanicoS ----
class MecanicoListView(ListView):
    model = Mecanico
    template_name = "car/mecanico_list.html"
    context_object_name = "mecanicos"

class MecanicoCreateView(CreateView):
    model = Mecanico
    fields = ["user", "especialidad","activo"]
    template_name = "car/mecanico_form.html"
    success_url = reverse_lazy("mecanico_list")

class MecanicoUpdateView(UpdateView):
    model = Mecanico
    fields = ["user", "especialidad","activo"]
    template_name = "car/mecanico_form.html"
    success_url = reverse_lazy("mecanico_list")

class MecanicoDeleteView(DeleteView):
    model = Mecanico
    template_name = "car/mecanico_confirm_delete.html"
    success_url = reverse_lazy("mecanico_list")

@login_required
def aprobar_diagnostico(request, pk):
    diagnostico = get_object_or_404(Diagnostico, pk=pk)

    if diagnostico.estado != "aprobado":
        trabajo = diagnostico.aprobar_y_clonar()
        messages.success(request, f"✅ Diagnóstico aprobado y trabajo #{trabajo.id} creado.")
    else:
        messages.info(request, "ℹ️ Este diagnóstico ya estaba aprobado.")

    return redirect("lista_diagnosticos")

@login_required
def lista_trabajos2(request):
    trabajos = Trabajo.objects.all().select_related(
        'vehiculo__cliente'
    ).prefetch_related(
        'acciones_componentes__accion',
        'acciones_componentes__componente',
        'repuestos'
    ).order_by('-fecha_inicio')

    # Calcular totales igual que en diagnósticos
    for t in trabajos:
        t.total_mano_obra = sum(tca.precio_mano_obra or 0 for tca in t.acciones_componentes.all())
        t.total_repuestos = sum(tr.subtotal or (tr.cantidad * (tr.precio_unitario or 0)) for tr in t.repuestos.all())
        t.total_presupuesto = t.total_mano_obra + t.total_repuestos

    return render(request, 'car/trabajo_lista.html', {
        'trabajos': trabajos
    })


@login_required
def lista_trabajos(request):
    trabajos = Trabajo.objects.all().select_related(
        'vehiculo__cliente'
    ).order_by('-fecha_inicio')

    # Agregar campos calculados
    

    return render(request, 'car/trabajo_lista.html', {
        'trabajos': trabajos
    })




@login_required
def trabajo_detalle(request, pk):
    trabajo = get_object_or_404(Trabajo, pk=pk)

    # Formularios
    asignar_form = AsignarMecanicosForm(instance=trabajo)
    foto_form = SubirFotoForm()

    if request.method == "POST":
        if "asignar_mecanicos" in request.POST:
            asignar_form = AsignarMecanicosForm(request.POST, instance=trabajo)
            if asignar_form.is_valid():
                trabajo = asignar_form.save(commit=False)
                if trabajo.estado == "iniciado":
                    trabajo.estado = "trabajando"
                    trabajo.fecha_inicio = now()
                trabajo.save()
                asignar_form.save_m2m()
                messages.success(request, "Mecánicos asignados y trabajo iniciado.")
                return redirect("trabajo_detalle", pk=trabajo.pk)
        # 🔹 Subir foto
        elif "subir_foto" in request.POST:
            foto_form = SubirFotoForm(request.POST, request.FILES)
            if foto_form.is_valid():
                foto = foto_form.save(commit=False)
                foto.trabajo = trabajo
                foto.save()
                messages.success(request, "Foto subida con éxito.")
                return redirect("trabajo_detalle", pk=trabajo.pk)

        # 🔹 Cambiar estado del trabajo (adelante/atrás)
        elif "cambiar_estado" in request.POST:
            nuevo_estado = request.POST.get("cambiar_estado")
            if nuevo_estado in dict(Trabajo.ESTADOS).keys():
                trabajo.estado = nuevo_estado
                if nuevo_estado == "trabajando" and not trabajo.fecha_inicio:
                    trabajo.fecha_inicio = now()
                if nuevo_estado in ["completado", "entregado"]:
                    trabajo.fecha_fin = now()
                else:
                    trabajo.fecha_fin = None
                trabajo.save()
                messages.success(request, f"Trabajo actualizado a {trabajo.get_estado_display()}.")
            return redirect("trabajo_detalle", pk=trabajo.pk)

        # 🔹 Toggle acción completada / pendiente
        elif "accion_toggle" in request.POST:
            accion_id = request.POST.get("accion_toggle")
            accion = get_object_or_404(TrabajoAccion, id=accion_id, trabajo=trabajo)
            accion.completado = not accion.completado
            accion.fecha = now() if accion.completado else None
            accion.save()
            messages.success(request, f"Acción '{accion.accion.nombre}' actualizada.")
            return redirect("trabajo_detalle", pk=trabajo.pk)

        # 🔹 Toggle repuesto instalado / pendiente
        elif "repuesto_toggle" in request.POST:
            rep_id = request.POST.get("repuesto_toggle")
            rep = get_object_or_404(TrabajoRepuesto, id=rep_id, trabajo=trabajo)
            rep.completado = not rep.completado
            rep.fecha = now() if rep.completado else None
            rep.save()
            messages.success(request, f"Repuesto '{rep.repuesto.nombre}' actualizado.")
            return redirect("trabajo_detalle", pk=trabajo.pk)

    context = {
        "trabajo": trabajo,
        "asignar_form": asignar_form,
        "foto_form": foto_form,
    }
    return render(request, "car/trabajo_detalle.html", context)



@login_required
def pizarra_view(request):
    trabajos = Trabajo.objects.select_related("vehiculo", "vehiculo__cliente")

    context = {
        "iniciados": trabajos.filter(estado="iniciado"),
        "trabajando": trabajos.filter(estado="trabajando"),
        "completados": trabajos.filter(estado="completado"),
        "entregados": trabajos.filter(estado="entregado"),
    }
    return render(request, "car/pizarra_page.html", context)

@login_required
def panel_principal(request):
    trabajos = Trabajo.objects.select_related("vehiculo", "vehiculo__cliente")
    context = {
        "iniciados": trabajos.filter(estado="iniciado"),
        "trabajando": trabajos.filter(estado="trabajando"),
        "completados": trabajos.filter(estado="completado"),
        "entregados": trabajos.filter(estado="entregado"),
    }
    return render(request, "car/panel_principal.html", context)


def venta_crear(request):
    today = datetime.date.today()
    fecha_str = request.GET.get("fecha")
    try:
        filtro_fecha = datetime.date.fromisoformat(fecha_str) if fecha_str else today
    except ValueError:
        filtro_fecha = today

    if request.method == "POST":
        form = VentaForm(request.POST)
        cart_json = request.POST.get("cart_json", "[]")
        try:
            cart = json.loads(cart_json)
        except Exception:
            cart = []
        # Validación mínima del cart
        if not cart:
            messages.error(request, "No hay productos en la venta.")
        elif not form.is_valid():
            messages.error(request, "Corrige los datos del formulario.")
        else:
            # Guardar la venta + items
            with transaction.atomic():
                venta = form.save(commit=False)
                venta.usuario = request.user
                venta.total = Decimal("0.00")
                venta.save()

                total = Decimal("0.00")
                for idx, it in enumerate(cart):
                    try:
                        repuesto_stock_id = int(it.get("repuesto_stock_id"))
                        cantidad = int(it.get("cantidad", 1))
                        precio_unitario = Decimal(str(it.get("precio_unitario", "0")))
                    except (ValueError, TypeError, InvalidOperation) as e:
                        raise ValueError(f"Datos inválidos en item #{idx+1}: {e}")

                    rs = get_object_or_404(RepuestoEnStock, pk=repuesto_stock_id)

                    # validar stock disponible
                    if rs.disponible < cantidad:
                        raise ValueError(f"Stock insuficiente para {rs.repuesto.nombre} (Disponible: {rs.disponible})")

                    subtotal = precio_unitario * cantidad

                    VentaItem.objects.create(
                        venta=venta,
                        repuesto_stock=rs,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario,
                        subtotal=subtotal
                    )

                    # actualizar stock y movimiento
                    rs.stock = rs.stock - cantidad
                    rs.save(update_fields=["stock", "ultima_actualizacion"])
                    StockMovimiento.objects.create(
                        repuesto_stock=rs,
                        tipo="salida",
                        cantidad=cantidad,
                        motivo=f"Venta #{venta.id}",
                        referencia=str(venta.id),
                        usuario=request.user
                    )

                    total += subtotal

                venta.total = total
                venta.pagado = True
                venta.save(update_fields=["total", "pagado"])

            messages.success(request, f"Venta #{venta.id} creada (Total: {total})")
            return redirect("venta_detalle", pk=venta.pk)

    else:
        form = VentaForm()

    # ---- cálculo de arqueo ----
    ventas_hoy = Venta.objects.filter(fecha__date=filtro_fecha, pagado=True)

    total_efectivo = ventas_hoy.filter(metodo_pago="efectivo").aggregate(s=Sum("total"))["s"] or Decimal("0.00")
    total_tarjeta = ventas_hoy.filter(metodo_pago="tarjeta").aggregate(s=Sum("total"))["s"] or Decimal("0.00")
    total_transferencia = ventas_hoy.filter(metodo_pago="transferencia").aggregate(s=Sum("total"))["s"] or Decimal("0.00")
    total_general = total_efectivo + total_tarjeta + total_transferencia

    context = {
        "form": form,
        "today": today.isoformat(),
        "total_efectivo": total_efectivo,
        "total_tarjeta": total_tarjeta,
        "total_transferencia": total_transferencia,
        "total_general": total_general,
        "filtro_fecha": filtro_fecha.isoformat(),
    }
    return render(request, "ventas/venta_crear.html", context)




def venta_detalle(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    return render(request, "ventas/venta_detalle.html", {"venta": venta})


def ventas_historial(request):
    ventas = Venta.objects.all().order_by("-fecha")
    return render(request, "ventas/ventas_historial.html", {"ventas": ventas})


def repuesto_lookup(request):
    q = request.GET.get("q", "").strip()
    results = []

    if q:
        repuestos = RepuestoEnStock.objects.select_related("repuesto").filter(
            Q(repuesto__nombre__icontains=q) |
            Q(repuesto__sku__icontains=q) |
            Q(repuesto__oem__icontains=q) |
            Q(repuesto__codigo_barra__icontains=q) |
            Q(repuesto__marca__icontains=q) |
            Q(repuesto__descripcion__icontains=q)
        )[:20]  # limitar a 20 resultados para que sea rápido

        for r in repuestos:
            text = f"{r.repuesto.sku or '-'} | {r.repuesto.nombre} | {r.repuesto.marca or ''} | Stock: {r.stock}"
            results.append({
                "id": r.id,   # ID de RepuestoEnStock
                "repuesto_nombre": r.repuesto.nombre,  # Nombre del repuesto
                "text": f"{r.repuesto.sku or '-'} | {r.repuesto.nombre} | {r.repuesto.marca or ''} | Stock: {r.stock}",
                "stock": r.stock,  # Stock disponible
                "deposito": r.deposito,  # Depósito
                "precio_venta": r.precio_venta
            })

    print("results :",{"results": results})
    return JsonResponse({"results": results})


class RepuestoListView(ListView):
    model = Repuesto
    template_name = "repuestos/repuesto_list.html"
    context_object_name = "repuestos"


class RepuestoCreateView(CreateView):
    model = Repuesto
    fields = ["nombre", "marca", "descripcion", "medida", "posicion",
              "unidad", "precio_costo", "precio_venta", "codigo_barra", "stock"]
    template_name = "repuestos/repuesto_form.html"
    success_url = reverse_lazy("repuesto_list")


class RepuestoUpdateView(UpdateView):
    model = Repuesto
    fields = ["nombre", "marca", "descripcion", "medida", "posicion",
              "unidad", "precio_costo", "precio_venta", "codigo_barra", "stock"]
    template_name = "repuestos/repuesto_form.html"
    success_url = reverse_lazy("repuesto_list")


class RepuestoDeleteView(DeleteView):
    model = Repuesto
    template_name = "repuestos/repuesto_confirm_delete.html"
    success_url = reverse_lazy("repuesto_list")
