"""
TireWatch Web Views
Sirve las páginas HTML del frontend integrado en Django.
La autenticación se maneja por sesión (SessionAuthentication).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q

from core.models import ConfiguracionSistema, Usuario
from turbos.models import ProyeccionTurbo
from neumaticos.models import Proyeccion as ProyeccionNeumaticos
from .forms import ConfiguracionSistemaForm, UsuarioCreationForm, UsuarioEditForm


def login_view(request):
    """Página de login — redirige al dashboard si ya está autenticado."""
    if request.user.is_authenticated:
        return redirect("web:dashboard")
    return render(request, "web/login.html")


@login_required
def dashboard(request):
    """Dashboard general (neumáticos).
    Los datos se cargan vía fetch JS al endpoint /api/neumaticos/dashboard/.
    """
    return render(request, "web/dashboard.html")


@login_required
def turbos_dashboard(request):
    """Dashboard Predictivo de Turbocompresores."""
    proyecciones = ProyeccionTurbo.objects.select_related("equipo").all()
    stats = proyecciones.aggregate(
        total=Count("id"),
        criticos=Count("id", filter=Q(estado="CRITICO")),
        atencion=Count("id", filter=Q(estado="ATENCION")),
        ok=Count("id", filter=Q(estado="OK")),
    )
    config = ConfiguracionSistema.load()
    context = {
        "proyecciones": proyecciones,
        "stats": stats,
        "config": config,
        "limite_rad_atencion": config.limite_turbo_radial * config.umbral_alerta_turbo_pct,
        "limite_ax_atencion": config.limite_turbo_axial * config.umbral_alerta_turbo_pct,
    }
    return render(request, "web/turbos_dashboard.html", context)


@login_required(login_url="/login/")
def importar(request):
    return render(request, "web/importar.html")


@login_required(login_url="/login/")
def terreno(request):
    return render(request, "web/terreno.html")


@login_required(login_url="/login/")
def equipo_detalle(request, equipo_id):
    return render(request, "web/equipo_detalle.html", {"numero": equipo_id})


@login_required(login_url="/login/")
def modulos(request):
    modulos_activos = [
        {"icono": "🛞", "titulo": "Neumáticos", "descripcion": "Desgaste y proyección de cambio", "url": "/", "activo": True},
        {"icono": "⚙️", "titulo": "Turbos", "descripcion": "Juego Radial/Axial y proyección de overhaul", "url": "/turbos/", "activo": True},
    ]
    modulos_futuros = [
        {"icono": "🛑", "titulo": "Frenos", "descripcion": "Desgaste de pastillas y discos"},
        {"icono": "⛓️", "titulo": "Cadenas", "descripcion": "Elongación y ciclos GPCO"},
        {"icono": "📄", "titulo": "Reportes PDF", "descripcion": "Reportes automáticos"},
        {"icono": "📱", "titulo": "App Móvil", "descripcion": "Flutter para terreno"},
    ]
    return render(request, "web/modulos.html", {"modulos_activos": modulos_activos, "modulos_futuros": modulos_futuros})


@login_required(login_url="/login/")
def ayuda(request):
    """Página de documentación técnica y tutoriales de medición."""
    return render(request, "web/ayuda.html")


@login_required(login_url="/login/")
def configuracion_sistema(request):
    if request.user.rol != "admin":
        messages.error(request, "No tienes permisos para acceder a la configuración del sistema.")
        return redirect("web:dashboard")

    config = ConfiguracionSistema.load()

    if request.method == "POST":
        form = ConfiguracionSistemaForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración guardada exitosamente. Los próximos cálculos utilizarán estos nuevos límites.")
            return redirect("web:configuracion_sistema")
    else:
        form = ConfiguracionSistemaForm(instance=config)

    return render(request, "web/configuracion.html", {"form": form})


@login_required(login_url="/login/")
def usuarios_list(request):
    if request.user.rol != "admin":
        messages.error(request, "Acceso denegado: solo administradores.")
        return redirect("web:dashboard")

    usuarios = Usuario.objects.all().order_by("-date_joined")
    return render(request, "web/usuarios_list.html", {"usuarios": usuarios})


@login_required(login_url="/login/")
def usuario_crear(request):
    if request.user.rol != "admin":
        messages.error(request, "Acceso denegado.")
        return redirect("web:dashboard")

    if request.method == "POST":
        form = UsuarioCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario creado exitosamente.")
            return redirect("web:usuarios_list")
    else:
        form = UsuarioCreationForm()

    return render(request, "web/usuario_form.html", {"form": form, "titulo": "Crear Nuevo Usuario"})


@login_required(login_url="/login/")
def usuario_editar(request, user_id):
    if request.user.rol != "admin":
        messages.error(request, "Acceso denegado.")
        return redirect("web:dashboard")

    usuario = get_object_or_404(Usuario, id=user_id)

    if request.method == "POST":
        form = UsuarioEditForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f"Usuario {usuario.username} actualizado.")
            return redirect("web:usuarios_list")
    else:
        form = UsuarioEditForm(instance=usuario)

    return render(request, "web/usuario_form.html", {"form": form, "titulo": f"Editar Usuario: {usuario.username}"})


@login_required(login_url="/login/")
def reporte_proyecciones(request):
    """
    Reporte imprimible de todas las proyecciones activas (neumáticos + turbos).
    Accesible en /reportes/ — usar Ctrl+P / Imprimir en el navegador para generar PDF.
    """
    proy_neumaticos = list(
        ProyeccionNeumaticos.objects
        .select_related("equipo")
        .order_by("horas_restantes")
    )
    proy_turbos = (
        ProyeccionTurbo.objects
        .select_related("equipo")
        .order_by("horas_motor_restantes")
    )
    config = ConfiguracionSistema.load()

    # Pre-calcular stats de neumáticos en Python (los templates Django no permiten
    # acumuladores mutables con {% with %}, lo que produce conteos incorrectos)
    stats_neu = {"total": len(proy_neumaticos), "criticos": 0, "atencion": 0, "ok": 0}
    for p in proy_neumaticos:
        stats_neu[p.estado] += 1  # p.estado retorna 'critico' | 'atencion' | 'ok'

    # Stats de turbos vía ORM (son simples porque el estado es un campo de BD)
    stats_turb = proy_turbos.aggregate(
        total=Count("id"),
        criticos=Count("id", filter=Q(estado="CRITICO")),
        atencion=Count("id", filter=Q(estado="ATENCION")),
        ok=Count("id", filter=Q(estado="OK")),
    )

    context = {
        "proy_neumaticos": proy_neumaticos,
        "proy_turbos": proy_turbos,
        "config": config,
        "usuario": request.user,
        "stats_neu": stats_neu,
        "stats_turb": stats_turb,
    }
    return render(request, "web/reporte.html", context)
