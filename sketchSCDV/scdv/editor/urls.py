from django.urls import path
from . import views

urlpatterns = [
    path('', views.data_view_editor, name='editor'),
    path('api/save-diagram/', views.save_diagram, name='save_diagram'),
    path('api/save-atomic-service/', views.save_atomic_service, name='save_atomic_service'),
    #path('api/save-composite-service/', views.save_composite_service, name='save_composite_service'),
    path('api/save-cpps-service/', views.save_cpps_service, name='save_cpps_service'),
    path('api/save-cppn-service/', views.save_cppn_service, name='save_cppn_service'),
]
