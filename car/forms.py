from django import forms
from .models import Componente, Cliente, Vehiculo,\
                    Diagnostico


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'telefono']

class VehiculoForm(forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = ['marca', 'modelo', 'anio', 'vin', 'placa', 'descripcion_motor']

class DiagnosticoForm(forms.ModelForm):
    class Meta:
        model = Diagnostico
        fields = ['componente', 'descripcion_problema']



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

