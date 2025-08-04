import os
import xml.etree.ElementTree as ET
from datetime import datetime

from .mongodb_handler import (
    MongoDBHandler,
    atomic_services_collection,
    cpps_collection,
    bpmn_collection
)
from .openapi_generator import OpenAPIGenerator
from .helpers import detect_type


class BPMNImporterXmlBased:

    def __init__(self, bpmn_path):
        self.bpmn_path = bpmn_path
        self.diagram_id = None
        self.xml_root = None
        self.namespaces = {}

    def parse_bpmn(self):
        tree = ET.parse(self.bpmn_path)
        self.xml_root = tree.getroot()
        self.namespaces = self._get_namespaces()

    def save_diagram(self):
        with open(self.bpmn_path, "r", encoding="utf-8") as f:
            xml_content = f.read()

        filename = os.path.basename(self.bpmn_path)
        name = os.path.splitext(filename)[0]

        doc = {
            "name": name,
            "filename": filename,
            "xml_content": xml_content,
            "created_at": datetime.utcnow()
        }

        result = bpmn_collection.insert_one(doc)
        self.diagram_id = result.inserted_id
        print(f"✅ Diagramma salvato con ID: {self.diagram_id}")

    def import_all(self):
        self.parse_bpmn()
        self.save_diagram()

        atomic_count = 0
        cpps_count = 0
        ns = self.namespaces

        for elem in self.xml_root.iter():
            tag = self._strip_ns(elem.tag)

            if tag == "task":
                task_id = elem.attrib["id"]
                task_name = elem.attrib.get("name", f"Task {task_id}")
                ext = elem.find(".//custom:atomicExtension", ns)

                if ext is not None:
                    atomic_type = ext.find("custom:atomicType", ns)
                    input_tag = ext.find("custom:inputParams", ns)
                    output_tag = ext.find("custom:outputParams", ns)
                    method_tag = ext.find("custom:method", ns)
                    url_tag = ext.find("custom:url", ns)
                    owner_tag = ext.find("custom:owner", ns)

                    input_params = input_tag.text.strip().split(",") if input_tag is not None else []
                    output_params = output_tag.text.strip().split(",") if output_tag is not None else []

                    input_dict = {p.strip(): detect_type(p.strip()) for p in input_params if p.strip()}
                    output_dict = {p.strip(): detect_type(p.strip()) for p in output_params if p.strip()}

                    atomic_doc = {
                        "diagram_id": str(self.diagram_id),
                        "task_id": task_id,
                        "name": task_name,
                        "atomic_type": atomic_type.text.strip() if atomic_type is not None else "unspecified",
                        "input_params": input_params,
                        "output_params": output_params,
                        "method": method_tag.text.strip() if method_tag is not None else "POST",
                        "url": url_tag.text.strip() if url_tag is not None else f"/{task_id.lower()}",
                        "owner": owner_tag.text.strip() if owner_tag is not None else "AutoImport",
                        "input": input_dict,
                        "output": output_dict
                    }

                    MongoDBHandler.save_atomic(atomic_doc)
                    openapi_doc = OpenAPIGenerator.generate_atomic_openapi(atomic_doc)
                    MongoDBHandler.save_openapi_documentation(openapi_doc)
                    atomic_count += 1
                    print(f"🔹 Atomic salvato: {task_name}")
                else:
                    print(f"⚠️ Nessuna <atomicExtension> per il task: {task_name}")

            elif tag == "subProcess":
                group_id = elem.attrib["id"]
                name = elem.attrib.get("name", f"CPPS {group_id}")

                component_ids = [
                    {"id": child.attrib["id"], "type": "Atomic"}
                    for child in elem
                    if self._strip_ns(child.tag) == "task"
                ]

                cpps_doc = {
                    "diagram_id": str(self.diagram_id),
                    "group_id": group_id,
                    "name": name,
                    "description": f"Imported from BPMN {name}",
                    "workflow_type": "sequence",
                    "actor": "AutoImport",
                    "components": component_ids,
                    "endpoints": [],
                    "group_type": "CPPS"
                }

                MongoDBHandler.save_cpps(cpps_doc)

                atomic_map = {
                    a["task_id"]: a
                    for a in atomic_services_collection.find({
                        "task_id": {"$in": [c["id"] for c in component_ids]}
                    })
                }

                openapi_doc = OpenAPIGenerator.generate_cpps_openapi(cpps_doc, atomic_map, {})
                MongoDBHandler.save_openapi_documentation(openapi_doc)
                cpps_count += 1
                print(f"🧩 CPPS salvato: {name}")

        print(f"\n✅ Importazione completata: {atomic_count} atomic, {cpps_count} cpps")

    def _get_namespaces(self):
        # Estrae i namespace come dict es: {"bpmn": "...", "custom": "..."}
        events = ("start", "start-ns")
        ns = {}
        for event, elem in ET.iterparse(self.bpmn_path, events):
            if event == "start-ns":
                prefix, uri = elem
                ns[prefix] = uri
        return ns

    def _strip_ns(self, tag):
        return tag.split('}')[-1] if '}' in tag else tag