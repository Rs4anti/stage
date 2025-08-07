from collections import OrderedDict

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
                "x-diagram_id": data.get("diagram_id"),
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



    from collections import OrderedDict

    @staticmethod
    def generate_cpps_openapi(doc, atomic_map, cpps_map):
        """
        doc: documento CPPS da cpps_collection
        atomic_map: dict {task_id: atomic_doc} dei componenti atomic
        cpps_map: dict {group_id: cpps_doc} dei componenti nested cpps
        """
        components_names = []
        structure = OrderedDict()

        workflow = doc.get("workflow", {})
        workflow_keys = list(workflow.keys())
        workflow_targets = {target for targets in workflow.values() for target in targets}
        all_nodes = list(OrderedDict.fromkeys(workflow_keys + list(workflow_targets)))

        # Build x-structure
        for comp_id in all_nodes:
            node = {
                "next": workflow.get(comp_id, [])
            }

            if comp_id in atomic_map:
                node["type"] = "Atomic"
                node["name"] = atomic_map[comp_id].get("name", comp_id)
                components_names.append(node["name"])

            elif comp_id in cpps_map:
                node["type"] = "CPPS"
                node["name"] = cpps_map[comp_id].get("name", comp_id)
                components_names.append(node["name"])

            else:
                # fallback: gateway or unknown
                comp = next((c for c in doc.get("components", []) if c["id"] == comp_id), {})
                node["type"] = comp.get("type", "Unknown")
                node["name"] = comp.get("name", comp_id)

            structure[comp_id] = node

        # Path
        path = f"/start-{doc.get('group_id', 'group')}".lower()

        paths = {
            path: {
                "post": {
                    "summary": f"Start {doc.get('name', doc.get('group_id'))} workflow",
                    # No parameters
                    "responses": {
                        "200": {
                            "description": "Workflow completed successfully"
                        }
                    }
                }
            }
        }

        # Final schema
        schema = {
            "openapi": "3.1.0",
            "info": {
                "title": f"CPPS Service: {doc.get('name', doc.get('group_id'))}",
                "version": "1.0.0",
                "description": doc.get('description', ''),
                "x-diagram_id": doc.get("diagram_id"),
                "x-owner": doc.get("owner", ''),
                "x-service-type": "cpps",
                "x-cpps-name": doc.get("name", ''),
                "x-components": components_names,
                "x-workflow": doc.get("workflow_type", "sequence")
            },
            "x-structure": structure,
            "paths": paths
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

        for comp in doc.get("components", []):
            if isinstance(comp, dict):
                comp_id = comp.get("id")
                comp_type = comp.get("type")

                if comp_type == "Atomic" and comp_id in atomic_map:
                    components_names.append(atomic_map[comp_id].get("name", comp_id))
                elif comp_type == "CPPS" and comp_id in cpps_map:
                    components_names.append(cpps_map[comp_id].get("name", comp_id))
            else:
                # fallback se comp è una stringa (id puro)
                if comp in atomic_map:
                    components_names.append(atomic_map[comp].get("name", comp))
                elif comp in cpps_map:
                    components_names.append(cpps_map[comp].get("name", comp))

        # Costruzione paths
        paths = {}

        if doc.get("endpoints"):
            for ep in doc["endpoints"]:
                path = ep.get("url")
                method = ep.get("method", "POST").lower()
                paths.setdefault(path, {})[method] = {
                    "summary": doc.get("description", "CPPN composite service"),
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "input_data": {
                                            "type": "string",
                                            "description": "Optional input to trigger CPPN"
                                        }
                                    }
                                }
                            }
                        }
                    },
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
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "input_data": {
                                            "type": "string",
                                            "description": "Optional input to trigger CPPN"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Workflow completed successfully"
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
                "x-diagram_id": doc.get("diagram_id"),
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