from django.shortcuts import render
from mongodb_handler import bpmn_collection
from rest_framework.decorators import api_view
from rest_framework.response import Response

def data_view_editor(request):
    return render(request, 'viewer/viewer.html')

@api_view(['GET'])
def list_diagrams(request):
    diagrams = bpmn_collection.find().sort("created_at", -1)
    result = []
    for d in diagrams:
        result.append({
            'id': str(d['_id']),
            'name': d.get('name', 'Untitled'),
            'created_at': d.get('created_at')
        })
    return Response(result)

@api_view(['GET'])
def get_diagram(request, diagram_id):
    from bson import ObjectId
    from bson.errors import InvalidId

    try:
        obj_id = ObjectId(diagram_id)
    except InvalidId:
        return Response({'error': 'Invalid ID'}, status=400)

    diagram = bpmn_collection.find_one({'_id': obj_id})
    if not diagram:
        return Response({'error': 'Not found'}, status=404)

    return Response({
        'id': str(diagram['_id']),
        'name': diagram.get('name', ''),
        'xml_content': diagram['xml_content']
    })



