from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
import uuid
from utilities.mongodb_handler import bpmn_collection
from django.shortcuts import render

def importer_home(request):
    return render(request, 'importer/home.html')


@api_view(['POST'])
def upload_imported_diagram(request):
    name = request.data.get('name')
    xml = request.data.get('xml_content')

    if not name or not xml:
        return Response({'error': 'Missing data'}, status=400)

    result = bpmn_collection.insert_one({
        'name': name,
        'xml_content': xml
    })

    return Response({'id': str(result.inserted_id)})

