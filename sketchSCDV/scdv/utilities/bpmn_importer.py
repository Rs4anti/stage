import os
import xml.etree.ElementTree as ET
from datetime import datetime

from .mongodb_handler import (
    MongoDBHandler,
    atomic_services_collection,
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
        cppn_count = 0
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

        group_to_elements = self._extract_group_members()
        actor_map = self._map_task_to_actor()

        for group_id, members in group_to_elements.items():
            involved_actors = set(actor_map.get(mid) for mid in members if mid in actor_map)

            valid_tasks = [
                {"id": mid, "type": "Atomic"}
                for mid in members
                if atomic_services_collection.find_one({"task_id": mid})
            ]

            if not valid_tasks:
                continue

            if len(involved_actors) == 1:
                actor = list(involved_actors)[0]
                cpps_doc = {
                    "diagram_id": str(self.diagram_id),
                    "group_id": group_id,
                    "name": f"CPPS {group_id}",
                    "description": f"CPPS for actor {actor}",
                    "workflow_type": "sequence",
                    "actor": actor,
                    "components": valid_tasks,
                    "endpoints": [],
                    "group_type": "CPPS"
                }
                MongoDBHandler.save_cpps(cpps_doc)

                atomic_map = {
                    a["task_id"]: a for a in atomic_services_collection.find({
                        "task_id": {"$in": [c["id"] for c in valid_tasks]}
                    })
                }

                openapi_doc = OpenAPIGenerator.generate_cpps_openapi(cpps_doc, atomic_map, {})
                MongoDBHandler.save_openapi_documentation(openapi_doc)
                cpps_count += 1
                print(f"🧩 CPPS salvato: {group_id}")

            else:
                cppn_doc = {
                    "diagram_id": str(self.diagram_id),
                    "group_id": group_id,
                    "name": f"CPPN {group_id}",
                    "description": f"CPPN for actors: {', '.join(involved_actors)}",
                    "workflow_type": "sequence",
                    "actors": list(involved_actors),
                    "gdpr_map": {},
                    "components": [c["id"] for c in valid_tasks],
                    "group_type": "CPPN"
                }
                MongoDBHandler.save_cppn(cppn_doc)

                atomic_map = {
                    a["task_id"]: a for a in atomic_services_collection.find({
                        "task_id": {"$in": [c["id"] for c in valid_tasks]}
                    })
                }
                cpps_map = {}
                openapi_doc = OpenAPIGenerator.generate_cppn_openapi(cppn_doc, atomic_map, cpps_map)
                MongoDBHandler.save_openapi_documentation(openapi_doc)
                cppn_count += 1
                print(f"🧠 CPPN salvato: {group_id}")

        print(f"\n✅ Importazione completata: {atomic_count} atomic, {cpps_count} cpps, {cppn_count} cppn")

    def _extract_group_members(self):
        ns = self.namespaces
        group_members = {}

        for g in self.xml_root.findall(".//bpmndi:BPMNShape", ns):
            bpmn_element = g.attrib.get("bpmnElement", "")
            if not bpmn_element.startswith("Group_"):
                continue

            group_id = bpmn_element
            bounds = g.find("dc:Bounds", ns)
            if bounds is None:
                continue

            gx = float(bounds.attrib["x"])
            gy = float(bounds.attrib["y"])
            gw = float(bounds.attrib["width"])
            gh = float(bounds.attrib["height"])

            members = []
            for shape in self.xml_root.findall(".//bpmndi:BPMNShape", ns):
                target_elem = shape.attrib.get("bpmnElement", "")
                if target_elem.startswith("Group_"):
                    continue
                b = shape.find("dc:Bounds", ns)
                if b is None:
                    continue

                x = float(b.attrib["x"])
                y = float(b.attrib["y"])

                if gx <= x <= gx + gw and gy <= y <= gy + gh:
                    members.append(target_elem)

            group_members[group_id] = members

        return group_members

    def _map_task_to_actor(self):
        ns = self.namespaces
        task_to_actor = {}

        process_to_actor = {
            p.attrib.get("processRef"): p.attrib.get("name", p.attrib["id"])
            for p in self.xml_root.findall(".//bpmn:participant", ns)
            if p.attrib.get("processRef")
        }

        for proc in self.xml_root.findall(".//bpmn:process", ns):
            process_id = proc.attrib.get("id")
            actor = process_to_actor.get(process_id, "UnknownActor")

            for task in proc.findall(".//bpmn:task", ns):
                tid = task.attrib.get("id")
                if tid:
                    task_to_actor[tid] = actor

        return task_to_actor

    def _get_namespaces(self):
        events = ("start", "start-ns")
        ns = {}
        for event, elem in ET.iterparse(self.bpmn_path, events):
            if event == "start-ns":
                prefix, uri = elem
                ns[prefix] = uri
        return ns

    def _strip_ns(self, tag):
        return tag.split('}')[-1] if '}' in tag else tag
