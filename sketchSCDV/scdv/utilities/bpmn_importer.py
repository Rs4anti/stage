import os
import xml.etree.ElementTree as ET
from datetime import datetime
import json

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

    def _extract_workflow(self, group_id, members):
        ns = self.namespaces
        workflow = {}

        for seq in self.xml_root.findall(".//bpmn:sequenceFlow", ns):
            source_ref = seq.attrib.get("sourceRef")
            target_ref = seq.attrib.get("targetRef")

            if source_ref in members and target_ref in members:
                if source_ref not in workflow:
                    workflow[source_ref] = []
                workflow[source_ref].append(target_ref)

        return workflow

    def _extract_gateways(self, members):
        ns = self.namespaces
        gateway_tags = {
            "bpmn:parallelGateway": "ParallelGateway",
            "bpmn:exclusiveGateway": "ExclusiveGateway",
            "bpmn:inclusiveGateway": "InclusiveGateway"
        }

        gateway_components = []

        for gw_tag, gw_type in gateway_tags.items():
            for gw in self.xml_root.findall(f".//{gw_tag}", ns):
                gw_id = gw.attrib.get("id")
                if not gw_id or gw_id not in members:
                    continue

                targets = []
                for seq in self.xml_root.findall(".//bpmn:sequenceFlow", ns):
                    if seq.attrib.get("sourceRef") == gw_id and seq.attrib.get("targetRef") in members:
                        targets.append(seq.attrib["targetRef"])

                gateway_components.append({
                    "id": gw_id,
                    "type": gw_type,
                    "targets": targets
                })

        return gateway_components

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

            group_ext = self.xml_root.find(f".//bpmn:group[@id='{group_id}']/bpmn:extensionElements/custom:groupExtension", ns)
            group_name = group_ext.find("custom:name", ns).text.strip() if group_ext is not None and group_ext.find("custom:name", ns) is not None else f"Composite {group_id}"
            group_description = group_ext.find("custom:description", ns).text.strip() if group_ext is not None and group_ext.find("custom:description", ns) is not None else "Imported composite service"
            workflow_type = group_ext.find("custom:workflowType", ns).text.strip() if group_ext is not None and group_ext.find("custom:workflowType", ns) is not None else "sequence"
            gdpr_tag = group_ext.find("custom:gdprMap", ns)
            try:
                gdpr_map = json.loads(gdpr_tag.text.strip()) if gdpr_tag is not None else {}
            except json.JSONDecodeError:
                print(f"⚠️ JSON invalido per gdprMap nel gruppo {group_id}")
                gdpr_map = {}

            if len(involved_actors) == 1:
                actor = list(involved_actors)[0]
                workflow = self._extract_workflow(group_id, members)
                gateway_components = self._extract_gateways(members)
                valid_task_ids = [c['id'] for c in valid_tasks]
                components = valid_tasks + gateway_components

                cpps_doc = {
                    "diagram_id": str(self.diagram_id),
                    "group_id": group_id,
                    "name": group_name,
                    "description": group_description,
                    "workflow_type": workflow_type,
                    "owner": actor,
                    "components": components,
                    "endpoints": [],
                    "group_type": "CPPS",
                    "workflow": workflow
                }

                MongoDBHandler.save_cpps(cpps_doc)

                atomic_map = {
                    a["task_id"]: a for a in atomic_services_collection.find({
                        "task_id": {"$in": valid_task_ids}
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
                    "name": group_name,
                    "description": group_description,
                    "workflow_type": workflow_type,
                    "actors": list(involved_actors),
                    "gdpr_map": gdpr_map,
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
        
        return {
            "diagram_id": str(self.diagram_id),
            "atomic": atomic_count,
            "cpps": cpps_count,
            "cppn": cppn_count
        }

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