from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import BPMNDiagram, AtomicService
from django.views.decorators.csrf import csrf_exempt
from mongodb_handler import atomic_services_collection, cpps_collection, cppn_collection, bpmn_collection
from django.utils.timezone import now


def data_view_editor(request):
    return render(request, 'editor/view.html')

@api_view(['POST'])
def save_diagram(request):
    data = request.data
    diagram = {
        "name": data['name'],
        "xml_content": data['xml_content'],
        "created_at": now()
    }
    result = bpmn_collection.insert_one(diagram)
    return Response({'id': str(result.inserted_id), 'status': 'saved'})



@api_view(['POST'])
def save_atomic_service(request):
    data = request.data
    print("=== Payload received:", data)

    required_fields = ['diagram_id', 'task_id', 'name', 'atomic_type', 'input_params', 'output_params', 'method', 'url']


    #TODO: c'è gia validazione in js lato client!! (NON SERVE)
    missing = [f for f in required_fields if f not in data]

    if missing:
        return Response({'error': f'Missing fields: {", ".join(missing)}'}, status=status.HTTP_400_BAD_REQUEST)    

    try:
        #verifico che diagramma esista
        diagram = BPMNDiagram.objects.get(id=data['diagram_id'])


        #salva o aggiorna l'atomic in mongo (activity_id univoco)
        result = atomic_services_collection.update_one(
             {'task_id': data['task_id']},
            {
                '$set': {
                    'name': data['name'],
                    'atomic_type': data['atomic_type'],
                    'input_params': data['input_params'],
                    'output_params': data['output_params'],
                    'method': data['method'],
                    'url': data['url']
                }
            },
            upsert=True #mix di update e insert
        )

        created = result.upserted_id is not None
        print("=== Atomic saved in Mongo. created:", created)

        return Response({'status': 'ok', 'created': created})
        
    except BPMNDiagram.DoesNotExist:
            return Response({'error': 'Diagram not found'}, status=status.HTTP_404_NOT_FOUND)
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
        BPMNDiagram.objects.get(id=data['diagram_id'])

        doc = {
            'diagram_id': data['diagram_id'],
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

    except BPMNDiagram.DoesNotExist:
        return Response({'error': 'Diagram not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
def save_cpps_service(request):
    data = request.data
    required_fields = ['diagram_id', 'group_id', 'name', 'description', 'workflow_type', 'members', 'actor', 'endpoints']

    missing = [f for f in required_fields if f not in data]
    if missing:
        return Response({'error': f'Missing fields: {", ".join(missing)}'}, status=400)

    try:
        diagram = BPMNDiagram.objects.get(id=data['diagram_id'])

        doc = {
            'diagram_id': data['diagram_id'],
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
    except BPMNDiagram.DoesNotExist:
        return Response({'error': 'Diagram not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
