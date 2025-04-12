from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import BPMNDiagram, AtomicService

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
    diagram = BPMNDiagram.objects.get(id=data['diagram_id'])
    service, created = AtomicService.objects.update_or_create(
        diagram=diagram,
        task_id=data['task_id'],
        defaults={
            'name': data['name'],
            'atomic_type': data['atomic_type'],
            'input_params': data['input_params'],
            'output_params': data['output_params']
        }
    )
    return Response({'status': 'ok', 'created': created})
