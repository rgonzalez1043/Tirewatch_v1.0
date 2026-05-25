"""
Context processors para el frontend web de TireWatch.
"""
from rest_framework.authtoken.models import Token


def drf_token(request):
    """
    Inyecta el token DRF del usuario autenticado en el contexto de todos los templates.
    Así el JS puede leerlo en `{{ drf_token }}` y guardarlo en sessionStorage.
    """
    if request.user.is_authenticated:
        token, _ = Token.objects.get_or_create(user=request.user)
        return {"drf_token": token.key}
    return {"drf_token": ""}
