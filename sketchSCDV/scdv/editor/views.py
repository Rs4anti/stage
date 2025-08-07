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
from utilities.helpers import detect_type

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
def save_cpps_service(request):
    data = request.data
    print("===CPPS Payload received:", data)

    # Estrai componenti
    components = data.get('components', [])
    component_ids = [c['id'] for c in components if c['type'] == 'Atomic']
    cpps_ids = [c['id'] for c in components if c['type'] == 'CPPS']

    # Recupera documenti atomic e cpps annidati
    atomic_map = {
        a["task_id"]: a
        for a in atomic_services_collection.find({"task_id": {"$in": component_ids}})
    }

    cpps_map = {
        c["group_id"]: c
        for c in cpps_collection.find({"group_id": {"$in": cpps_ids}})
    }

    # ✅ Normalizza components e workflow
    data["components"], data["workflow"] = normalize_components_and_workflow(data, cpps_map)

    # ✅ Salva nel DB
    result, status_code = MongoDBHandler.save_cpps(data)

    if status_code in [200, 201]:
        # Genera OpenAPI
        openapi_doc = OpenAPIGenerator.generate_cpps_openapi(data, atomic_map, cpps_map)
        doc_result, doc_status = MongoDBHandler.save_openapi_documentation(openapi_doc)
        print("===OpenAPI doc saved:", doc_result)
    else:
        doc_result, doc_status = {"message": "CPPS not saved, skipping OpenAPI"}, 400

    return Response({
        "cpps_service": result,
        "openapi_documentation": doc_result
    }, status=status_code)

from collections import OrderedDict

def normalize_components_and_workflow(data, cpps_map):
    components = data.get('components', [])
    workflow = data.get('workflow', {})

    nested_atomic_ids = {
        comp["id"]
        for c in components if c["type"] == "CPPS"
        for comp in cpps_map.get(c["id"], {}).get("components", [])
        if comp["type"] == "Atomic"
    }

    filtered_components = [
        c for c in components
        if c["type"] != "Atomic" or c["id"] not in nested_atomic_ids
    ]

    new_workflow = OrderedDict()

    # 🔧 PRIMA: inserisci Group → Primo Nodo Esterno
    for group_id, group_doc in cpps_map.items():
        last_atomic_ids = [
            atomic["id"] for atomic in group_doc.get("components", [])
            if atomic["type"] == "Atomic"
        ]

        outgoing = set()
        for atomic_id in last_atomic_ids:
            targets = workflow.get(atomic_id, [])
            for t in targets:
                if t not in nested_atomic_ids:
                    outgoing.add(t)

        if outgoing:
            new_workflow[group_id] = list(outgoing)

    # DOPO: il resto del workflow
    for source, targets in workflow.items():
        if source in nested_atomic_ids:
            continue

        new_targets = []
        for target in targets:
            if target in nested_atomic_ids:
                for group_id, group_doc in cpps_map.items():
                    group_atomic_ids = [c["id"] for c in group_doc.get("components", []) if c["type"] == "Atomic"]
                    if target in group_atomic_ids:
                        target = group_id
                        break
            new_targets.append(target)

        if new_targets:
            new_workflow[source] = new_targets

    return filtered_components, new_workflow


@api_view(['POST'])
def save_cppn_service(request):
    data = request.data
    print("===CPPN Payload received:", data)

    # Salva CPPN nel database
    result, status_code = MongoDBHandler.save_cppn(data)

    if status_code in [200, 201]:
        # Recupera documento appena salvato
        saved_doc = cppn_collection.find_one({'group_id': data['group_id']})

        if not saved_doc:
            print("❌ CPPN not found after save")
            return Response({"error": "CPPN saved but not found for OpenAPI generation"}, status=500)

        # Recupera i componenti (atomic e cpps)
        components = saved_doc.get('components', [])

        atomic_map = {
            a["task_id"]: a
            for a in atomic_services_collection.find({"task_id": {"$in": components}})
        }

        cpps_map = {
            c["group_id"]: c
            for c in cpps_collection.find({"group_id": {"$in": components}})
        }

        # Genera documentazione OpenAPI per il CPPN
        openapi_doc = OpenAPIGenerator.generate_cppn_openapi(saved_doc, atomic_map, cpps_map)

        # Salva documentazione OpenAPI nella collection openapi
        doc_result, doc_status = MongoDBHandler.save_openapi_documentation(openapi_doc)
        print("===OpenAPI doc saved:", doc_result)
    else:
        doc_result, doc_status = {"message": "CPPN not saved, skipping OpenAPI"}, 400

    return Response({
        "cppn_service": result,
        "openapi_documentation": doc_result
    }, status=status_code)


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
    

@api_view(['DELETE'])
def delete_diagram_and_services(request, diagram_id):
    try:
        obj_id = ObjectId(diagram_id)

        # Elimina il diagramma
        result = bpmn_collection.delete_one({"_id": obj_id})
        if result.deleted_count == 0:
            return Response({"error": "Diagram not found"}, status=404)

        # Elimina atomic services collegati
        atomic_deleted = atomic_services_collection.delete_many({"diagram_id": diagram_id})

        # Elimina CPPS collegati
        cpps_deleted = cpps_collection.delete_many({"diagram_id": diagram_id})

        # Elimina CPPN collegati
        cppn_deleted = cppn_collection.delete_many({"diagram_id": diagram_id})

        # Elimina documentazione OpenAPI associata
        from utilities.mongodb_handler import openapi_collection
        openapi_deleted = openapi_collection.delete_many({"info.x-diagram_id": diagram_id})


        return Response({
            "status": "deleted",
            "diagram_id": diagram_id,
            "atomic_deleted": atomic_deleted.deleted_count,
            "cpps_deleted": cpps_deleted.deleted_count,
            "cppn_deleted": cppn_deleted.deleted_count,
            "openapi_deleted": openapi_deleted.deleted_count
        }, status=200)

    except InvalidId:
        return Response({"error": "Invalid diagram ID"}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
