from django.shortcuts import render
from utilities.mongodb_handler import atomic_services_collection, cpps_collection, cppn_collection, openapi_collection
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.decorators import api_view
from bson import ObjectId

def openapi_docs_page(request):
    return render(request, 'openapi_docs/openapi_docs.html')

def atomic_docs_page(request):
    services = list(openapi_collection.find({"info.x-service-type": "atomic"}))
    base_url = request.build_absolute_uri('/').rstrip('/')
    filtered_services = []

    for s in services:
        # Prendi _id come stringa
        mongo_id = str(s.get('_id'))
        
        # Prendi primo path e metodo
        paths = s.get('paths', {})
        if not paths:
            continue  # Skippa se mancano

        path, methods = next(iter(paths.items()))
        method = next(iter(methods.keys())).upper()  # es. DELETE

        # Popola campi per il template
        s['task_id'] = mongo_id  # ATTENZIONE: ora è l'ObjectId, non più info.title
        s['name'] = s.get('info', {}).get('title', 'unnamed')
        s['url'] = path
        s['method'] = method
        s['schema_url'] = f"{base_url}/openapi_docs/schema/atomic/{mongo_id}/"

        filtered_services.append(s)

    return render(request, 'openapi_docs/atomic_docs.html', {'services': filtered_services})


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
    try:
        object_id = ObjectId(task_id)
    except Exception:
        return JsonResponse({'error': 'Invalid ID'}, status=400)

    atomic_doc = openapi_collection.find_one({'_id': object_id})
    if not atomic_doc:
        return JsonResponse({'error': 'Atomic service not found'}, status=404)

    atomic_doc.pop('_id', None)
    return JsonResponse(atomic_doc)



def cpps_docs_page(request):
    services = list(openapi_collection.find({"info.x-service-type": "cpps"}))
    base_url = request.build_absolute_uri('/').rstrip('/')

    for s in services:
        s['group_id'] = s.get('info', {}).get('x-cpps-name', 'unknown')
        s['name'] = s.get('info', {}).get('title', 'unknown')
        s['actor'] = s.get('info', {}).get('x-owner', 'unknown')
        s['schema_url'] = f"{base_url}/openapi_docs/schema/cpps/{s['group_id']}/"

    return render(request, 'openapi_docs/cpps_docs.html', {'services': services})



def cppn_docs_page(request):
    services = list(openapi_collection.find({"info.x-service-type": "cppn"}))
    base_url = request.build_absolute_uri('/').rstrip('/')

    for s in services:
        s['group_id'] = s.get('info', {}).get('x-cppn-name', 'unknown')
        s['name'] = s.get('info', {}).get('title', 'unknown')
        s['actor'] = ", ".join(s.get('info', {}).get('x-actors', []))  # lista attori joinata
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
    doc = openapi_collection.find_one({"info.x-cpps-name": group_id})
    if not doc:
        return JsonResponse({'error': 'CPPS doc not found'}, status=404)
    doc.pop('_id', None)
    return JsonResponse(doc)

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
    doc = openapi_collection.find_one({'info.x-cppn-name': group_id})
    if not doc:
        return JsonResponse({'error': 'CPPN not found'}, status=404)
    doc.pop('_id', None)
    return JsonResponse(doc)

from django.urls import reverse
def swagger_viewer_cpps(request, group_id):
    schema_url = reverse('cpps-schema-by-id', args=[group_id])
    return render(request, 'openapi_docs/swagger_viewer.html', {
        'schema_url': schema_url
    })

def swagger_viewer_cppn(request, group_id):
    schema_url = reverse('cppn-schema-by-id', args=[group_id])
    return render(request, 'openapi_docs/swagger_viewer.html', {
        'schema_url': schema_url
    })

