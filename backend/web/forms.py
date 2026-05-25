from django import forms
from core.models import ConfiguracionSistema

class ConfiguracionSistemaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionSistema
        fields = '__all__'
        widgets = {
            'limite_cambio_neumatico_mm': forms.NumberInput(attrs={'class': 'w-full bg-navy-900 border border-navy-700 rounded-md py-2 px-3 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500', 'step': '0.1'}),
            'filtro_pinchazo_neumatico_mm': forms.NumberInput(attrs={'class': 'w-full bg-navy-900 border border-navy-700 rounded-md py-2 px-3 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500', 'step': '0.1'}),
            'horas_diarias_operacion': forms.NumberInput(attrs={'class': 'w-full bg-navy-900 border border-navy-700 rounded-md py-2 px-3 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500', 'step': '0.1'}),
            'prof_fabrica_neumatico': forms.NumberInput(attrs={'class': 'w-full bg-navy-900 border border-navy-700 rounded-md py-2 px-3 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500', 'step': '0.1'}),
            
            'limite_turbo_radial': forms.NumberInput(attrs={'class': 'w-full bg-navy-900 border border-navy-700 rounded-md py-2 px-3 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500', 'step': '0.00001'}),
            'limite_turbo_axial': forms.NumberInput(attrs={'class': 'w-full bg-navy-900 border border-navy-700 rounded-md py-2 px-3 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500', 'step': '0.00001'}),
            'umbral_alerta_turbo_pct': forms.NumberInput(attrs={'class': 'w-full bg-navy-900 border border-navy-700 rounded-md py-2 px-3 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500', 'step': '0.001'}),
        }

from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from core.models import Usuario

class UsuarioCreationForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ('username', 'email', 'first_name', 'last_name', 'rol', 'departamento', 'cargo')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full bg-navy-900 border border-navy-700 rounded-md py-2 px-3 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500'
            })

class UsuarioEditForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ('username', 'email', 'first_name', 'last_name', 'rol', 'departamento', 'cargo', 'is_active')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if type(field.widget) == forms.CheckboxInput:
                field.widget.attrs.update({'class': 'w-4 h-4 text-blue-600 bg-navy-900 border-navy-700 rounded focus:ring-blue-500'})
            else:
                field.widget.attrs.update({
                    'class': 'w-full bg-navy-900 border border-navy-700 rounded-md py-2 px-3 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500'
                })
