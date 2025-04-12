from django.urls import path
from . import views

urlpatterns = [
    path('', views.data_view_editor, name='editor'),
    path('api/save-diagram/', views.save_diagram, name='save_diagram'),
    path('api/save-atomic-service/', views.save_atomic_service, name='save_atomic_service')
]
