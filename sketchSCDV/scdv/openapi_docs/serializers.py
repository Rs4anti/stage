from rest_framework import serializers

class AtomicUpsertSerializer(serializers.Serializer):
    diagram_id = serializers.CharField()
    task_id = serializers.CharField()       # = service_id
    name = serializers.CharField()
    atomic_type = serializers.CharField()   # collect | dispatch | process&monitor | display
    method = serializers.ChoiceField(choices=['GET','POST','PUT','PATCH','DELETE'])
    url = serializers.CharField()
    owner = serializers.CharField()
    # input/output: { "<example>": "<type>" }  es: { "100": "integer", "abc": "string" }
    input = serializers.DictField(child=serializers.CharField())
    output = serializers.DictField(child=serializers.CharField())
