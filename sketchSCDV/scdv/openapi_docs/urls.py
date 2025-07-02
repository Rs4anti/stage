from django.urls import path
from . import views

urlpatterns = [
    path('', views.openapi_docs_page, name='openapi-docs'),
    path('docs/openapidocs/', views.openapi_docs_page, name='openapi-docs-page'),
    #restituisce lo schema OpenAPI di tutti i servizi atomici disponibili.
    #È pensato per fornire una descrizione conforme a OpenAPI degli endpoint
    #REST delle atomic services (servizi per raccolta, elaborazione, visualizzazione e condivisione dati).
    path('schema/atomic/', views.AtomicServiceSchemaView.as_view(), name='atomic-schema'),

     #restituisce lo schema OpenAPI per un servizio atomico specifico,
    #identificato da task_id. Serve per esplorare i dettagli di un singolo servizio.
    path('schema/atomic/<str:task_id>/', views.atomic_service_schema, name='atomic-schema-by-id'),

    #lista degli as con possibilita di vedere api in json o api in swagger
    path('docs/atomic/', views.atomic_docs_page, name='atomic-docs-page'),

    #swagger view openapi di un as
    path('docs/atomic/view/<str:task_id>/', views.swagger_viewer, name='swagger-viewer'),

    #swagger view openapi di un cpps
    path('schema/cpps/<str:group_id>/', views.cpps_service_schema, name='cpps-schema-by-id'),

    # Schema JSON singolo CPPS
    path('schema/cpps/<str:group_id>/', views.cpps_service_schema, name='cpps-schema-by-id'),
 
    path('docs/cpps/', views.cpps_docs_page, name='cpps-docs-page'),
    path('docs/cppn/', views.cppn_docs_page, name='cppn-docs-page'),

    ##swagger view openapi di un cppn
    path('schema/cppn/<str:group_id>/', views.cppn_service_schema, name='cppn-schema-by-id'),
  
    # Schema JSON singolo CPPN
    path('schema/cppn/<str:group_id>/', views.cppn_service_schema, name='cppn-schema-by-id'),

    
]
