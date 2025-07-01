from django.urls import path
from . import views

urlpatterns = [
    path('', views.data_view_editor, name='diagram_list'),  # pagina HTML
    path('api/list/', views.list_diagrams, name='list_diagrams'),
    path('api/<str:diagram_id>/', views.get_diagram, name='get_diagram'),
]
