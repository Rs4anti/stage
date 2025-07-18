class OpenAPIGenerator:
    @staticmethod
    def generate_atomic_openapi(data):
        return {
            "openapi": "3.1.0",
            "info": {
                "title": data["name"],
                "version": "1.0.0",
                "x-service-type": "atomic",
                "x-owner": data["owner"],
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
                                        "input": {k: {"type": "string"} for k in data["input_params"]},
                                        "required": data["input_params"]
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
                                            "output": {k: {"type": "string"} for k in data["output_params"]}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

    @staticmethod
    def generate_cpps_openapi(data, atomic_services):
        # TODO: implementa la logica per CPPS
        pass

    @staticmethod
    def generate_cppn_openapi(data, cpps_services):
        # TODO: implementa la logica per CPPN
        pass
