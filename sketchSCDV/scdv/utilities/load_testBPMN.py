from .bpmn_importer import BPMNImporterXmlBased
from .mongodb_handler import db, client

#svuoto il db
client.drop_database(db)
print(f"⚠️ DB '{db.name}' droppato.")

#carico servizi da file
bpmn_path = r"C:\Users\santi\Downloads\paper_diagram.bpmn"
importer = BPMNImporterXmlBased(bpmn_path)
importer.import_all()
