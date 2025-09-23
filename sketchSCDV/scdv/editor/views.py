from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from utilities.mongodb_handler import rbac_collection, atomic_services_collection, cpps_collection, cppn_collection, bpmn_collection, MongoDBHandler
from utilities.rbac import rbac
from django.utils.timezone import now
from rest_framework.response import Response
from django.http import JsonResponse
from bson import ObjectId, json_util
from bson.errors import InvalidId
from utilities.helpers import detect_type
from openapi_docs.services import publish_atomic_spec, publish_cpps_spec, publish_cppn_spec
from openapi_docs.serializers import AtomicUpsertSerializer
from django.urls import reverse
from collections import OrderedDict
from utilities.mongodb_handler import openapi_collection

def data_view_editor(request):
    return render(request, 'editor/view.html')

def rbac_policies_view(request):
    service_id = request.GET.get("id")
    # se serve, puoi filtrare subito
    # policies = mongo_collection.find({"atomic_id": service_id}) ...
    return render(request, "editor/rbac.html", {"service_id": service_id})


def check_diagram_name(request):
    name = request.GET.get('name')
    if not name:
        return JsonResponse({'error': 'Missing name'}, status=400)

    # Confronto case-insensitive
    exists = bpmn_collection.find_one({ 'name': { '$regex': f'^{name}$', '$options': 'i' } }) is not None
    return JsonResponse({'exists': exists})

@api_view(['POST', 'PUT', 'GET'])
def save_diagram(request, diagram_id=None):
    data = request.data

    if request.method == 'GET':
        try:
            object_id = ObjectId(diagram_id)
        except InvalidId:
            return Response({'error': 'Invalid ID'}, status=400)

        exists = bpmn_collection.find_one({'_id': object_id})
        if exists:
            return Response({'status': 'exists'})
        else:
            return Response({'error': 'Not found'}, status=404)

    if request.method == 'POST':
        diagram = {
            "name": data['name'],
            "xml_content": data['xml_content'],
            "created_at": now()
        }
        result = bpmn_collection.insert_one(diagram)
        return Response({'id': str(result.inserted_id), 'status': 'saved'})

    elif request.method == 'PUT':
        if not diagram_id:
            return Response({'error': 'Diagram ID is required'}, status=400)

        update_fields = {
            "xml_content": data['xml_content'],
            "updated_at": now()
        }

        if 'name' in data:
            update_fields['name'] = data['name']

        result = bpmn_collection.update_one(
            {"_id": ObjectId(diagram_id)},
            {"$set": update_fields}
        )

        if result.matched_count == 0:
            return Response({'error': 'Diagram not found'}, status=404)

        return Response({'id': diagram_id, 'status': 'updated'})

def parse_param_list(param_list):
    parsed = []
    for item in param_list:
        item = item.strip()
        if item == "":
            continue
        if item.isdigit():
            type_ = 'Int'
        else:
            try:
                float(item)
                type_ = 'Float'
            except ValueError:
                type_ = 'String'
        parsed.append({'name': item, 'type': type_})
    return parsed

@api_view(['POST'])
def save_atomic_service(request):
    data = request.data

    # Genera input/output tipizzati a partire da input_params/output_params
    data = dict(data)  # copiamo per sicurezza
    data['input'] = { str(v): detect_type(v) for v in data.get('input_params', []) }
    data['output'] = { str(v): detect_type(v) for v in data.get('output_params', []) }

    # Validazione schema (DRF) per evitare payload incompleti
    ser = AtomicUpsertSerializer(data={
        "diagram_id": data.get("diagram_id"),
        "task_id": data.get("task_id"),
        "name": data.get("name"),
        "atomic_type": data.get("atomic_type"),
        "method": data.get("method"),
        "url": data.get("url"),
        "owner": data.get("owner"),
        "input": data.get("input"),
        "output": data.get("output"),
    })
    ser.is_valid(raise_exception=True)

    # Salvataggio atomic nel DB
    result, status_code = MongoDBHandler.save_atomic({
        "diagram_id": data["diagram_id"],
        "task_id": data["task_id"],
        "name": data["name"],
        "atomic_type": data["atomic_type"],
        "method": data["method"],
        "url": data["url"],
        "owner": data["owner"],
        "input": data["input"],
        "output": data["output"],
    })

    # Se ok, pubblica la OpenAPI
    if status_code in (200, 201):
        servers = [{"url": request.build_absolute_uri("/").rstrip("/")}]
        pub_res = publish_atomic_spec(service_id=data["task_id"], servers=servers)

        json_url = reverse("openapi_docs:atomic-oas-latest", args=[data["task_id"]])
        swagger_url = reverse("openapi_docs:atomic-docs-latest", args=[data["task_id"]])
        
        rbac.atomic_policy(data)

        return Response({
            "status": "ok",
            "atomic_service": result,
            "openapi_publish": pub_res,
            "links": {"json": json_url, "swagger": swagger_url}
        }, status=status.HTTP_201_CREATED if status_code == 201 else status.HTTP_200_OK)

    return Response({
        "status": "error",
        "detail": "Atomic not saved, OpenAPI skipped",
        "atomic_service": result
    }, status=status_code)

@api_view(['POST'])
def save_cpps_service(request):
    data = request.data
    print("===CPPS Payload received:", data)

    # Estraggo componenti
    components = data.get('components', [])
    component_ids = [c['id'] for c in components if c['type'] == 'Atomic']
    cpps_ids = [c['id'] for c in components if c['type'] == 'CPPS']

    # Recupero documenti atomic e cpps annidati
    atomic_map = {
        a["task_id"]: a
        for a in atomic_services_collection.find({"task_id": {"$in": component_ids}})
    }

    cpps_map = {
        c["group_id"]: c
        for c in cpps_collection.find({"group_id": {"$in": cpps_ids}})
    }

    # Normalizza components e workflow
    data["components"], data["workflow"] = normalize_components_and_workflow(data, cpps_map)
    
    # Salva nel DB
    result, status_code = MongoDBHandler.save_cpps(data)

    if status_code in [200, 201]:
        # Genera e pubblica OpenAPI
        servers = [{"url": request.build_absolute_uri("/").rstrip("/")}]
        pub_res = publish_cpps_spec(group_id=data["group_id"], servers=servers)

        if pub_res.get("status") == "ok":
            doc_result, doc_status = pub_res, 201
            print("===OpenAPI doc published:", pub_res)
        else:
            doc_result, doc_status = {
                "message": "OpenAPI publish failed",
                "errors": pub_res.get("errors")
            }, 400
        #scrivo policy
        rbac.cpps_policy(data, component_ids, cpps_ids)

    else:
        doc_result, doc_status = {"message": "CPPS not saved, skipping OpenAPI"}, 400

    return Response({
        "cpps_service": result,
        "openapi_documentation": doc_result
    }, status=status_code)

def normalize_components_and_workflow(data, cpps_map):
    """
    Normalizza il CPPS esterno per avere un workflow del tipo:
      - Activity_esterna -> Group_interno
      - Group_interno   -> Activity_esterna
    Collassa qualsiasi nodo interno (Atomic o Gateway) al relativo group_id.
    NON risale oltre 1 livello di annidamento (voluto).
    """
    components = data.get('components', [])
    workflow = data.get('workflow', {})

    # id -> type (per riconoscere gateway/cpps)
    comp_type = {c["id"]: c["type"] for c in components}

    # ---- Indici 1-livello sui CPPS annidati ----
    # atomic interno -> group che lo contiene
    atomic_to_group = {}
    # nodo interno (atomic o gateway) -> group che lo contiene
    node_to_group = {}
    # per ogni group, insieme dei suoi id interni (atomic+gateway)
    group_inner = {}

    for comp in components:
        if comp.get("type") == "CPPS":
            gid = comp["id"]
            inner = set()
            nested = cpps_map.get(gid, {}).get("components", [])
            for c in nested:
                cid, ctype = c.get("id"), c.get("type")
                inner.add(cid)
                node_to_group[cid] = gid
                if ctype == "Atomic":
                    atomic_to_group[cid] = gid
            group_inner[gid] = inner

    nested_atomic_ids = set(atomic_to_group.keys())
    nested_internal_ids = set(node_to_group.keys())  # atomic + gateway interni

    # ---- Filtro componenti del CPPS esterno: rimuovi nodi interni (atomic/gateway) ----
    filtered_components = []
    for c in components:
        cid, ctype = c["id"], c["type"]
        # escludo tutto ciò che è interno a un CPPS annidato (tranne il CPPS stesso)
        if cid in nested_internal_ids and ctype != "CPPS":
            continue
        # escludo atomic duplicati interni
        if ctype == "Atomic" and cid in nested_atomic_ids:
            continue
        filtered_components.append(c)

    # ---- Costruisco workflow esterno con soli Activity->Group e Group->Activity ----
    mapped = OrderedDict()

    def add_edge(src, tgt, store=mapped):
        if src == tgt:
            return  # evita self-loop
        if src not in store:
            store[src] = []
        if tgt not in store[src]:
            store[src].append(tgt)

    for source, targets in workflow.items():
        if source in nested_internal_ids:
            # Sorgente interna (atomic/gateway di un CPPS): alza a group_id (uscita del CPPS)
            gid = node_to_group[source]
            inner = group_inner.get(gid, set())
            for t in targets:
                if t in inner:
                    continue  # interno->interno: non esce dal group
                # mappa target che è nodo interno di altri CPPS al relativo group
                t_mapped = node_to_group.get(t, atomic_to_group.get(t, t))
                if t_mapped == gid:
                    continue  # evita group -> group sullo stesso group
                add_edge(gid, t_mapped)
        else:
            # Sorgente esterna: ingresso nel CPPS (collassa target interni - atomic o gateway - al loro group)
            dedup = []
            for t in targets:
                t_mapped = node_to_group.get(t, atomic_to_group.get(t, t))
                if t_mapped != source and t_mapped not in dedup:
                    dedup.append(t_mapped)
            for t in dedup:
                add_edge(source, t)

    # ---- Compressione leggera di gateway ESTERNI lineari (pred -> gw -> unico tgt) ----
    predecessors = {}
    for s, tgts in mapped.items():
        for t in tgts:
            predecessors.setdefault(t, set()).add(s)

    compressed = OrderedDict()
    compressed_gateways = set()

    def add_c(src, tgt):
        add_edge(src, tgt, store=compressed)

    for src, tgts in mapped.items():
        is_gateway = comp_type.get(src, '').endswith('Gateway')
        if is_gateway:
            preds = list(predecessors.get(src, []))
            # uniq targets preservando l'ordine
            uniq_tgts = []
            for t in tgts:
                if t not in uniq_tgts:
                    uniq_tgts.append(t)
            # comprimi se c'è un solo predecessore e (dopo mapping) un solo target effettivo
            if len(preds) == 1 and len(set(uniq_tgts)) == 1:
                add_c(preds[0], uniq_tgts[0])
                compressed_gateways.add(src)
                continue
        # caso standard
        for t in tgts:
            add_c(src, t)

    # Rimuove i gateway compressi dai target
    if compressed_gateways:
        for s, tgts in list(compressed.items()):
            new_tgts = [t for t in tgts if t not in compressed_gateways]
            if new_tgts:
                compressed[s] = new_tgts
            else:
                del compressed[s]

    # ---------- FLATTEN: Group -> Atomic_interna_finale -> X  ==>  Group -> X ----------
    # Applica finché non ci sono più casi; copre fuga di un'Atomic finale marcata come sorgente.
    changed = True
    while changed:
        changed = False

        # ricalcola i predecessori sul grafo corrente
        predecessors = {}
        for s, tgts in compressed.items():
            for t in tgts:
                predecessors.setdefault(t, set()).add(s)

        to_delete_sources = set()
        updates = []  # (group, old_atomic_target, new_targets_list)

        for g, tgts in compressed.items():
            # considera solo sorgenti che sono group (CPPS)
            if g not in cpps_map:
                continue
            for a in list(tgts):
                # a) 'a' è un'Atomic
                # b) 'a' compare come sorgente
                # c) l'unico predecessore di 'a' è proprio 'g'
                if comp_type.get(a) == "Atomic" and a in compressed and predecessors.get(a, {None}) == {g}:
                    # sposta g->a->T su g->T (dedup, no self-loop)
                    new_targets = []
                    for t in compressed[a]:
                        if t != g and t not in tgts:
                            new_targets.append(t)
                    if new_targets:
                        updates.append((g, a, new_targets))
                        to_delete_sources.add(a)
                        changed = True

        # applica gli aggiornamenti raccolti
        for g, a, new_targets in updates:
            compressed[g] = [t for t in compressed[g] if t != a]
            for t in new_targets:
                if t not in compressed[g]:
                    compressed[g].append(t)

        # cancella le sorgenti appiattite
        for a in to_delete_sources:
            compressed.pop(a, None)

    # Purge finale: niente self-loop e niente entry vuote
    for s in list(compressed.keys()):
        compressed[s] = [t for t in compressed[s] if t != s]
        if not compressed[s]:
            del compressed[s]

    # ---- Risultato: Activity->Group e Group->Activity, senza leak di nodi interni ----
    return filtered_components, compressed

def normalize_cppn_components_and_workflow(
    data,
    cpps_map,
    *,
    compress_trivial_gateways: bool = False,
    boundary_only: bool = False,
):
    """
    CPPN normalize:
    - Mantiene i GATEWAY *esterni* (non interni a CPPS annidati).
    - Collassa qualsiasi nodo *interno* ai CPPS (Atomic o Gateway) al relativo group_id.
    - Opzioni:
        compress_trivial_gateways: comprime solo gateway esterni banali (1 pred -> gw -> 1 tgt)
        boundary_only: se True, tiene solo archi che toccano almeno un CPPS (group)
    """
    components = data.get("components", [])
    workflow   = data.get("workflow", {})

    # id -> type, set dei group (CPPS referenziati nel CPPN)
    comp_type = {c["id"]: c["type"] for c in components}
    groups    = {c["id"] for c in components if c.get("type") == "CPPS"}

    # ---- Indici 1-livello per i CPPS annidati ----
    # nodo interno (atomic o gateway) -> group che lo contiene
    node_to_group = {}
    # per ogni group, insieme dei suoi id interni
    group_inner = {}
    # atomic interni (utile per chiarezza; non indispensabile separatamente)
    nested_atomic_ids = set()

    for c in components:
        if c.get("type") == "CPPS":
            gid = c["id"]
            inner = set()
            nested = cpps_map.get(gid, {}).get("components", [])
            for n in nested:
                nid, ntype = n.get("id"), n.get("type")
                inner.add(nid)
                node_to_group[nid] = gid
                if ntype == "Atomic":
                    nested_atomic_ids.add(nid)
            group_inner[gid] = inner

    nested_internal_ids = set(node_to_group.keys())  # atomic + gateway interni

    # ---- Filtra i componenti del CPPN: rimuove solo i nodi interni ai CPPS ----
    filtered_components = []
    for c in components:
        cid, ctype = c["id"], c["type"]
        if cid in nested_internal_ids and ctype != "CPPS":
            continue  # non far trapelare i nodi interni ai CPPS
        filtered_components.append(c)

    # ---- Costruisco il workflow tenendo i gateway ESTERNI ----
    mapped = OrderedDict()

    def add_edge(store, s, t):
        if s == t:
            return
        if s not in store:
            store[s] = []
        if t not in store[s]:
            store[s].append(t)

    for source, targets in workflow.items():
        if source in nested_internal_ids:
            # Sorgente interna a un CPPS: alza al relativo group (uscita del CPPS)
            gid = node_to_group[source]
            inner = group_inner.get(gid, set())
            for t in targets:
                if t in inner:
                    continue  # interno->interno: resta nel CPPS, non trapela
                # se il target è interno a QUALCHE CPPS, collassa a quel group
                t_mapped = node_to_group.get(t, t)
                if t_mapped == gid:
                    continue  # evita self-loop group->group sullo stesso CPPS
                add_edge(mapped, gid, t_mapped)
        else:
            # Sorgente esterna (Activity, Gateway, Group esterno): mantenura
            dedup = []
            for t in targets:
                # target interno? collassa al relativo group
                t_mapped = node_to_group.get(t, t)
                if t_mapped != source and t_mapped not in dedup:
                    dedup.append(t_mapped)
            for t in dedup:
                add_edge(mapped, source, t)

    # ---- (opzionale) comprimo solo gateway ESTERNI banali ----
    if compress_trivial_gateways:
        # calcola predecessori
        preds = {}
        for s, tgts in mapped.items():
            for t in tgts:
                preds.setdefault(t, set()).add(s)

        compressed = OrderedDict()
        removed_gw = set()

        def add_c(s, t):
            add_edge(compressed, s, t)

        for src, tgts in mapped.items():
            is_external_gw = comp_type.get(src, "").endswith("Gateway") and (src not in nested_internal_ids)
            uniq_tgts = []
            for t in tgts:
                if t not in uniq_tgts:
                    uniq_tgts.append(t)

            if is_external_gw:
                src_preds = list(preds.get(src, []))
                if len(src_preds) == 1 and len(uniq_tgts) == 1:
                    add_c(src_preds[0], uniq_tgts[0])
                    removed_gw.add(src)
                    continue
            for t in uniq_tgts:
                add_c(src, t)

        # purge target = gateway compresso
        if removed_gw:
            for s, tgts in list(compressed.items()):
                new_t = [t for t in tgts if t not in removed_gw]
                if new_t:
                    compressed[s] = new_t
                else:
                    del compressed[s]
        mapped = compressed

    # ---- boundary-only: tieni solo archi che toccano almeno un CPPS ----
    if boundary_only:
        boundary = {}
        for s, tgts in mapped.items():
            keep = [t for t in tgts if (s in groups) or (t in groups)]
            if keep:
                boundary[s] = keep
        mapped = boundary

    # ---- pulizia finale: no self-loop, no entry vuote ----
    for s in list(mapped.keys()):
        mapped[s] = [t for t in mapped[s] if t != s]
        if not mapped[s]:
            del mapped[s]

    return filtered_components, mapped

@api_view(['POST'])
def save_cppn_service(request):
    data = request.data
    print("===CPPN Payload received:", data)

    # Prepara mappe CPPS (servono per normalizzare)
    components = data.get('components', [])
    cpps_ids = [c['id'] for c in components if c['type'] == 'CPPS']
    cpps_map = { c["group_id"]: c for c in cpps_collection.find({"group_id": {"$in": cpps_ids}}) }

    data["components"], data["workflow"] = normalize_cppn_components_and_workflow(data, cpps_map)

   # Salva CPPN nel database
    result, status_code = MongoDBHandler.save_cppn(data)

    if status_code in [200, 201]:
        # servers per self-link corretti
        servers = [{"url": request.build_absolute_uri("/").rstrip("/")}]
        pub_res = publish_cppn_spec(group_id=data["group_id"], servers=servers)

        if pub_res.get("status") == "ok":
            # link per la UI 
            json_url = reverse("openapi_docs:cppn-oas-latest", args=[data["group_id"]])
            swagger_url = reverse("openapi_docs:swagger-viewer-cppn", args=[data["group_id"]])
            doc_result, doc_status = {
                **pub_res,
                "links": {"json": json_url, "swagger": swagger_url}
            }, 201
            print("===OpenAPI CPPN published:", pub_res)

            rbac.cppn_policy(data, data["components"])
        else:
            doc_result, doc_status = {
                "message": "OpenAPI publish failed",
                "errors": pub_res.get("errors")
            }, 400
    else:
        doc_result, doc_status = {"message": "CPPN not saved, skipping OpenAPI"}, 400

    return Response({
        "cppn_service": result,
        "openapi_documentation": doc_result
    }, status=status_code)


@api_view(['GET'])
def get_cppn_service(request, group_id):
    service = cppn_collection.find_one({'group_id': group_id})
    if not service:
        return JsonResponse({'error': 'CPPN not found'}, status=404)

    return JsonResponse(service, safe=False, json_dumps_params={'default': json_util.default})

@api_view(['GET'])
def get_cpps_service(request, group_id):
    service = cpps_collection.find_one({'group_id': group_id})
    if not service:
        return Response({'error': 'CPPS not found'}, status=404)

    return JsonResponse(service, safe=False, json_dumps_params={'default': json_util.default})


@api_view(['GET'])
def get_atomic_service(request, task_id):
    service = atomic_services_collection.find_one({'task_id': task_id})
    if not service:
        return JsonResponse({'error': 'Atomic service not found'}, status=404)
    return JsonResponse(service, safe=False, json_dumps_params={'default': json_util.default})


@api_view(['GET'])
def get_all_services(request):
    atomic = list(atomic_services_collection.find(
        {},
        {
            '_id': 0,
            'task_id': 1,
            'name': 1,
            'description': 1,
            'input': 1,
            'output': 1,
            'input_params': 1,
            'output_params': 1,
            'owner' : 1,
            'atomic_type' : 1,
            'url' : 1,
            'method' : 1
        }
    ))

    # normalizzazione server-side
    for a in atomic:
        a['input']  = a.get('input')  or a.get('input_params')  or {}
        a['output'] = a.get('output') or a.get('output_params') or {}
        a.pop('input_params', None)
        a.pop('output_params', None)

    cpps = list(cpps_collection.find(
        {},
        {
            '_id': 0,
            'group_id': 1,
            'name': 1,
            'description': 1,
            'components': 1,
            'owner': 1
        }
    ))

    cppn = list(cppn_collection.find(
        {},
        {
            '_id': 0,
            'group_id': 1,
            'name': 1,
            'description': 1,
            'components': 1,
            'actors': 1,
            'gdpr_map': 1,
            'business_goal': 1
        }
    ))

    return Response({
        'atomic': atomic,
        'cpps': cpps,
        'cppn': cppn
    })

@api_view(['DELETE'])
def delete_group(request, group_id):
    try:
        # Prova cancellare da CPPS
        deleted_cpps = cpps_collection.find_one_and_delete({'group_id': group_id})

        # Prova cancellare anche da CPPN
        deleted_cppn = cppn_collection.find_one_and_delete({'group_id': group_id})

        deleted_any = bool(deleted_cpps or deleted_cppn)

        # --- Pulizia riferimenti in altri documenti ---

        # rimozione da components e workflow
        pipeline = [
            { "$set": {
                # components: rimuovi item con id == group_id (facoltativo filtrare anche per type == "CPPS")
                "components": {
                    "$filter": {
                        "input": "$components",
                        "as": "c",
                        "cond": { "$ne": ["$$c.id", group_id] }
                        # Se vuoi essere più stretto:
                        # "cond": { "$not": { "$and": [ { "$eq": ["$$c.id", group_id] }, { "$eq": ["$$c.type", "CPPS"] } ] } }
                    }
                }
            }},
            { "$set": {
                # workflow: elimina la chiave uguale a group_id
                "workflow": {
                    "$cond": [
                        { "$and": [
                            { "$ne": ["$workflow", None] },
                            { "$eq": [ { "$type": "$workflow" }, "object" ] }
                        ]},
                        {
                            "$arrayToObject": {
                                "$map": {
                                    "input": {
                                        "$filter": {
                                            "input": { "$objectToArray": "$workflow" },
                                            "as": "w",
                                            "cond": { "$ne": ["$$w.k", group_id] }
                                        }
                                    },
                                    "as": "w",
                                    "in": {
                                        "k": "$$w.k",
                                        # rimuove group_id da ogni lista di destinazioni
                                        "v": {
                                            "$cond": [
                                                { "$isArray": "$$w.v" },
                                                {
                                                    "$filter": {
                                                        "input": "$$w.v",
                                                        "as": "t",
                                                        "cond": { "$ne": ["$$t", group_id] }
                                                    }
                                                },
                                                "$$w.v"
                                            ]
                                        }
                                    }
                                }
                            }
                        },
                        "$workflow"
                    ]
                }
            }},

            # rimuovo group_id da nested_cpps (se esiste e se è un array)
            { "$set": {
                "nested_cpps": {
                    "$cond": [
                        { "$isArray": "$nested_cpps" },
                        {
                            "$filter": {
                                "input": "$nested_cpps",
                                "as": "n",
                                "cond": { "$ne": ["$$n", group_id] }
                            }
                        },
                        "$nested_cpps"
                    ]
                }
            }}
        ]

        # Applica solo a documenti che potenzialmente contengono riferimenti
        match = {
            "$or": [
                {"components.id": group_id},
                {f"workflow.{group_id}": {"$exists": True}},
                {"workflow": {"$elemMatch": {"$in": [group_id]}}},  # non funziona con object, lascio gli altri due controlli
                {"nested_cpps": group_id}
            ]
        }

        cpps_update = cpps_collection.update_many(match, pipeline)
        cppn_update = cppn_collection.update_many(match, pipeline)

        # 3) Fallback: un pull semplice su nested_cpps per sicurezza
        pull_nested = {"$pull": {"nested_cpps": group_id}}
        cpps_pull = cpps_collection.update_many({"nested_cpps": group_id}, pull_nested)
        cppn_pull = cppn_collection.update_many({"nested_cpps": group_id}, pull_nested)

        if deleted_any:
            return Response({
                "message": f"Gruppo {group_id} deleted!",
                "deleted_from_cpps": bool(deleted_cpps),
                "deleted_from_cppn": bool(deleted_cppn),
                "updated_cpps_docs": cpps_update.modified_count,
                "updated_cppn_docs": cppn_update.modified_count,
                "pulled_cpps_nested": cpps_pull.modified_count,
                "pulled_cppn_nested": cppn_pull.modified_count
            }, status=status.HTTP_200_OK)

        return Response({
            "error": f"Gruppo {group_id} not found",
            "updated_cpps_docs": cpps_update.modified_count,
            "updated_cppn_docs": cppn_update.modified_count,
            "pulled_cpps_nested": cpps_pull.modified_count,
            "pulled_cppn_nested": cppn_pull.modified_count
        }, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
def add_nested_cpps(request, group_id):
    nested_id = request.data.get('nested_id')
    if not nested_id:
        return Response({'error': 'Missing nested_id'}, status=400)

    result = cpps_collection.update_one(
        {'group_id': group_id},
        {'$addToSet': {'nested_cpps': nested_id}}
    )

    if result.matched_count == 0:
        return Response({'error': 'Parent CPPS not found'}, status=404)

    return Response({'status': 'nested_cpps updated'})


@api_view(['DELETE'])
def delete_atomic(request, atomic_id):
    try:
        # Elimino atomic dalla sua collection
        deleted = atomic_services_collection.find_one_and_delete({'task_id': atomic_id})
        if not deleted:
            return Response({'error': 'Atomic service not found'}, status=404)

        # Pipeline che:
        # - filtra components rimuovendo gli item con id == atomic_id
        # - rimuove la chiave di workflow == atomic_id
        # - rimuove atomic_id da TUTTE le liste di workflow
        pipeline = [
            { "$set": {
                "components": {
                    "$filter": {
                        "input": "$components",
                        "as": "c",
                        "cond": { "$ne": ["$$c.id", atomic_id] }
                    }
                }
            }},
            { "$set": {
                "workflow": {
                    "$arrayToObject": {
                        "$map": {
                            "input": {
                                # toglie eventuale entry con chiave == atomic_id
                                "$filter": {
                                    "input": { "$objectToArray": "$workflow" },
                                    "as": "w",
                                    "cond": { "$ne": ["$$w.k", atomic_id] }
                                }
                            },
                            "as": "w",
                            "in": {
                                "k": "$$w.k",
                                # rimuove atomic_id da ogni lista destinazioni
                                "v": {
                                    "$filter": {
                                        "input": "$$w.v",
                                        "as": "t",
                                        "cond": { "$ne": ["$$t", atomic_id] }
                                    }
                                }
                            }
                        }
                    }
                }
            }}
        ]

        # Applicazione la pipeline a TUTTI i doc
        cpps_result = cpps_collection.update_many({}, pipeline)
        cppn_result = cppn_collection.update_many({}, pipeline)

        return Response({
            "status": "deleted",
            "removed_from_cpps": cpps_result.modified_count,
            "removed_from_cppn": cppn_result.modified_count
        }, status=200)  
    
    except Exception as e:
        print(f"Error during atomic delete: {e}")
        return Response({"error": str(e)}, status=500)

@api_view(['DELETE'])
def delete_diagram_and_services(request, diagram_id):
    try:
        obj_id = ObjectId(diagram_id)

        # Elimina il diagramma
        result = bpmn_collection.delete_one({"_id": obj_id})
        if result.deleted_count == 0:
            return Response({"error": "Diagram not found"}, status=404)

        # Elimina atomic services collegati
        atomic_deleted = atomic_services_collection.delete_many({"diagram_id": diagram_id})

        # Elimina CPPS collegati
        cpps_deleted = cpps_collection.delete_many({"diagram_id": diagram_id})

        # Elimina CPPN collegati
        cppn_deleted = cppn_collection.delete_many({"diagram_id": diagram_id})

        # Elimina documentazione OpenAPI associata
        openapi_deleted = openapi_collection.delete_many({"info.x-diagram_id": diagram_id})

        # Elimina rbac dei servizi del diagramma
        rbac_delted = rbac_collection.delete_many({"diagram_id": diagram_id})


        return Response({
            "status": "deleted",
            "diagram_id": diagram_id,
            "atomic_deleted": atomic_deleted.deleted_count,
            "cpps_deleted": cpps_deleted.deleted_count,
            "cppn_deleted": cppn_deleted.deleted_count,
            "openapi_deleted": openapi_deleted.deleted_count
        }, status=200)

    except InvalidId:
        return Response({"error": "Invalid diagram ID"}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
