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

class CPPSComponentSerializer(serializers.Serializer):
    """
    Un componente del CPPS. Per ora accettiamo:
    - Atomic: riferimento a un servizio atomico
    - CPPS: (eventuale) nesting futuro
    - External: step esterni (es. hook)
    """
    id = serializers.CharField()
    type = serializers.ChoiceField(choices=["Atomic", "CPPS", "External"], default="Atomic")


class CPPSEndpointSerializer(serializers.Serializer):
    """
    Endpoint opzionali a supporto del CPPS (es. webhook, callback).
    Non sono richiesti; manteniamo schema permissivo ma tipizzato.
    """
    name = serializers.CharField(required=False, allow_blank=True)
    url = serializers.URLField()
    method = serializers.ChoiceField(choices=["GET", "POST", "PUT", "PATCH", "DELETE"], default="POST")
    description = serializers.CharField(required=False, allow_blank=True)


class CPPSUpsertSerializer(serializers.Serializer):
    """
    Serializer per l'upsert di documenti CPPS su Mongo e per la
    generazione della specifica OpenAPI 3.1 coerente con il paper.
    """
    group_id = serializers.CharField()
    diagram_id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)
    owner = serializers.CharField()  # attore responsabile (actor nel paper)

    group_type = serializers.ChoiceField(choices=["CPPS"], default="CPPS")

    components = serializers.ListField(child=CPPSComponentSerializer(), allow_empty=False)

    # Esempio dal tuo documento:
    # "workflow": { "Activity_07o8s0a": ["Activity_16oz7n2"] }
    workflow = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        allow_empty=False
    )

    workflow_type = serializers.ChoiceField(choices=["sequence", "parallel", "custom"], default="sequence")

    endpoints = serializers.ListField(
        child=CPPSEndpointSerializer(),
        required=False,
        default=list
    )

    def validate(self, data):
        """
        Cross-field validation:
        - component ids univoche e non vuote
        - chiavi/valori del workflow appartengono ai component ids
        - group_type deve essere 'CPPS'
        - niente self-loop evidenti in workflow (opzionale, ma utile)
        """
        # 1) component ids
        comp_ids = [c["id"] for c in data.get("components", [])]
        if any(not cid.strip() for cid in comp_ids):
            raise serializers.ValidationError("Tutti i component.id devono essere non vuoti.")
        if len(set(comp_ids)) != len(comp_ids):
            raise serializers.ValidationError("I component.id devono essere univoci nel CPPS.")

        # 2) workflow references
        wf = data.get("workflow", {})
        unknown = set()

        for src, nxts in wf.items():
            if src not in comp_ids:
                unknown.add(src)
            for target in nxts:
                if target not in comp_ids:
                    unknown.add(target)
                if target == src:
                    raise serializers.ValidationError(f"Self-loop non consentito sul nodo '{src}'.")

        if unknown:
            raise serializers.ValidationError(
                f"Workflow fa riferimento a id non presenti in components: {sorted(list(unknown))}"
            )

        # 3) tipo
        if data.get("group_type") != "CPPS":
            raise serializers.ValidationError("group_type deve essere 'CPPS'.")

        return data
