from rest_framework import serializers
from .models import BPMNProcess

class BPMNProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = BPMNProcess
        fields = '__all__'