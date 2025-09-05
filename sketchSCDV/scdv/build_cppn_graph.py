# build_cppn_graph.py
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set

# ==================== Helpers su tipi / etichette ====================

def node_type(node_id: str, components: List[dict]) -> str:
    for c in components:
        if c.get("id") == node_id:
            return c.get("type", "Unknown")
    return "Unknown"

def gateway_label(node_id: str, components: List[dict]) -> str:
    t = node_type(node_id, components)
    t_lower = t.lower()
    if "exclusive" in t_lower:
        return "ExclusiveGateway"
    if "inclusive" in t_lower:
        return "InclusiveGateway"
    if "parallel" in t_lower:
        return "ParallelGateway"
    if "gateway" in t_lower:
        return "Gateway"
    return t  # Atomic / CPPS / Unknown

# opzionale: può essere sostituito runtime dal main (lookup su cpps_collection)
def resolve_cpps_name_by_id(group_id: str) -> Optional[str]:
    return None

def format_node(node_id: str, components: List[dict]) -> str:
    t = node_type(node_id, components).lower()
    if t == "atomic":
        return node_id
    if "gateway" in t:
        return gateway_label(node_id, components)
    if t == "cpps":
        name = resolve_cpps_name_by_id(node_id)
        return f"CPPS({name or node_id})"
    return f"{t.upper()}({node_id})"

# ==================== Logica grafo ====================

def build_degrees(workflow: Dict[str, List[str]]) -> Tuple[Dict[str, int], Dict[str, int]]:
    out_deg = {s: len(tgts) for s, tgts in workflow.items()}
    in_deg = defaultdict(int)
    for s, tgts in workflow.items():
        for t in tgts:
            in_deg[t] += 1
        in_deg.setdefault(s, in_deg.get(s, 0))
    return out_deg, dict(in_deg)

def find_starts(workflow: Dict[str, List[str]]) -> List[str]:
    targets = set(t for tgts in workflow.values() for t in tgts)
    sources = set(workflow.keys())
    starts = [s for s in sources if s not in targets]
    return starts or sorted(list(sources))

def next_of(node_id: str, workflow: Dict[str, List[str]]) -> List[str]:
    return workflow.get(node_id, [])

# ==================== Rendering compatto (no duplicati) ====================

def render_branch_until_join(start: str,
                             workflow: Dict[str, List[str]],
                             components: List[dict],
                             in_deg: Dict[str, int],
                             out_deg: Dict[str, int],
                             seen: Set[str]) -> Tuple[str, Optional[str]]:
    expr_parts = []
    current = start
    local_seen = set()
    first = True

    while True:
        if current in local_seen or current in seen:
            expr_parts.append(f"[loop:{current}]")
            return " -> ".join(expr_parts), None
        local_seen.add(current)

        outs = next_of(current, workflow)
        expr_parts.append(format_node(current, components))

        # split interno al branch
        if out_deg.get(current, 0) > 1 and not first:
            expr_parts[-1] = gateway_label(current, components)
            split_str = render_split(current, workflow, components, in_deg, out_deg, seen | local_seen)
            expr_parts.append(split_str)
            return " -> ".join(expr_parts), None

        if not outs:
            return " -> ".join(expr_parts), None

        nxt = outs[0]
        if in_deg.get(nxt, 0) > 1:
            return " -> ".join(expr_parts), nxt

        expr_parts.append("->")
        current = nxt
        first = False

def find_nearest_common_convergence(starts: List[str],
                                    workflow: Dict[str, List[str]]) -> Optional[str]:
    """
    Dato un elenco di nodi di partenza (le uscite di uno split),
    trova il primo nodo raggiungibile da *tutti* (con distanza minima complessiva).
    Ritorna None se non esiste un nodo comune.
    """
    # BFS da ciascun start per calcolare distanze minime
    dist_maps = []
    for s in starts:
        dist = {s: 0}
        q = [s]
        i = 0
        while i < len(q):
            u = q[i]; i += 1
            for v in workflow.get(u, []):
                if v not in dist:
                    dist[v] = dist[u] + 1
                    q.append(v)
        dist_maps.append(dist)

    # intersezione dei nodi raggiungibili
    common = set(dist_maps[0].keys())
    for d in dist_maps[1:]:
        common &= set(d.keys())

    if not common:
        return None

    # scegli il nodo "più vicino" in media (o con max distanza minimale)
    best = None
    best_score = None
    for n in common:
        # evitiamo di restituire lo stesso start se presente in tutti (non è vera convergenza)
        if n in starts and len(starts) > 1:
            continue
        dists = [d[n] for d in dist_maps]
        score = (max(dists), sum(dists))  # ordina per max, poi per somma
        if best is None or score < best_score:
            best = n
            best_score = score
    return best

def render_split(node: str,
                 workflow: Dict[str, List[str]],
                 components: List[dict],
                 in_deg: Dict[str, int],
                 out_deg: Dict[str, int],
                 seen: Set[str]) -> str:
    outs = next_of(node, workflow)
    branches = []
    branch_joins = []

    for t in outs:
        branch_str, join_node = render_branch_until_join(t, workflow, components, in_deg, out_deg, seen)
        branches.append(branch_str)
        branch_joins.append(join_node)

    base = f"{gateway_label(node, components)}(" + ", ".join(branches) + ")"

    # Caso 1: join immediato uguale per tutti
    join_set = {j for j in branch_joins if j is not None}
    if len(join_set) == 1:
        join = join_set.pop()
        continuation = render_linear_from(join, workflow, components, in_deg, out_deg, seen | set(outs))
        return base + " -> " + continuation

    # Caso 2: nessun join immediato — cerca la convergenza più vicina nel grafo
    conv = find_nearest_common_convergence(outs, workflow)
    if conv:
        continuation = render_linear_from(conv, workflow, components, in_deg, out_deg, seen | set(outs))
        return base + " -> " + continuation

    # Nessuna convergenza comune (grafo davvero divergente)
    return base

def render_linear_from(node: str,
                       workflow: Dict[str, List[str]],
                       components: List[dict],
                       in_deg: Dict[str, int],
                       out_deg: Dict[str, int],
                       global_seen: Set[str]) -> str:
    parts = []
    current = node
    local_seen = set()
    first_print = True

    while True:
        if current in local_seen or current in global_seen:
            parts.append(f"[loop:{current}]")
            break
        local_seen.add(current)

        if first_print:
            parts.append(format_node(current, components))
            first_print = False

        outs = next_of(current, workflow)
        deg_out = out_deg.get(current, 0)

        if deg_out == 0:
            break

        if deg_out > 1:
            branch_expr = render_split(current, workflow, components, in_deg, out_deg, global_seen | local_seen)
            parts[-1] = branch_expr  # evita "Gateway Gateway(...)"
            break

        nxt = outs[0]
        parts.append(" -> " + format_node(nxt, components))
        current = nxt

    return "".join(parts)

def render_workflow_cppn(cppn_doc: dict) -> str:
    components = cppn_doc.get("components", [])
    workflow = cppn_doc.get("workflow", {})
    if not workflow:
        return "(workflow vuoto)"

    out_deg, in_deg = build_degrees(workflow)
    starts = find_starts(workflow)

    rendered = []
    seen_global: Set[str] = set()

    for s in starts:
        rendered.append(render_linear_from(s, workflow, components, in_deg, out_deg, seen_global))
        seen_global.add(s)

    return " | ".join(filter(None, rendered))

# ==================== Main ====================

# Import collections dal tuo handler del progetto (stessa cartella 'utilities')
from utilities.mongodb_handler import cppn_collection, cpps_collection

if __name__ == "__main__":
    # abilita la risoluzione del nome dei CPPS
    def _resolve_cpps_name_from_db(group_id: str) -> Optional[str]:
        doc = cpps_collection.find_one({"group_id": group_id}, {"name": 1})
        return doc.get("name") if doc else None

    # inietto il resolver nel namespace del modulo
    globals()["resolve_cpps_name_by_id"] = _resolve_cpps_name_from_db

    count = 0
    cursor = cppn_collection.find(
        {"group_type": "CPPN"},
        {"group_id": 1, "name": 1, "actors": 1, "components": 1, "workflow": 1}
    ).sort("group_id", 1)

    print("=== CPPN workflow graphs ===")
    for doc in cursor:
        try:
            group_id = doc.get("group_id", "?")
            name = doc.get("name", "(no name)")
            graph_str = render_workflow_cppn(doc)
            print(f"\n[{group_id}] {name}\n  {graph_str}\n")
            count += 1
        except Exception as e:
            print(f"[{doc.get('group_id','?')}] ERRORE nel rendering: {type(e).__name__}: {e}")

    print(f"\nTotale CPPN processati: {count}")