from django.urls import path
from . import views

urlpatterns = [
    path('', views.data_view_editor, name='editor'),

    path('api/save-diagram/', views.save_diagram),  # POST
    path('api/save-diagram/<str:diagram_id>/', views.save_diagram),  # PUT

    path('api/save-atomic-service/', views.save_atomic_service, name='save_atomic_service'),
    path('api/atomic_service/<str:task_id>/', views.get_atomic_service, name='get_atomic_service'),

    path('api/save-cpps-service/', views.save_cpps_service, name='save_cpps_service'),
    path('api/save-cppn-service/', views.save_cppn_service, name='save_cppn_service'),



    path('api/cppn_service/<str:group_id>/', views.get_cppn_service, name='get_cppn_service'),
    path('api/cpps_service/<str:group_id>/', views.get_cpps_service, name='get_cpps_service'),
    path('api/check-name/', views.check_diagram_name, name='check_diagram_name'),

    path('api/all-services/', views.get_all_services, name='all-services'),
    path('api/delete_group/<str:group_id>/', views.delete_group, name='delete_group'),
    path('api/add-nested-cpps/<str:group_id>/', views.add_nested_cpps),



]
