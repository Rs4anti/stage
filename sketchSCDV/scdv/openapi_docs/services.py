# openapi_docs/services.py
import hashlib, json
from datetime import datetime
from typing import Optional, Tuple

# riuso diretto delle collection dal tuo modulo
from utilities.mongodb_handler import atomic_services_collection, openapi_collection

from openapi_docs.openapi_generator import OpenAPIGenerator
from openapi_docs.oas_validation import validate_openapi


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def _sha256(obj) -> str:
    canon = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canon).hexdigest()

def _parse_semver(v: str) -> Tuple[int, int, int]:
    try:
        M, m, p = v.split(".")
        return int(M), int(m), int(p)
    except Exception:
        return (0, 0, 0)

def _format_semver(t: Tuple[int,int,int]) -> str:
    return f"{t[0]}.{t[1]}.{t[2]}"

def _latest_published_version(service_id: str) -> Optional[str]:
    """
    Cerca in `openapi` la versione pubblicata più alta (semver) per il servizio.
    """
    cur = openapi_collection.find(
        {"level": "atomic", "service_id": service_id, "status": "published"},
        {"version": 1, "_id": 0}
    )
    best = None
    best_t = (-1, -1, -1)
    for doc in cur:
        v = doc.get("version")
        if not v:
            continue
        t = _parse_semver(v)
        if t > best_t:
            best_t, best = t, v
    return best

def _bump_patch(v: Optional[str]) -> str:
    if not v:
        return "1.0.0"   # prima pubblicazione
    M, m, p = _parse_semver(v)
    return _format_semver((M, m, p + 1))


def upsert_atomic(doc: dict) -> dict:
    """
    Salva/aggiorna il documento Atomic (senza toccare le OpenAPI).
    doc deve contenere: diagram_id, task_id, name, atomic_type, method, url, owner, input, output
    """
    atomic_services_collection.update_one(
        {"task_id": doc["task_id"]},
        {"$set": {
            "diagram_id": doc["diagram_id"],
            "name": doc["name"],
            "atomic_type": doc["atomic_type"],
            "method": doc["method"],
            "url": doc["url"],
            "owner": doc["owner"],
            "input": doc["input"],
            "output": doc["output"],
            "updated_at": _now_iso()
        }, "$setOnInsert": {"created_at": _now_iso()}},
        upsert=True
    )
    return atomic_services_collection.find_one({"task_id": doc["task_id"]}, {"_id": 0})


def publish_atomic_spec(service_id: str, servers: list | None = None) -> dict:
    """
    Genera, valida e pubblica (status=published) la OpenAPI per l'Atomic indicato.
    - versione = patch + 1 della latest pubblicata; se non esiste, 1.0.0
    - salva in `openapi` un documento con level=atomic
    """
    atomic = atomic_services_collection.find_one({"task_id": service_id})
    if not atomic:
        return {"status": "error", "detail": "Atomic not found"}

    base = _latest_published_version(service_id)  # può essere None
    version = _bump_patch(base)

    oas = OpenAPIGenerator.generate_atomic_openapi(atomic, version=version)
    if servers:
        oas["servers"] = servers

    ok, errs = validate_openapi(oas)
    if not ok:
        return {"status": "error", "errors": errs}

    openapi_collection.insert_one({
        "level": "atomic",
        "service_id": service_id,
        "diagram_id": atomic.get("diagram_id"),
        "owner": atomic.get("owner"),
        "name": atomic.get("name"),
        "version": version,
        "status": "published",
        "hash": _sha256(oas),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "oas": oas,
        "meta": {"source": "generator", "tags": []}
    })

    return {"status": "ok", "service_id": service_id, "version": version}

# openapi_docs/services.py
def republish_atomic_spec(service_id: str, servers: list|None=None) -> dict:
    """
    Pubblica una nuova versione della OAS per un atomic già presente.
    Versione = latest patch + 1 (o 1.0.0 se non esiste nulla).
    """
    atomic = atomic_services_collection.find_one({"task_id": service_id})
    if not atomic:
        return {"status": "error", "detail": "Atomic not found"}

    base = _latest_published_version(service_id)
    version = _bump_patch(base)

    oas = OpenAPIGenerator.generate_atomic_openapi(atomic, version=version)
    if servers:
        oas["servers"] = servers

    ok, errs = validate_openapi(oas)
    if not ok:
        return {"status": "error", "errors": errs}

    openapi_collection.insert_one({
        "level": "atomic",
        "service_id": service_id,
        "diagram_id": atomic.get("diagram_id"),
        "owner": atomic.get("owner"),
        "name": atomic.get("name"),
        "version": version,
        "status": "published",
        "hash": _sha256(oas),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "oas": oas,
        "meta": {"source": "generator", "tags": []}
    })
    return {"status": "ok", "service_id": service_id, "version": version}

