# openapi_docs/urls.py
from django.urls import path
from .views import (
    openapi_docs_home,          # NEW
    atomic_docs_list,           # NEW
    atomic_upsert,
    atomic_oas_latest,
    atomic_oas_version,
    atomic_republish,
)

from .views_ui import SwaggerUIView

app_name = "openapi_docs"

urlpatterns = [

    # Homepage OpenAPI
    path("openapi_docs/", openapi_docs_home, name="openapi-docs-page"),       # NEW

    # Lista Atomic
    path("openapi_docs/docs/atomic/", atomic_docs_list, name="atomic-docs"),  # NEW

    # API Atomic
    path("api/openapi/atomic", atomic_upsert, name="atomic-upsert"),
    path("api/openapi/atomic/<str:service_id>/publish", atomic_republish, name="atomic-republish"),

    # JSON OpenAPI
    path("openapi/services/<str:service_id>", atomic_oas_latest, name="atomic-oas-latest"),
    path("openapi/services/<str:service_id>/versions/<str:version>", atomic_oas_version, name="atomic-oas-version"),

    # Swagger UI
    path("docs/services/<str:service_id>", SwaggerUIView.as_view(), name="atomic-docs-latest"),
    path("docs/services/<str:service_id>/versions/<str:version>", SwaggerUIView.as_view(), name="atomic-docs-version"),
]
