from django.urls import path

from . import views
from .views import lista_articoli, atomic_service

urlpatterns = [
    #path("", views.index, name="index"),
    path('lista_articoli/', lista_articoli, name='lista_articoli'),
    path('crea_articolo/', views.crea_articolo, name = 'crea_articolo'),
    path('atomic_service/', atomic_service, name = 'atomic_service'),
]