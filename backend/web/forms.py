from django import forms
from django.contrib.auth.forms import UserCreationForm

from core.models import ConfiguracionSistema, Usuario

_INPUT = "w-full bg-navy-900 border border-navy-700 rounded-md py-2 px-3 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
_INPUT_RED = "w-full bg-navy-900 border border-red-800/50 rounded-md py-2 px-3 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-red-500"
_INPUT_YELLOW = "w-full bg-navy-900 border border-yellow-800/50 rounded-md py-2 px-3 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-yellow-500"
_CHECKBOX = "w-4 h-4 text-blue-600 bg-navy-900 border-navy-700 rounded focus:ring-blue-500"


def _ni(cls, step="0.1"):
    return forms.NumberInput(attrs={"class": cls, "step": step})


class ConfiguracionSistemaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionSistema
        fields = "__all__"
        widgets = {
            "limite_cambio_neumatico_mm":      _ni(_INPUT),
            "filtro_pinchazo_neumatico_mm":    _ni(_INPUT),
            "horas_diarias_operacion":         _ni(_INPUT),
            "prof_fabrica_neumatico":          _ni(_INPUT),
            "limite_turbo_radial":             _ni(_INPUT, "0.00001"),
            "limite_turbo_axial":              _ni(_INPUT, "0.00001"),
            "umbral_alerta_turbo_pct":         _ni(_INPUT, "0.001"),
            "limite_freno_tambor_mm":          _ni(_INPUT_RED, "0.01"),
            "prof_fabrica_freno_tambor_mm":    _ni(_INPUT_RED),
            "limite_freno_disco_mm":           _ni(_INPUT_RED, "0.01"),
            "prof_fabrica_freno_disco_mm":     _ni(_INPUT_RED),
            "limite_freno_tambor_aire_mm":     _ni(_INPUT_RED, "0.01"),
            "prof_fabrica_freno_tambor_aire_mm": _ni(_INPUT_RED),
            "umbral_alerta_freno_pct":         _ni(_INPUT_RED, "0.01"),
            "limite_freno_pastilla_mm":        _ni(_INPUT_RED, "0.01"),
            "prof_fabrica_freno_mm":           _ni(_INPUT_RED),
            "limite_elongacion_cadena_pct":    _ni(_INPUT_YELLOW),
            "umbral_alerta_cadena_pct":        _ni(_INPUT_YELLOW),
            "limite_opacidad_k_default":       _ni(_INPUT, "0.1"),
            "umbral_alerta_opacidad_pct":      _ni(_INPUT, "0.01"),
            "umbral_critico_opacidad_pct":     _ni(_INPUT, "0.01"),
            "meses_periodicidad_opacidad":     _ni(_INPUT, "1"),
        }


class UsuarioCreationForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ("username", "email", "first_name", "last_name", "rol", "departamento", "cargo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": _INPUT})


class UsuarioEditForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ("username", "email", "first_name", "last_name", "rol", "departamento", "cargo", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": _CHECKBOX})
            else:
                field.widget.attrs.update({"class": _INPUT})


from equipos.models import MarcaComponente

class MarcaComponenteForm(forms.ModelForm):
    class Meta:
        model = MarcaComponente
        fields = ("nombre", "tipo", "profundidad_fabrica_mm", "vida_util_horas", "activo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": _CHECKBOX})
            else:
                field.widget.attrs.update({"class": _INPUT})

