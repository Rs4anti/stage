from utilities.mongodb_handler import rbac_collection
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from datetime import datetime
from bson import ObjectId

@api_view(['GET'])
def get_diagram_atomic_rbac(request):
    """
    GET /api/rbac/policies/atomic/by-diagram?id=<diagram_id>
    Returns atomic RBAC policies filtered by diagram_id.
    """
    diagram_id = request.query_params.get("id")
    if not diagram_id:
        return Response(
            {"detail": "Parametro 'id' (diagram_id) obbligatorio."},
            status=status.HTTP_400_BAD_REQUEST
        )

    query = {
        "diagram_id": diagram_id,
        "service_type": "atomic"
    }

    cursor = rbac_collection.find(query)

    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)

    return Response({
        "count": len(results),
        "results": results
    }, status=status.HTTP_200_OK)

def rbac_atomic_view(request):
    return render(request, "editor/rbac_atomic.html")

def rbac_atomic_edit(request, atomic_id):
    # TODO: render pagina di modifica (form) per atomic_id
    return render(request, "editor/rbac_atomic_edit.html", {"atomic_id": atomic_id, "diagram_id": request.GET.get("id")})


def _sanitize(doc: dict) -> dict:
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["_id"] = str(d["_id"])
    return d

@api_view(["GET"])
def get_atomic_policy_by_atomic_id(request):
    """
    GET /editor/api/rbac/policies/atomic/by-id?atomic_id=Activity_1u1y293[&diagram_id=...]
    Ritorna il documento RBAC (service_type=atomic) con quell'atomic_id.
    Se diagram_id è passato, filtra anche su quello.
    """
    atomic_id = request.query_params.get("atomic_id")
    if not atomic_id:
        return Response({"detail": "Parametro 'atomic_id' obbligatorio."},
                        status=status.HTTP_400_BAD_REQUEST)

    q = {"service_type": "atomic", "atomic_id": atomic_id}
    diagram_id = request.query_params.get("diagram_id")
    if diagram_id:
        q["diagram_id"] = diagram_id

    doc = rbac_collection.find_one(q)
    if not doc:
        return Response({"detail": "Policy non trovata."}, status=status.HTTP_404_NOT_FOUND)

    return Response(_sanitize(doc), status=status.HTTP_200_OK)


@api_view(["GET"])
def get_diagram_actors(request):
    """
    GET /editor/api/actors?diagram_id=<id>
    Ritorna l'insieme (ordinato) degli attori del diagramma, basato SOLO su owner
    dei documenti RBAC atomic.
    """
    diagram_id = request.query_params.get("diagram_id") or request.query_params.get("id")
    if not diagram_id:
        return Response({"detail": "Parametro 'diagram_id' (o 'id') obbligatorio."},
                        status=status.HTTP_400_BAD_REQUEST)

    query = {"diagram_id": diagram_id, "service_type": "atomic"}
    projection = {"_id": 0, "owner": 1}

    actors = { (doc.get("owner") or "").strip()
               for doc in rbac_collection.find(query, projection)
               if (doc.get("owner") or "").strip() }

    return Response({
        "diagram_id": diagram_id,
        "count": len(actors),
        "actors": sorted(actors)
    }, status=status.HTTP_200_OK)


def _stringify_ids(d):
    if isinstance(d, list):
        return [_stringify_ids(x) for x in d]
    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            if isinstance(v, ObjectId):
                out[k] = str(v)
            else:
                out[k] = _stringify_ids(v)
        return out
    return d

@api_view(["PUT"])
def update_atomic_permissions(request):
    """
    PUT /editor/api/rbac/policies/atomic/permissions
    Body JSON:
    {
      "diagram_id": "...",          # obbligatorio
      "atomic_id": "...",           # obbligatorio
      "permission_actors": ["A1","A2"]  # opzionale: attori extra (≠ owner) con invoke
    }
    - Aggiorna SOLO le permissions del documento (owner resta invoke).
    - 404 se il documento non esiste.
    """
    body = request.data if isinstance(request.data, dict) else {}
    diagram_id = str(body.get("diagram_id", "")).strip()
    atomic_id  = str(body.get("atomic_id", "")).strip()
    if not diagram_id or not atomic_id:
        return Response({"detail": "diagram_id e atomic_id sono obbligatori."},
                        status=status.HTTP_400_BAD_REQUEST)

    # Recupera doc esistente (obbligatorio)
    filt = {"diagram_id": diagram_id, "atomic_id": atomic_id, "service_type": "atomic"}
    doc = rbac_collection.find_one(filt, {"owner": 1, "_id": 0})
    if not doc:
        return Response({"detail": "Policy non trovata."}, status=status.HTTP_404_NOT_FOUND)
    owner = (doc.get("owner") or "").strip()

    # Normalizza attori extra
    raw = body.get("permission_actors") or []
    if not isinstance(raw, list):
        return Response({"detail": "permission_actors deve essere una lista."},
                        status=status.HTTP_400_BAD_REQUEST)

    seen = set()
    extra = []
    for a in raw:
        a = str(a or "").strip()
        if not a or a == owner:
            continue
        k = a.lower()
        if k in seen:  # unici case-insensitive
            continue
        seen.add(k)
        extra.append(a)

    new_permissions = [{"actor": owner, "permission": "invoke"}] + [
        {"actor": a, "permission": "invoke"} for a in extra
    ]

    rbac_collection.update_one(
        filt,
        {"$set": {"permissions": new_permissions, "updated_at": datetime.utcnow()}}
    )
    out = rbac_collection.find_one(filt)
    return Response({"status": "permissions_updated", "result": _stringify_ids(out)},
                    status=status.HTTP_200_OK)