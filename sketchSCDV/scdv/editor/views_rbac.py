from utilities.mongodb_handler import rbac_collection
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render

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