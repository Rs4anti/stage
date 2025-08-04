from .bpmn_importer import BPMNImporterXmlBased

bpmn_path = r"C:\Users\santi\Downloads\prova_diagram_paper.bpmn"
importer = BPMNImporterXmlBased(bpmn_path)
importer.import_all()
