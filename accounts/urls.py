from django.urls import path
from .views import csrf_view, login_view, logout_view, RegisterUserView

urlpatterns = [
    path('csrf/', csrf_view, name='csrf'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', RegisterUserView.as_view(), name='register'),
]
