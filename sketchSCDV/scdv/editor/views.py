from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from utilities.mongodb_handler import atomic_services_collection, cpps_collection, cppn_collection, bpmn_collection, MongoDBHandler
from utilities.openapi_generator import OpenAPIGenerator
from django.utils.timezone import now
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from bson import ObjectId, json_util
from bson.errors import InvalidId

def data_view_editor(request):
    return render(request, 'editor/view.html')

def check_diagram_name(request):
    name = request.GET.get('name')
    if not name:
        return JsonResponse({'error': 'Missing name'}, status=400)

    # Confronto case-insensitive
    exists = bpmn_collection.find_one({ 'name': { '$regex': f'^{name}$', '$options': 'i' } }) is not None
    return JsonResponse({'exists': exists})

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

        update_fields = {
            "xml_content": data['xml_content'],
            "updated_at": now()
        }

        if 'name' in data:
            update_fields['name'] = data['name']

        result = bpmn_collection.update_one(
            {"_id": ObjectId(diagram_id)},
            {"$set": update_fields}
        )

        if result.matched_count == 0:
            return Response({'error': 'Diagram not found'}, status=404)

        return Response({'id': diagram_id, 'status': 'updated'})



def parse_param_list(param_list):
    parsed = []
    for item in param_list:
        item = item.strip()
        if item == "":
            continue
        if item.isdigit():
            type_ = 'Int'
        else:
            try:
                float(item)
                type_ = 'Float'
            except ValueError:
                type_ = 'String'
        parsed.append({'name': item, 'type': type_})
    return parsed

from utilities.helpers import detect_type
@api_view(['POST'])
def save_atomic_service(request):
    data = request.data
    print("===Atomic Payload received:", data)

    # Genera input/output tipizzati
    input_dict = {
        str(v): detect_type(v)
        for v in data.get('input_params', [])
    }
    output_dict = {
        str(v): detect_type(v)
        for v in data.get('output_params', [])
    }

    # Aggiorna il payload con input/output già pronti
    data['input'] = input_dict
    data['output'] = output_dict

    result, status_code = MongoDBHandler.save_atomic(data)

    if status_code in [200, 201]:
        openapi_doc = OpenAPIGenerator.generate_atomic_openapi(data)
        doc_result, doc_status = MongoDBHandler.save_openapi_documentation(openapi_doc)
        print("===OpenAPI doc saved:", doc_result)
    else:
        doc_result, doc_status = {"message": "Atomic service not saved, skipping OpenAPI"}, 400

    return Response({
        "atomic_service": result,
        "openapi_documentation": doc_result
    }, status=status_code)
    
@api_view(['POST'])
def save_cppn_service(request):
     data = request.data
     print("===CPPN Payload received:", data)
     result, status_code = MongoDBHandler.save_cppn(data)
     return Response(result, status=status_code)

@api_view(['POST'])
def save_cpps_service(request):
    data = request.data
    print("===CPPS Payload received:", data)
    result, status_code = MongoDBHandler.save_cpps(data)

    return Response(result, status=status_code)

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

    return JsonResponse(service, safe=False, json_dumps_params={'default': json_util.default})


@api_view(['GET'])
def get_atomic_service(request, task_id):
    service = atomic_services_collection.find_one({'task_id': task_id})
    if not service:
        return JsonResponse({'error': 'Atomic service not found'}, status=404)
    return JsonResponse(service, safe=False, json_dumps_params={'default': json_util.default})


@api_view(['GET'])
def get_all_services(request):
    atomic = list(atomic_services_collection.find({}, {'_id': 0, 'name': 1}))
    cpps = list(cpps_collection.find({}, {'_id': 0, 'name': 1}))
    cppn = list(cppn_collection.find({}, {'_id': 0, 'name': 1}))

    return Response({
        'atomic': atomic,
        'cpps': cpps,
        'cppn': cppn
    })


@api_view(['DELETE'])
def delete_group(request, group_id):
    deleted = False

    # Prova a cancellare dalla collezione CPPS
    if cpps_collection.find_one({'group_id': group_id}):
        cpps_collection.find_one_and_delete({'group_id': group_id})
        deleted = True

    # Prova a cancellare dalla collezione CPPN
    elif cppn_collection.find_one({'group_id': group_id}):
        cppn_collection.find_one_and_delete({'group_id': group_id})
        deleted = True

    # Rimuove il group_id da nested_cpps in altri CPPS
    removed_from_cpps = cpps_collection.update_many(
        { 'nested_cpps': group_id },
        { '$pull': { 'nested_cpps': group_id } }
    )

    # Rimuove il group_id da nested_cpps in CPPN
    removed_from_cppn = cppn_collection.update_many(
        { 'nested_cpps': group_id },
        { '$pull': { 'nested_cpps': group_id } }
    )

    if deleted:
        return Response({
            'message': f'Gruppo {group_id} delted!',
            'removed_from_nested_cpps': removed_from_cpps.modified_count,
            'removed_from_nested_cppn': removed_from_cppn.modified_count
        }, status=status.HTTP_200_OK)

    return Response({
        'error': f'Gruppo {group_id} not found',
        'removed_from_nested_cpps': removed_from_cpps.modified_count,
        'removed_from_nested_cppn': removed_from_cppn.modified_count
    }, status=status.HTTP_404_NOT_FOUND)



@api_view(['POST'])
def add_nested_cpps(request, group_id):
    nested_id = request.data.get('nested_id')
    if not nested_id:
        return Response({'error': 'Missing nested_id'}, status=400)

    result = cpps_collection.update_one(
        {'group_id': group_id},
        {'$addToSet': {'nested_cpps': nested_id}}
    )

    if result.matched_count == 0:
        return Response({'error': 'Parent CPPS not found'}, status=404)

    return Response({'status': 'nested_cpps updated'})


@api_view(['DELETE'])
def delete_atomic(request, atomic_id):
    try:

        # Elimino atomic
        deleted = atomic_services_collection.find_one_and_delete({'task_id': atomic_id})
        if not deleted:
            return Response({'error': 'Atomic service not found'}, status=404)

        # Rimuovo atomic dai CPPS
        cpps_result = cpps_collection.update_many(
            {'atomic_services': atomic_id},
            {'$pull': {'atomic_services': atomic_id}}
        )

        # Rimuovo atomic dai CPPN
        cppn_result = cppn_collection.update_many(
            {'atomic_services': atomic_id},
            {'$pull': {'atomic_services': atomic_id}}
        )

        return Response({
            'status': 'deleted',
            'removed_from_cpps': cpps_result.modified_count,
            'removed_from_cppn': cppn_result.modified_count
        }, status=200)

    except Exception as e:
        print(f"❌ Errore durante l'eliminazione dell'atomic: {e}")
        return Response({'error': str(e)}, status=500)