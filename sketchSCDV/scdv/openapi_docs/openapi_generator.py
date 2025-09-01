class OpenAPIGenerator:
    """
    Genera una OpenAPI 3.1 per un Atomic Service a partire dal documento atomic:
    {
      "task_id", "diagram_id", "name", "atomic_type", "owner",
      "method", "url", "input": { "<example>": "<type>" }, "output": { ... }
    }
    """
    @staticmethod
    def _cast_example(value: str, oas_type: str):
        if oas_type == 'integer':
            try: return int(value)
            except: return value
        if oas_type == 'number':
            try: return float(value)
            except: return value
        if oas_type == 'boolean':
            v = str(value).lower()
            if v in ('true','1','yes','y'): return True
            if v in ('false','0','no','n'): return False
            return value
        return value  # string

    @staticmethod
    def generate_atomic_openapi(doc: dict, version: str = "1.0.0") -> dict:
        mapping = {'string':'string','integer':'integer','float':'number','number':'number','boolean':'boolean'}

        # Costruzione proprietà input/output
        in_props, out_props = {}, {}
        for i, (ex, typ) in enumerate(doc.get("input", {}).items(), start=1):
            t = mapping.get(typ, "string")
            in_props[f"input_{i}"] = {"type": t, "example": OpenAPIGenerator._cast_example(ex, t)}
        for i, (ex, typ) in enumerate(doc.get("output", {}).items(), start=1):
            t = mapping.get(typ, "string")
            out_props[f"output_{i}"] = {"type": t, "example": OpenAPIGenerator._cast_example(ex, t)}

        method = doc["method"].lower()
        op = {"summary": f"{doc['atomic_type']} atomic service"}

        if method == "get":
            # Parametri in query
            op["parameters"] = [{
                "in": "query", "name": k, "required": True,
                "schema": {"type": v["type"]},
                "example": v.get("example")
            } for k, v in in_props.items()]
        else:
            # Body JSON
            op["requestBody"] = {
                "required": True,
                "content": {"application/json": {
                    "schema": {"$ref":"#/components/schemas/AtomicInput"},
                    "examples": {"default":{"value":{k:v["example"] for k,v in in_props.items()}}}
                }}
            }

        # Risposte
        op["responses"] = {
            "200": {"description":"Success","content":{"application/json":{
                "schema":{"$ref":"#/components/schemas/AtomicOutput"},
                "examples":{"default":{"value":{k:v["example"] for k,v in out_props.items()}}}
            }}}
        }

        # Documento OpenAPI
        oas = {
            "openapi": "3.1.0",
            "jsonSchemaDialect": "https://spec.openapis.org/oas/3.1/dialect/base",
            "info": {
                "title": doc["name"],
                "version": version,
                "x-service_id": doc.get("task_id"),
                "x-diagram_id": doc.get("diagram_id"),
                "x-owner": doc["owner"],
                "x-service-type": "atomic",
                "x-atomic-type": doc["atomic_type"]
            },
            "paths": { doc["url"]: { method: op } },
            "components": {
                "securitySchemes": {
                    "bearerAuth": { "type":"http", "scheme":"bearer", "bearerFormat":"JWT" }
                },
                "schemas": {
                    "AtomicInput": { "type":"object","properties": in_props,"required": list(in_props.keys()) },
                    "AtomicOutput": { "type":"object","properties": out_props }
                }
            },
            "security": [{"bearerAuth": []}]
        }
        return oas