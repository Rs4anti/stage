from django.db import models
from django.db.models import JSONField

class BPMNProcess(models.Model):
    name = models.CharField(max_length=255)
    xml_content = models.TextField()  # Raw BPMN diagram (XML)
    type = models.CharField(
        max_length=10,
        choices=[('atomic', 'Atomic'), ('cpps', 'CPPS'), ('cppn', 'CPPN')]
    )
    metadata = JSONField()  # Structured metadata (custom extensions)
    created_at = models.DateTimeField(auto_now_add=True)