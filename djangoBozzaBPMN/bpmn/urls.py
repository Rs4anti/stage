from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BPMNProcessViewSet

router = DefaultRouter()
router.register(r'bpmn', BPMNProcessViewSet)

urlpatterns = [
        path('api/', include(router.urls)),
    ]