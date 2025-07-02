from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
import uuid
from mongodb_handler import bpmn_collection
from django.shortcuts import render

def importer_home(request):
    return render(request, 'importer/home.html')


@api_view(['POST'])
def import_diagram(request):
    file = request.FILES.get('bpmn_file')
    if not file:
        return Response({'error': 'No file provided'}, status=400)

    content = file.read().decode('utf-8')
    name = f"Imported_{uuid.uuid4().hex[:6]}"

    result = bpmn_collection.insert_one({
        'name': name,
        'xml_content': content
    })

    return Response({'id': str(result.inserted_id)})
