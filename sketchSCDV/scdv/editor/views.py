from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import BPMNDiagram, AtomicService
from django.views.decorators.csrf import csrf_exempt
from mongodb_handler import atomic_services_collection


def data_view_editor(request):
    return render(request, 'editor/view.html')

@api_view(['POST'])
def save_diagram(request):
    data = request.data
    diagram = BPMNDiagram.objects.create(
        name=data['name'],
        xml_content=data['xml_content']
    )
    return Response({'id': diagram.id, 'status': 'saved'})


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
