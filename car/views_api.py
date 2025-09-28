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
from .models import Diagnostico, Cliente, Vehiculo,\
                    Componente, Accion, ComponenteAccion,\
                    DiagnosticoComponenteAccion, Repuesto, VehiculoVersion,\
                    DiagnosticoRepuesto, Trabajo
from .forms import ComponenteForm, ClienteForm, VehiculoForm,\
                   DiagnosticoForm, AccionForm, ComponenteAccionForm


import requests
import json
import openpyxl
import re
import pathlib
import os


@login_required
def vehiculo_lookup(request):
    placa = request.GET.get("placa", "").upper().strip()
    if not placa:
        return JsonResponse({"error": "Falta parámetro placa"}, status=400)

    print("Entrando a buscar por placa:", placa)

    url = f"https://chile.getapi.cl/v1/vehicles/plate/{placa}"
    headers = {"X-Api-Key": "e8d1f0d0-a2aa-45cb-98aa-21a667c26f11"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        print("Data extraída de API:", data)

        if not data.get("success"):
            return JsonResponse({"error": "No se encontró vehículo"}, status=404)

        api_data = data.get("data", {})

        # 🔹 Armar descripción de motor
        motor = api_data.get("engine")
        version = api_data.get("version")
        descripcion_motor = None
        if motor and version:
            descripcion_motor = f"Motor {motor} • {version}"
        elif motor:
            descripcion_motor = f"Motor {motor}"
        elif version:
            descripcion_motor = version

        vehiculo_data = {
            "marca": api_data.get("model", {}).get("brand", {}).get("name"),
            "modelo": api_data.get("model", {}).get("name"),
            "anio": api_data.get("year"),
            "vin": api_data.get("vinNumber"),
            "placa": api_data.get("licensePlate"),
            "descripcion_motor": descripcion_motor,
        }

        print("vehiculo_data preparado:", vehiculo_data)
        return JsonResponse(vehiculo_data)

    except Exception as e:
        print("Error en vehiculo_lookup:", str(e))
        return JsonResponse({"error": "Error consultando API"}, status=500)
