from rest_framework import viewsets
from .models import BPMNProcess
from .serializers import BPMNProcessSerializer

class BPMNProcessViewSet(viewsets.ModelViewSet):
    queryset = BPMNProcess.objects.all()
    serializer_class = BPMNProcessSerializer