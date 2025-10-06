from django import forms
from .models import Componente, Cliente, Vehiculo,\
                    Diagnostico,Accion, ComponenteAccion,\
                    Mecanico, Trabajo, TrabajoFoto,\
                    Venta, VentaItem, Repuesto

class MecanicoForm(forms.ModelForm):
    class Meta:
        model = Mecanico
        fields = ['user', 'especialidad','activo']


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'telefono']

class VehiculoForm(forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = ['marca', 'modelo', 'anio', 'vin', 'placa', 'descripcion_motor']

#class DiagnosticoForm2(forms.ModelForm):
#    class Meta:
#        model = Diagnostico
#        fields = ['componente', 'descripcion_problema']

class DiagnosticoForm(forms.ModelForm):
    class Meta:
        model = Diagnostico
        fields = ['descripcion_problema']  # eliminamos 'vehiculo' porque se asigna en la vista
        widgets = {
            'componentes': forms.CheckboxSelectMultiple,  # o SelectMultiple si prefieres lista desplegable
        }


class ComponenteForm(forms.ModelForm):
    class Meta:
        model = Componente
        fields = ['nombre', 'activo', 'padre']  # <- sin descripcion
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            #'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'padre': forms.Select(attrs={'class': 'form-select'}),
        }

        def clean(self):
            cleaned = super().clean()
            nombre = (cleaned.get('nombre') or '').strip()
            padre  = cleaned.get('padre')
            qs = Componente.objects.filter(padre=padre, nombre__iexact=nombre)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                # Error “lindo” arriba del formulario
                raise forms.ValidationError("Ya existe un componente con ese nombre bajo el mismo padre.")
            return cleaned

class AccionForm(forms.ModelForm):
    class Meta:
        model = Accion
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Desarmar / Revisar / Calibrar ..."})
        }

    def clean_nombre(self):
        n = (self.cleaned_data.get("nombre") or "").strip()
        if not n:
            raise forms.ValidationError("El nombre es obligatorio.")
        # normaliza para evitar duplicados por mayúsculas/minúsculas
        if Accion.objects.exclude(pk=self.instance.pk).filter(nombre__iexact=n).exists():
            raise forms.ValidationError("Ya existe una acción con ese nombre.")
        return n


class ComponenteAccionForm(forms.ModelForm):
    componente = forms.ModelChoiceField(
        queryset=Componente.objects.all().order_by("nombre"),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    accion = forms.ModelChoiceField(
        queryset=Accion.objects.all().order_by("nombre"),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    precio_mano_obra = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"})
    )

    class Meta:
        model = ComponenteAccion
        fields = ["componente", "accion", "precio_mano_obra"]

    def clean(self):
        cleaned = super().clean()
        comp = cleaned.get("componente")
        acc = cleaned.get("accion")
        if comp and acc:
            exists = ComponenteAccion.objects.exclude(pk=self.instance.pk).filter(
                componente=comp, accion=acc
            ).exists()
            if exists:
                raise forms.ValidationError("Ya existe un precio para ese Componente + Acción.")
        return cleaned

class AsignarMecanicosForm(forms.ModelForm):
    mecanicos = forms.ModelMultipleChoiceField(
        queryset=Mecanico.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Selecciona los mecánicos"
    )

    class Meta:
        model = Trabajo
        fields = ["mecanicos"]


class SubirFotoForm(forms.ModelForm):
    class Meta:
        model = TrabajoFoto
        fields = ["imagen", "descripcion"]



class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ["cliente", "metodo_pago"]

class VentaItemForm(forms.ModelForm):
    class Meta:
        model = VentaItem
        fields = ["repuesto_stock", "cantidad", "precio_unitario", "subtotal"]

class RepuestoForm(forms.ModelForm):
    class Meta:
        model = Repuesto
        fields = [
            "sku", "oem", "referencia", "nombre", "marca",
            "descripcion", "medida", "posicion", "unidad",
            "precio_costo", "precio_venta", "codigo_barra", "stock"
        ]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }