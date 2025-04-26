from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import BPMNDiagram, AtomicService
from django.views.decorators.csrf import csrf_exempt


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

    print("=== Payload ricevuto:", data)
    try:
        diagram = BPMNDiagram.objects.get(id=data['diagram_id'])
        service, created = AtomicService.objects.update_or_create(
            diagram=diagram,
            task_id=data['task_id'],
            defaults={
                'name': data['name'],
                'atomic_type': data['atomic_type'],
                'input_params': data['input_params'],
                'output_params': data['output_params'],
                'method': data['method'],       
                'url': data['url']              
            }
        )
        print("=== Salvato atomic:", service)
        return Response({'status': 'ok', 'created': created})
    except BPMNDiagram.DoesNotExist:
        return Response({'error': 'Diagram not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
