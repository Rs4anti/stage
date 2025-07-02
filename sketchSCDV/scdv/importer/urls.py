from django.urls import path
from . import views

urlpatterns = [
    path('', views.importer_home, name='importer_home'),
]
