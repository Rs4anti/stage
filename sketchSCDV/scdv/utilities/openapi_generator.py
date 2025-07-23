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
        Genera documentazione OpenAPI v3.1 per un CPPS orchestrato.
        - ParallelGateway come fork (solo se ha più target)
        - Nessuna duplicazione delle attività
        - Join gateway ignorati
        """

        group_id = doc.get("group_id")
        name = doc.get("name", group_id)
        description = doc.get("description", "")
        workflow_type = doc.get("workflow_type", "sequence")
        owner = doc.get("owner", doc.get("actor", ""))

        # === COMPONENTI ===
        components_names = []
        for comp in doc.get("components", []):
            comp_id = comp.get("id")
            comp_type = comp.get("type")
            if comp_type == "Atomic" and comp_id in atomic_map:
                components_names.append(atomic_map[comp_id].get("name", comp_id))
            elif comp_type == "CPPS" and comp_id in cpps_map:
                components_names.append(cpps_map[comp_id].get("name", comp_id))

        # === STRUTTURA WORKFLOW ===
        structure = {
            "type": workflow_type,
            "steps": []
        }

        # Mappa componenti e controllo duplicazioni
        component_map = {c["id"]: c for c in doc.get("components", [])}
        included_ids = set()

        for comp in doc.get("components", []):
            comp_id = comp.get("id")
            comp_type = comp.get("type")

            if comp_id in included_ids:
                continue

            # === ParallelGateway: fork solo se ha >1 targets ===
            if comp_type == "ParallelGateway":
                targets = comp.get("targets", [])
                if len(targets) > 1:
                    branches = []
                    for tid in targets:
                        if tid in atomic_map:
                            branches.append({
                                "activity": atomic_map[tid].get("name", tid),
                                "id": tid
                            })
                            included_ids.add(tid)  # evita duplicazione
                    structure["steps"].append({
                        "type": "parallel",
                        "gateway_id": comp_id,
                        "branches": branches
                    })
                    included_ids.add(comp_id)
                else:
                    # È probabilmente un join: ignoralo
                    included_ids.add(comp_id)

            # === ExclusiveGateway ===
            elif comp_type == "ExclusiveGateway":
                targets = comp.get("targets", [])
                if targets:
                    branches = []
                    for tid in targets:
                        if tid in atomic_map:
                            branches.append({
                                "activity": atomic_map[tid].get("name", tid),
                                "id": tid
                            })
                            included_ids.add(tid)
                    structure["steps"].append({
                        "type": "exclusive",
                        "gateway_id": comp_id,
                        "branches": branches
                    })
                    included_ids.add(comp_id)

            # === Atomic fuori da gateway ===
            elif comp_type == "Atomic" and comp_id not in included_ids:
                structure["steps"].append({
                    "activity": atomic_map.get(comp_id, {}).get("name", comp_id),
                    "id": comp_id
                })
                included_ids.add(comp_id)

        # === ENDPOINTS ===
        paths = {}
        for ep in doc.get("endpoints", []):
            url = ep.get("url")
            method = ep.get("method", "POST").lower()
            if url:
                paths.setdefault(url, {})[method] = {
                    "summary": description or "CPPS composite service",
                    "responses": {
                        "200": {
                            "description": "Execution completed"
                        }
                    }
                }

        if not paths:
            paths[f"/start-{group_id.lower()}"] = {
                "post": {
                    "summary": f"Start {name} workflow",
                    "responses": {
                        "200": {
                            "description": "Workflow completed successfully"
                        }
                    }
                }
            }

        # === DOCUMENTO OPENAPI COMPLETO ===
        openapi_doc = {
            "openapi": "3.1.0",
            "info": {
                "title": f"CPPS Service: {name}",
                "version": "1.0.0",
                "description": description,
                "x-owner": owner,
                "x-service-type": "cpps",
                "x-cpps-name": name,
                "x-components": components_names,
                "x-workflow": workflow_type
            },
            "x-structure": structure,
            "paths": paths
        }

        return openapi_doc


        

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
