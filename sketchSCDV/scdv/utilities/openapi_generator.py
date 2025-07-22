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


    @staticmethod
    def generate_cpps_openapi(doc, atomic_map, cpps_map):
        """
        doc: documento CPPS da cpps_collection
        atomic_map: dict {task_id: atomic_doc} dei componenti atomic
        cpps_map: dict {group_id: cpps_doc} dei componenti nested cpps
        """

        components_names = []

        for comp_id in doc.get("components", []):
            if comp_id in atomic_map:
                components_names.append(atomic_map[comp_id].get("name", comp_id))
            elif comp_id in cpps_map:
                components_names.append(cpps_map[comp_id].get("name", comp_id))

        # Costruzione paths
        paths = {}
        for idx, ep in enumerate(doc.get("endpoints", [])):
            path = ep.get("url")
            method = ep.get("method", "POST").lower()

            paths.setdefault(path, {})[method] = {
                "summary": doc.get("description", "CPPS composite service"),
                "responses": {
                    "200": {
                        "description": doc.get('description', "Execution successful")
                    }
                }
            }

        # Schema finale
        schema = {
            "openapi": "3.1.0",
            "info": {
                "title": f"CPPS Service: {doc.get('name', doc.get('group_id'))}",
                "version": "1.0.0",
                "description": doc.get('description', ''),
                "x-owner": doc.get("actor", ''),
                "x-service-type": "cpps",
                "x-cpps-name": doc.get("name", ''),
                "x-components": components_names,
                "x-workflow": doc.get("workflow_type", "sequence")
            },
            "paths": paths,
        }

        return schema
    

    @staticmethod
    def generate_cppn_openapi(doc, atomic_map, cpps_map):
        """
        doc: documento CPPN da cppn_collection
        atomic_map: dict {task_id: atomic_doc} dei componenti atomic
        cpps_map: dict {group_id: cpps_doc} dei componenti cpps
        """

        components_names = []
        for comp_id in doc.get("components", []):
            if comp_id in atomic_map:
                components_names.append(atomic_map[comp_id].get("name", comp_id))
            elif comp_id in cpps_map:
                components_names.append(cpps_map[comp_id].get("name", comp_id))

        # Costruzione paths: fallback se vuoto
        paths = {}
        if doc.get("endpoints"):
            for ep in doc["endpoints"]:
                path = ep.get("url")
                method = ep.get("method", "POST").lower()
                paths.setdefault(path, {})[method] = {
                    "summary": doc.get("description", "CPPN composite service"),
                    "responses": {
                        "200": {
                            "description": doc.get('description', "Execution successful")
                        }
                    }
                }
        else:
            paths["/cppn/execute"] = {
                "post": {
                    "summary": f"Execute {doc.get('name', doc.get('group_id'))} network",
                    "responses": {
                        "200": {
                            "description": "Execution successful"
                        }
                    }
                }
            }

        # Schema finale
        schema = {
            "openapi": "3.1.0",
            "info": {
                "title": f"CPPN Service: {doc.get('name', doc.get('group_id'))}",
                "version": "1.0.0",
                "description": doc.get('description', ''),
                "x-actors": doc.get("actors", []),
                "x-cppn-name": doc.get("name", ''),
                "x-service-type": "cppn",
                "x-components": components_names,
                "x-gdpr-map": doc.get("gdpr_map", {}),
                "x-workflow": doc.get("workflow_type", "sequence")
            },
            "paths": paths
        }

        return schema
