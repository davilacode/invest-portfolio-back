from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.middleware.csrf import get_token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_view(request):
    """GET /api/auth/csrf/ - Asegura cookie CSRF y devuelve el token.

    Respuesta JSON: { csrftoken: "..." }
    El frontend puede leer la cookie 'csrftoken'; esto sólo facilita debug.
    """
    token = get_token(request)
    return Response({'csrftoken': token})


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_protect
def login_view(request):
    """POST /api/auth/login/  {username, password}

    Inicia sesión usando sesiones de Django. Requiere cabecera X-CSRFToken.
    Si ya está autenticado, devuelve datos del usuario actual.
    """
    if request.user.is_authenticated:
        u = request.user
        return Response({'id': u.id, 'username': u.username, 'email': u.email})

    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response({'detail': 'username and password required'}, status=status.HTTP_400_BAD_REQUEST)
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    login(request, user)
    return Response({'id': user.id, 'username': user.username, 'email': user.email})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """POST /api/auth/logout/ - Cierra la sesión actual"""
    logout(request)
    return Response({'detail': 'Logged out'})
