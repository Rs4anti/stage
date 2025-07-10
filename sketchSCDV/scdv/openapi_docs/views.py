from django.shortcuts import render
from mongodb_handler import atomic_services_collection, cpps_collection, cppn_collection
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.decorators import api_view

def openapi_docs_page(request):
    return render(request, 'openapi_docs/openapi_docs.html')

def atomic_docs_page(request):
    services = list(atomic_services_collection.find())
    base_url = request.build_absolute_uri('/').rstrip('/')

    for s in services:
        s['schema_url'] = f"{base_url}/openapi_docs/schema/atomic/{s['task_id']}/"

    return render(request, 'openapi_docs/atomic_docs.html', {'services': services})

def swagger_viewer(request, task_id):
    base_url = request.build_absolute_uri('/').rstrip('/')
    schema_type = request.GET.get("type", "atomic")  # "atomic", "cpps", "cppn"

    if schema_type not in ["atomic", "cpps", "cppn"]:
        schema_type = "atomic"

    schema_url = f"{base_url}/openapi_docs/schema/{schema_type}/{task_id}/"
    return render(request, 'openapi_docs/swagger_viewer.html', {'schema_url': schema_url})

class AtomicServiceSchemaView(APIView):
    """
    Dynamic OpenAPI 3.1 schema for atomic services stored in MongoDB.
    """

    def get(self, request):
        paths = {}
        for doc in atomic_services_collection.find():
            path = doc.get("url")
            method = doc.get("method", "POST").lower()
            input_params = doc.get("input_params", [])
            output_params = doc.get("output_params", [])

            paths.setdefault(path, {})[method] = {
                "atomic-name": doc.get("name", "unnamed-service"),
                "summary": f"{doc.get('atomic_type')} atomic service",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {p: {"type": "string"} for p in input_params},
                                "required": input_params,
                                "x-owner": doc.get("owner", "unknown")
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
                                    "properties": {p: {"type": "string"} for p in output_params}
                                }
                            }
                        }
                    }
                },
                "tags": ["atomic"],
                "x-atomic-type": doc.get("atomic_type")
            }

        openapi = {
            "openapi": "3.1.0",
            "info": {
                "title": "Atomic Services API",
                "version": "1.0.0"
            },
            "paths": paths
        }
        return Response(openapi)
    


@api_view(['GET'])
def atomic_service_schema(request, task_id):
    atomic = atomic_services_collection.find_one({'task_id': task_id})
    if not atomic:
        return JsonResponse({'error': 'Atomic service not found'}, status=404)

    schema = {
        'openapi': '3.1.0',
        'info': {
            'title': f"Atomic Service: {atomic.get('name', task_id)}",
            'version': '1.0.0',
            'x-atomic-type': atomic.get('atomic_type', ''),
            "x-owner": atomic.get("owner", "unknown"),
            'x-atomic-name': atomic.get('name', task_id),
        },
        'paths': {
            atomic['url']: {
                atomic.get('method', 'POST').lower(): {
                    'summary': f"{atomic.get('atomic_type', 'atomic')} service",
                    'requestBody': {
                        'required': True,
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            k: {'type': 'string'} for k in atomic.get('input_params', [])
                                        },
                                        'required': atomic.get('input_params', [])
                                    }
                                }
                            }
                        },
                        'responses': {
                            '200': {
                                'description': 'Success',
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                k: {'type': 'string'} for k in atomic.get('output_params', [])
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        'tags': ['atomic']
                    }
                }
            }
        }

    return JsonResponse(schema)


def cpps_docs_page(request):
    services = list(cpps_collection.find())
    base_url = request.build_absolute_uri('/').rstrip('/')

    for s in services:
        s['schema_url'] = f"{base_url}/openapi_docs/schema/cpps/{s['group_id']}/"

    return render(request, 'openapi_docs/cpps_docs.html', {'services': services})



def cppn_docs_page(request):
    services = list(cppn_collection.find())
    base_url = request.build_absolute_uri('/').rstrip('/')

    for s in services:
        s['schema_url'] = f"{base_url}/openapi_docs/schema/cppn/{s['group_id']}/"

    return render(request, 'openapi_docs/cppn_docs.html', {'services': services})

class CPPSServiceSchemaView(APIView):
    """
    Dynamic OpenAPI 3.1 with drf, schema for CPPS services stored in MongoDB.
    """

    def get(self, request):
        paths = {}
        cpps_docs = list(cpps_collection.find())

        for doc in cpps_docs:
            for ep in doc.get("endpoints", []):
                path = ep.get("url")
                method = ep.get("method", "POST").lower()

                paths.setdefault(path, {})[method] = {
                    "operationId": doc.get("name", "unnamed-cpps"),
                    "tags": doc.get("group_type"),
                    "responses": {
                        "200": {
                            "description": doc.get('description', '')
                        }
                    },
                    "x-owner": doc.get("actor"),
                    "x-members": doc.get("members", []),
                    "x-workflow": doc.get("workflow_type", "sequence")
                }

        openapi = {
            "openapi": "3.1.0",
            "info": {
                "title": "CPPS Services API",
                "version": "1.0.0",
                "description": doc.get('description', '')
            },
            "paths": paths
        }

        return Response(openapi)



@api_view(['GET'])
def cpps_service_schema(request, group_id):
    doc = cpps_collection.find_one({'group_id': group_id})
    if not doc:
        return JsonResponse({'error': 'CPPS not found'}, status=404)

    atomic_services = doc.get("atomic_services", [])
    nested_cpps = doc.get("nested_cpps")
    atomic_names = []
    nested_cpps_names = []

    atomic_map = {
        a["task_id"]: a.get("name", a["task_id"])
        for a in atomic_services_collection.find({"task_id": {"$in": atomic_services}})
    }

    cpps_map = {
        c["group_id"]: c.get("name", c["group_id"])
        for c in cpps_collection.find({"group_id": {"$in": nested_cpps}})
    }

    for aid in atomic_services:
        if aid in atomic_map:
            atomic_names.append(atomic_map[aid])
    
    for aid in nested_cpps:
        if aid in cpps_map:
            nested_cpps_names.append(cpps_map[aid])

    # costruzione paths
    paths = {}
    for idx, ep in enumerate(doc.get("endpoints", [])):
        path = ep.get("url")
        method = ep.get("method", "POST").lower()

        paths.setdefault(path, {})[method] = {
            #"operationId": f"{doc.get('name', 'cpps')}_{idx}",
            "summary": doc.get("description", "CPPS composite service"),
            "responses": {
                "200": {
                    "description": doc.get('description', "Execution successful")
                }
            },
        }

    schema = {
        "openapi": "3.1.0",
        "info": {
            "title": f"CPPS Service: {doc.get('name', group_id)}",
            "version": "1.0.0",
            "description": doc.get('description'),
            "x-owner": doc.get("actor"),
            "x-cpps-name" : doc.get("name"),
            #"x-services": members,
            "x-atomicservices": atomic_names,
            "x-nestedcpps" : nested_cpps_names,
            #"x-servicetypes": servicetypes,
            #"x-workflow": doc.get("workflow_type", "sequence")
        },
        "paths": paths,
        "tags": [doc.get("group_type", "CPPS")]
    }

    return JsonResponse(schema)

class CPPNServiceSchemaView(APIView):
    """
    Dynamic OpenAPI 3.1 schema for CPPN services stored in MongoDB.
    """

    def get(self, request):
        cppn_docs = list(cppn_collection.find())

        # Non hanno endpoint diretti, ma includono metadata per estensioni x-
        components = []
        for doc in cppn_docs:
            components.append({
                "name": doc.get("name", "unnamed-cppn"),
                "description": doc.get("description", ""),
                "x-actors": doc.get("actors", []),
                "x-gdpr-map": doc.get("gdpr_map", {}),
                "x-members": doc.get("atomic_services", []),
                "x-workflow": doc.get("workflow_type", "sequence")
            })

        openapi = {
            "openapi": "3.1.0",
            "info": {
                "title": "CPPN Services API",
                "version": "1.0.0"
            },
            #"paths": {},  # Nessun path diretto
            "x-cppn-services": components
        }

        return Response(openapi)

@api_view(['GET'])
def cppn_service_schema(request, group_id):
    doc = cppn_collection.find_one({'group_id': group_id})
    if not doc:
        return JsonResponse({'error': 'CPPN not found'}, status=404)

    atomic_ids = doc.get("atomic_services", [])  # meglio usare "services", non "x-services"
    cppn_ids = doc.get("nested_cpps", [])

    atomic_names = []
    cppn_names = []

    for aid in atomic_ids:
        atomic = atomic_services_collection.find_one({'task_id': aid})
        if atomic:
            atomic_names.append(atomic.get("name", aid))
            continue  # trovato, vado avanti
    
    for cppnid in cppn_ids:
        cpps = cpps_collection.find_one({'group_id': cppnid})
        if cpps:
            cppn_names.append(cpps.get("name", cppnid))

    # schema finale
    schema = {
        "openapi": "3.1.0",
        "info": {
            "title": f"CPPN Service: {doc.get('name', group_id)}",
            "version": "1.0.0",
            "description": doc.get("description", ""),
            "x-actors": doc.get("actors", []),
            "x-cppn-name": doc.get("name"),
            "x-atomicservices": atomic_names,
            "x-nestedcpps": cppn_names,                
            "x-gdpr-map": doc.get("gdpr_map", {}),
            "x-workflow": doc.get("workflow_type", "sequence")
        },
        "tags": doc.get("group_type", "CPPN")
    }

    return JsonResponse(schema)