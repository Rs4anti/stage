import os
import uuid
from tempfile import NamedTemporaryFile
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render

from utilities.bpmn_importer import BPMNImporterXmlBased  # Assicurati sia correttamente importata

def importer_home(request):
    return render(request, 'importer/home.html')


@api_view(['POST'])
def upload_imported_diagram(request):
    name = request.data.get('name')
    xml = request.data.get('xml_content')

    if not name or not xml:
        return Response({'error': 'Missing data'}, status=400)

    try:
        with NamedTemporaryFile(mode='w+', suffix=".bpmn", delete=False) as tmp:
            tmp.write(xml)
            tmp.flush()
            tmp_path = tmp.name

        importer = BPMNImporterXmlBased(bpmn_path=tmp_path, name=name)
        result = importer.import_all()

        os.remove(tmp_path)

        return Response(result)

    except Exception as e:
        return Response({'error': f'Import failed: {str(e)}'}, status=500)


from django.shortcuts import render

def import_summary(request):
    return render(request, 'importer/summary.html', {
        'diagram_id': request.GET.get('diagram_id'),
        'atomic': request.GET.get('atomic', 0),
        'cpps': request.GET.get('cpps', 0),
        'cppn': request.GET.get('cppn', 0)
    })

