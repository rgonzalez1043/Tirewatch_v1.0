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
from equipos.models import MarcaComponente
from turbos.models import ProyeccionTurbo
from frenos.models import ProyeccionFreno
from cadenas.models import ProyeccionCadena
from neumaticos.models import Proyeccion as ProyeccionNeumaticos
from .forms import ConfiguracionSistemaForm, UsuarioCreationForm, UsuarioEditForm, MarcaComponenteForm


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


@login_required
def importar(request):
    return render(request, "web/importar.html")


@login_required
def terreno(request):
    config = ConfiguracionSistema.load()
    return render(request, "web/terreno.html", {"config": config})


@login_required
def equipo_detalle(request, equipo_id):
    return render(request, "web/equipo_detalle.html", {"numero": equipo_id})


@login_required
def modulos(request):
    modulos_activos = [
        {"icono": "🛥", "titulo": "Neumáticos", "descripcion": "Desgaste y proyección de cambio", "url": "/", "activo": True},
        {"icono": "⚙️", "titulo": "Turbos", "descripcion": "Juego Radial/Axial y proyección de overhaul", "url": "/turbos/", "activo": True},
        {"icono": "🛑", "titulo": "Frenos", "descripcion": "Desgaste de pastillas — Kalmar T2, Terberg, Konecranes", "url": "/frenos/", "activo": True},
        {"icono": "⛓️", "titulo": "Cadenas", "descripcion": "Elongación de cadenas de spreader — Taylor", "url": "/cadenas/", "activo": True},
    ]
    modulos_futuros = [
        {"icono": "📱", "titulo": "App Móvil", "descripcion": "Flutter para registro en terreno", "url": "/app-movil/"},
        {"icono": "📤", "titulo": "Exportación Avanzada", "descripcion": "Reportes Excel y bi-direccionales"},
    ]
    return render(request, "web/modulos.html", {"modulos_activos": modulos_activos, "modulos_futuros": modulos_futuros})


@login_required
def ayuda(request):
    """Página de documentación técnica y tutoriales de medición."""
    return render(request, "web/ayuda.html")


@login_required
def configuracion_sistema(request):
    if request.user.rol != "admin":
        messages.error(request, "No tienes permisos para acceder a la configuración del sistema.")
        return redirect("web:dashboard")

    config = ConfiguracionSistema.load()
    marcas = MarcaComponente.objects.all().order_by("tipo", "nombre")

    if request.method == "POST":
        form = ConfiguracionSistemaForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración guardada exitosamente. Los próximos cálculos utilizarán estos nuevos límites.")
            return redirect("web:configuracion_sistema")
    else:
        form = ConfiguracionSistemaForm(instance=config)

    marca_form = MarcaComponenteForm()
    return render(request, "web/configuracion.html", {
        "form": form,
        "marcas": marcas,
        "marca_form": marca_form,
    })


@login_required
def marca_crear(request):
    if request.user.rol != "admin":
        messages.error(request, "Acceso denegado.")
        return redirect("web:dashboard")

    if request.method == "POST":
        form = MarcaComponenteForm(request.POST)
        if form.is_valid():
            marca = form.save()
            messages.success(request, f"Marca '{marca.nombre}' ({marca.get_tipo_display()}) agregada exitosamente.")
        else:
            messages.error(request, "Error al agregar la marca. Verifique los datos.")
    return redirect("web:configuracion_sistema")


@login_required
def marca_eliminar(request, marca_id):
    if request.user.rol != "admin":
        messages.error(request, "Acceso denegado.")
        return redirect("web:dashboard")

    marca = get_object_or_404(MarcaComponente, id=marca_id)
    nombre = marca.nombre
    marca.delete()
    messages.success(request, f"Marca '{nombre}' eliminada del sistema.")
    return redirect("web:configuracion_sistema")


@login_required
def usuarios_list(request):
    if request.user.rol != "admin":
        messages.error(request, "Acceso denegado: solo administradores.")
        return redirect("web:dashboard")

    usuarios = Usuario.objects.all().order_by("-date_joined")
    return render(request, "web/usuarios_list.html", {"usuarios": usuarios})


@login_required
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


@login_required
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


@login_required
def reporte_proyecciones(request):
    """
    Reporte imprimible de todas las proyecciones activas (neumáticos + turbos + frenos + cadenas).
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
    proy_frenos = (
        ProyeccionFreno.objects
        .select_related("equipo")
        .order_by("horas_restantes")
    )
    proy_cadenas = (
        ProyeccionCadena.objects
        .select_related("equipo")
        .order_by("horas_restantes")
    )
    config = ConfiguracionSistema.load()

    # Pre-calcular stats de neumáticos en Python
    stats_neu = {"total": len(proy_neumaticos), "criticos": 0, "atencion": 0, "ok": 0}
    for p in proy_neumaticos:
        st = str(getattr(p, "estado", "") or "ok").lower()
        if "critico" in st:
            stats_neu["criticos"] += 1
        elif "atencion" in st or "atencion" in st:
            stats_neu["atencion"] += 1
        else:
            stats_neu["ok"] += 1

    stats_turb = proy_turbos.aggregate(
        total=Count("id"),
        criticos=Count("id", filter=Q(estado="CRITICO")),
        atencion=Count("id", filter=Q(estado="ATENCION")),
        ok=Count("id", filter=Q(estado="OK")),
    )

    stats_frenos = proy_frenos.aggregate(
        total=Count("id"),
        criticos=Count("id", filter=Q(estado="CRITICO")),
        atencion=Count("id", filter=Q(estado="ATENCION")),
        ok=Count("id", filter=Q(estado="OK")),
    )

    stats_cadenas = proy_cadenas.aggregate(
        total=Count("id"),
        criticos=Count("id", filter=Q(estado="CRITICO")),
        atencion=Count("id", filter=Q(estado="ATENCION")),
        ok=Count("id", filter=Q(estado="OK")),
    )

    context = {
        "proy_neumaticos": proy_neumaticos,
        "proy_turbos": proy_turbos,
        "proy_frenos": proy_frenos,
        "proy_cadenas": proy_cadenas,
        "config": config,
        "usuario": request.user,
        "stats_neu": stats_neu,
        "stats_turb": stats_turb,
        "stats_frenos": stats_frenos,
        "stats_cadenas": stats_cadenas,
    }
    return render(request, "web/reporte.html", context)


@login_required
def frenos_dashboard(request):
    """Dashboard de Frenos. Datos cargados vía fetch JS al endpoint /api/frenos/."""
    config = ConfiguracionSistema.load()
    proyecciones = ProyeccionFreno.objects.select_related("equipo").all()
    stats = proyecciones.aggregate(
        total=Count("id"),
        criticos=Count("id", filter=Q(estado="CRITICO")),
        atencion=Count("id", filter=Q(estado="ATENCION")),
        ok=Count("id", filter=Q(estado="OK")),
    )
    context = {
        "proyecciones": proyecciones,
        "stats": stats,
        "config": config,
    }
    return render(request, "web/frenos_dashboard.html", context)


@login_required
def cadenas_dashboard(request):
    """Dashboard de Cadenas. Datos cargados vía fetch JS al endpoint /api/cadenas/."""
    config = ConfiguracionSistema.load()
    proyecciones = ProyeccionCadena.objects.select_related("equipo").all()
    stats = proyecciones.aggregate(
        total=Count("id"),
        criticos=Count("id", filter=Q(estado="CRITICO")),
        atencion=Count("id", filter=Q(estado="ATENCION")),
        ok=Count("id", filter=Q(estado="OK")),
    )
    context = {
        "proyecciones": proyecciones,
        "stats": stats,
        "config": config,
    }
    return render(request, "web/cadenas_dashboard.html", context)


@login_required
def app_movil(request):
    """Página informativa de la App Móvil TireWatch (Flutter)."""
    return render(request, "web/app_movil.html")
