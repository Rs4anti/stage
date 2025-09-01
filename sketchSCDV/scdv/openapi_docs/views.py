# openapi_docs/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from utilities.mongodb_handler import openapi_collection, atomic_services_collection

from openapi_docs.serializers import AtomicUpsertSerializer
from openapi_docs.services import (
    upsert_atomic,
    publish_atomic_spec,
    republish_atomic_spec,
    _latest_published_version,   # riuso per la latest
)

# openapi_docs/views.py (aggiungi in cima al file)
from django.shortcuts import render
from django.urls import reverse

def openapi_docs_home(request):
    return render(request, "openapi_docs/openapi_docs.html")  # il tuo template homepage


@api_view(["POST"])
#@permission_classes([IsAuthenticated])   # rimuovi se vuoi testare senza auth
def atomic_upsert(request):
    """
    Upsert dell'atomic + pubblicazione automatica della sua OpenAPI.
    """
    ser = AtomicUpsertSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    atomic_doc = upsert_atomic(ser.validated_data)

    # opzionale: aggiungiamo servers alla OAS con la base URL calcolata dalla request
    servers = [{"url": request.build_absolute_uri("/").rstrip("/")}]

    pub = publish_atomic_spec(service_id=atomic_doc["task_id"], servers=servers)
    if pub.get("status") != "ok":
        return Response(pub, status=status.HTTP_400_BAD_REQUEST)

    return Response({"status": "ok", "atomic": atomic_doc, "openapi": pub}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
#@permission_classes([IsAuthenticated])   # rimuovi se vuoi testare senza auth
def atomic_oas_latest(request, service_id: str):
    """
    Ritorna la OAS JSON latest (versione pubblicata più alta) per l'atomic indicato.
    """
    latest = _latest_published_version(service_id)
    if not latest:
        return Response({"detail": "No published version"}, status=404)

    doc = openapi_collection.find_one({
        "level": "atomic",
        "service_id": service_id,
        "version": latest,
        "status": "published"
    }, {"_id": 0, "oas": 1})

    if not doc:
        return Response({"detail": "Spec not found"}, status=404)

    return Response(doc["oas"])


@api_view(["GET"])
#@permission_classes([IsAuthenticated])   # rimuovi se vuoi testare senza auth
def atomic_oas_version(request, service_id: str, version: str):
    """
    Ritorna la OAS JSON per versione specifica.
    """
    doc = openapi_collection.find_one({
        "level": "atomic",
        "service_id": service_id,
        "version": version
    }, {"_id": 0, "oas": 1})

    if not doc:
        return Response({"detail": "Spec not found"}, status=404)

    return Response(doc["oas"])

@api_view(["POST"])
def atomic_republish(request, service_id: str):
    servers = [{"url": request.build_absolute_uri("/").rstrip("/")}]
    res = republish_atomic_spec(service_id=service_id, servers=servers)
    status_code = 200 if res.get("status") == "ok" else 400
    return Response(res, status=status_code)


def atomic_docs_list(request):
    cur = atomic_services_collection.find({}, {"_id":0,"task_id":1,"name":1,"method":1,"url":1}).sort("name", 1)
    services = []
    for d in cur:
        task_id = d["task_id"]
        services.append({
            "task_id": task_id,
            "name": d["name"],
            "method": d["method"],
            "url": d["url"],
            "json_url": reverse("openapi_docs:atomic-oas-latest", args=[task_id]),
            "swagger_url": reverse("openapi_docs:atomic-docs-latest", args=[task_id]),
        })
    return render(request, "openapi_docs/atomic_docs.html", {"services": services})