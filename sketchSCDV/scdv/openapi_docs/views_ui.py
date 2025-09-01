from django.views.generic import TemplateView
from django.urls import reverse

class SwaggerUIView(TemplateView):
    template_name = "openapi_docs/swagger_ui.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        service_id = self.kwargs["service_id"]
        version = self.kwargs.get("version")
        # Se è passata una versione, usiamo l'endpoint versionato,
        # altrimenti la latest.
        ctx["spec_url"] = reverse(
            "openapi_docs:atomic-oas-version",
            args=[service_id, version]
        ) if version else reverse(
            "openapi_docs:atomic-oas-latest",
            args=[service_id]
        )
        return ctx
