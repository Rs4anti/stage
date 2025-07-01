from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import BPMNDiagram, AtomicService
from django.views.decorators.csrf import csrf_exempt
from mongodb_handler import atomic_services_collection, cpps_collection, cppn_collection, bpmn_collection
from django.utils.timezone import now
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from bson import ObjectId


def data_view_editor(request):
    return render(request, 'editor/view.html')


def atomic_docs_page(request):
    services = list(atomic_services_collection.find())
    base_url = request.build_absolute_uri('/').rstrip('/')

    for s in services:
        s['schema_url'] = f"{base_url}/editor/schema/atomic/{s['task_id']}/"

    return render(request, 'editor/atomic_docs.html', {'services': services})

def swagger_viewer(request, task_id):
    base_url = request.build_absolute_uri('/').rstrip('/')
    schema_url = f"{base_url}/editor/schema/atomic/{task_id}/"
    return render(request, 'editor/swagger_viewer.html', {'schema_url': schema_url})

from bson.errors import InvalidId

@api_view(['POST', 'PUT', 'GET'])
def save_diagram(request, diagram_id=None):
    data = request.data

    if request.method == 'GET':
        try:
            object_id = ObjectId(diagram_id)
        except InvalidId:
            return Response({'error': 'Invalid ID'}, status=400)

        exists = bpmn_collection.find_one({'_id': object_id})
        if exists:
            return Response({'status': 'exists'})
        else:
            return Response({'error': 'Not found'}, status=404)

    if request.method == 'POST':
        diagram = {
            "name": data['name'],
            "xml_content": data['xml_content'],
            "created_at": now()
        }
        result = bpmn_collection.insert_one(diagram)
        return Response({'id': str(result.inserted_id), 'status': 'saved'})

    elif request.method == 'PUT':
        if not diagram_id:
            return Response({'error': 'Diagram ID is required'}, status=400)

        result = bpmn_collection.update_one(
            {"_id": ObjectId(diagram_id)},
            {"$set": {
                "xml_content": data['xml_content'],
                "updated_at": now()
            }}
        )

        if result.matched_count == 0:
            return Response({'error': 'Diagram not found'}, status=404)

        return Response({'id': diagram_id, 'status': 'updated'})



@api_view(['POST'])
def save_atomic_service(request):
    from bson import ObjectId

    data = request.data
    print("=== Payload received:", data)

    required_fields = ['diagram_id', 'task_id', 'name', 'atomic_type', 'input_params', 'output_params', 'method', 'url']
    missing = [f for f in required_fields if f not in data]
    if missing:
        return Response({'error': f'Missing fields: {", ".join(missing)}'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        diagram_id = ObjectId(data['diagram_id'])
    except Exception:
        return Response({'error': 'Invalid diagram ID'}, status=status.HTTP_400_BAD_REQUEST)

    diagram = bpmn_collection.find_one({'_id': diagram_id})
    if not diagram:
        return Response({'error': 'Diagram not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        result = atomic_services_collection.update_one(
            {'task_id': data['task_id']},
            {
                '$set': {
                    'diagram_id': str(diagram_id),
                    'name': data['name'],
                    'atomic_type': data['atomic_type'],
                    'input_params': data['input_params'],
                    'output_params': data['output_params'],
                    'method': data['method'],
                    'url': data['url']
                }
            },
            upsert=True
        )

        created = result.upserted_id is not None
        print("=== Atomic saved in Mongo. created:", created)

        return Response({'status': 'ok', 'created': created})

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def save_cppn_service(request):
    data = request.data
    required_fields = ['diagram_id', 'group_id', 'name', 'description', 'workflow_type', 'members', 'actors', 'gdpr_map']

    missing = [f for f in required_fields if f not in data]
    if missing:
        return Response({'error': f'Missing fields: {", ".join(missing)}'}, status=400)

    if not isinstance(data['actors'], list):
        return Response({'error': 'Field "actors" must be a list'}, status=400)

    if not isinstance(data['gdpr_map'], dict):
        return Response({'error': 'Field "gdpr_map" must be a JSON object'}, status=400)

    try:
        diagram_id = ObjectId(data['diagram_id'])
    except Exception:
        return Response({'error': 'Invalid diagram ID'}, status=400)

    diagram = bpmn_collection.find_one({'_id': diagram_id})
    if not diagram:
        return Response({'error': 'Diagram not found'}, status=404)

    try:
        doc = {
            "group_type" : "CPPN",
            'diagram_id': str(diagram_id),
            'group_id': data['group_id'],
            'name': data['name'],
            'description': data['description'],
            'workflow_type': data['workflow_type'],
            'members': data['members'],
            'actors': data['actors'],
            'gdpr_map': data['gdpr_map']
        }

        result = cppn_collection.update_one(
            {'group_id': data['group_id']},
            {'$set': doc},
            upsert=True
        )

        return Response({'status': 'ok', 'created': result.upserted_id is not None})

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
def save_cpps_service(request):
    data = request.data
    required_fields = ['diagram_id', 'group_id', 'name', 'description', 'workflow_type', 'members', 'actor', 'endpoints']

    missing = [f for f in required_fields if f not in data]
    if missing:
        return Response({'error': f'Missing fields: {", ".join(missing)}'}, status=400)

    from bson import ObjectId
    try:
        diagram_id = ObjectId(data['diagram_id'])
    except Exception:
        return Response({'error': 'Invalid diagram ID'}, status=400)

    diagram = bpmn_collection.find_one({'_id': diagram_id})
    if not diagram:
        return Response({'error': 'Diagram not found'}, status=404)

    try:
        doc = {
            "group_type" : "CPPS",
            'diagram_id': str(diagram_id),
            'group_id': data['group_id'],
            'name': data['name'],
            'description': data['description'],
            'workflow_type': data['workflow_type'],
            'members': data['members'],
            'actor': data['actor'],
            'endpoints': data['endpoints']
        }

        result = cpps_collection.update_one(
            {'group_id': data['group_id']},
            {'$set': doc},
            upsert=True
        )

        return Response({'status': 'ok', 'created': result.upserted_id is not None})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

    

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
                "operationId": doc.get("name", "unnamed-service"),
                "summary": f"{doc.get('atomic_type')} atomic service",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {p: {"type": "string"} for p in input_params},
                                "required": input_params
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
        },
        'paths': {
            atomic['url']: {
                atomic.get('method', 'POST').lower(): {
                'operationId': atomic.get('name', task_id),
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
                        'tags': ['atomic'],
                        'x-atomic-type': atomic.get('atomic_type', '')
                    }
                }
            }
        }

    return JsonResponse(schema)


@api_view(['GET'])
def get_cppn_service(request, group_id):
    service = cppn_collection.find_one({'group_id': group_id})
    if not service:
        return JsonResponse({'error': 'CPPN not found'}, status=404)

    return JsonResponse(service, safe=False, json_dumps_params={'default': json_util.default})

@api_view(['GET'])
def get_cpps_service(request, group_id):
    service = cpps_collection.find_one({'group_id': group_id})
    if not service:
        return Response({'error': 'CPPS not found'}, status=404)

    from bson import json_util
    from django.http import JsonResponse

    return JsonResponse(service, safe=False, json_dumps_params={'default': json_util.default})


from bson import json_util

@api_view(['GET'])
def get_atomic_service(request, task_id):
    service = atomic_services_collection.find_one({'task_id': task_id})
    if not service:
        return JsonResponse({'error': 'Atomic service not found'}, status=404)
    return JsonResponse(service, safe=False, json_dumps_params={'default': json_util.default})
