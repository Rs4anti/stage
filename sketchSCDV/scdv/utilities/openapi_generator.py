class OpenAPIGenerator:
    @staticmethod
    def generate_atomic_openapi(data):
        type_mapping = {
            'string': 'string',
            'integer': 'integer',
            'float': 'number',
            'boolean': 'boolean'
        }

        input_schema = {
            f"input_{i+1}": {
                "type": type_mapping.get(param_type, "string"),
                "example": param_value
            }
            for i, (param_value, param_type) in enumerate(data.get("input", {}).items())
        }

        output_schema = {
            f"output_{i+1}": {
                "type": type_mapping.get(param_type, "string"),
                "example": param_value
            }
            for i, (param_value, param_type) in enumerate(data.get("output", {}).items())
        }

        return {
            "openapi": "3.1.0",
            "info": {
                "title": data["name"],
                "version": "1.0.0",
                "x-owner": data["owner"],
                "x-service-type": "atomic",
                "x-atomic-type": data["atomic_type"]
            },
            "paths": {
                data["url"]: {
                    data["method"].lower(): {
                        "summary": f"{data['atomic_type']} atomic service",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": input_schema,
                                        "required": list(input_schema.keys())
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": output_schema
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
