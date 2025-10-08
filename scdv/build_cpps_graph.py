from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set

# ---- helpers su tipi/etichette ------------------------------------------------

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
    return t  # non-gateway: Atomic / Unknown

def format_node(node_id: str, components: List[dict]) -> str:
    t = node_type(node_id, components)
    if t.lower() == "atomic":
        return node_id
    # per gateway e altri, torna l'etichetta (senza id) quando è "funzione"
    if "gateway" in t.lower():
        return gateway_label(node_id, components)
    return f"{t}({node_id})"

# ---- logica grafo -------------------------------------------------------------

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
    # start = sorgenti che non sono mai target; se vuoto, ripiega su min(sources) stabile
    starts = [s for s in sources if s not in targets]
    return starts or sorted(list(sources))

def is_gateway(node_id: str, components: List[dict]) -> bool:
    return "gateway" in node_type(node_id, components).lower()

def next_of(node_id: str, workflow: Dict[str, List[str]]) -> List[str]:
    return workflow.get(node_id, [])

# ---- rendering ---------------------------------------------------------------

def render_linear_from(node: str,
                       workflow: Dict[str, List[str]],
                       components: List[dict],
                       in_deg: Dict[str, int],
                       out_deg: Dict[str, int],
                       global_seen: Set[str]) -> str:
    """
    Rende una sequenza lineare finché:
      - non incontra uno split (out>1)
      - non entra in un nodo di join (in>1)
      - non rientra in un ciclo
    Evita di stampare due volte lo stesso nodo.
    """
    parts = []
    current = node
    local_seen = set()
    first_print = True  # stampiamo il primo nodo una sola volta

    while True:
        if current in local_seen or current in global_seen:
            parts.append(f"[loop:{current}]")
            break
        local_seen.add(current)

        # stampa il nodo corrente una sola volta all'inizio
        if first_print:
            parts.append(format_node(current, components))
            first_print = False

        outs = next_of(current, workflow)
        deg_out = out_deg.get(current, 0)

        # fine: nessuna uscita
        if deg_out == 0:
            break

        # split (gateway con più uscite)
        if deg_out > 1:
            # al posto di etichetta+append, sostituiamo l'ultimo pezzo con l'intero split
            branch_expr = render_split(current, workflow, components, in_deg, out_deg, global_seen | local_seen)
            parts[-1] = branch_expr  # <- così evitiamo "ParallelGateway ParallelGateway(...)"
            break

        # passo lineare
        nxt = outs[0]
        parts.append(" -> " + format_node(nxt, components))
        current = nxt
        # al prossimo giro NON ristampiamo 'current' (già stampato come 'nxt' qui sopra)

    return "".join(parts)

def render_branch_until_join(start: str,
                             workflow: Dict[str, List[str]],
                             components: List[dict],
                             in_deg: Dict[str, int],
                             out_deg: Dict[str, int],
                             seen: Set[str]) -> Tuple[str, Optional[str]]:
    """
    Percorre il branch da 'start' finché:
      - trova un nodo join (in>1) *successivo* allo start
      - finisce il cammino
      - trova uno split (in quel caso il rendering del sotto-split viene incluso nella branch expression)
    Ritorna: (branch_expr, join_node_opzionale)
    """
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

        # se split dentro il branch: rappresentalo come funzione e stop branch qui
        if out_deg.get(current, 0) > 1 and not first:
            expr_parts[-1] = gateway_label(current, components)
            split_str = render_split(current, workflow, components, in_deg, out_deg, seen | local_seen)
            expr_parts.append(split_str)
            return " -> ".join(expr_parts), None

        # fine cammino
        if not outs:
            return " -> ".join(expr_parts), None

        nxt = outs[0]  # nel branch, seguiamo il primo (se c’è uno split sopra, l’abbiamo già gestito)
        # se il prossimo è un join (in>1), fermati e restituisci il join
        if in_deg.get(nxt, 0) > 1:
            return " -> ".join(expr_parts), nxt

        # altrimenti continua
        expr_parts.append("->")
        current = nxt
        first = False

def render_split(node: str,
                 workflow: Dict[str, List[str]],
                 components: List[dict],
                 in_deg: Dict[str, int],
                 out_deg: Dict[str, int],
                 seen: Set[str]) -> str:
    """
    Rende 'GatewayType(branch1, branch2, ...)[ -> continuation]'
    Se tutte le branch convergono allo stesso join, aggiunge '-> JOIN -> ...'
    """
    outs = next_of(node, workflow)
    branches = []
    branch_joins = []

    for t in outs:
        branch_str, join_node = render_branch_until_join(t, workflow, components, in_deg, out_deg, seen)
        branches.append(branch_str)
        branch_joins.append(join_node)

    # se tutte le branch convergono nello stesso join, continua dopo il join
    join_set = {j for j in branch_joins if j is not None}
    base = f"{gateway_label(node, components)}(" + ", ".join(branches) + ")"
    if len(join_set) == 1:
        join = join_set.pop()
        continuation = render_linear_from(join, workflow, components, in_deg, out_deg, seen | set(outs))
        return base + " -> " + continuation
    return base

def render_workflow(cpps_doc: dict) -> str:
    """
    Accetta il documento CPPS e restituisce una sola stringa compatta del grafo.
    Rende solo i cammini a partire dagli start reali (in-degree == 0).
    Niente giro extra sui 'remaining' per evitare duplicati.
    """
    components = cpps_doc.get("components", [])
    workflow = cpps_doc.get("workflow", {})
    if not workflow:
        return "(workflow vuoto)"

    out_deg, in_deg = build_degrees(workflow)
    starts = find_starts(workflow)

    rendered = []
    seen_global: Set[str] = set()

    for s in starts:
        rendered.append(render_linear_from(s, workflow, components, in_deg, out_deg, seen_global))
        # segna come visti almeno gli start (evita rerendering se più start coincidono in DAG strani)
        seen_global.add(s)

    return " | ".join(filter(None, rendered))

from utilities.mongodb_handler import cpps_collection  # già usata altrove nel tuo progetto

if __name__ == "__main__":
    

    count = 0
    cursor = cpps_collection.find(
        {"group_type": "CPPS"},
        {"group_id": 1, "name": 1, "components": 1, "workflow": 1}
    ).sort("group_id", 1)

    print("=== CPPS workflow graphs ===")
    for doc in cursor:
        try:
            group_id = doc.get("group_id", "?")
            name = doc.get("name", "(no name)")
            graph_str = render_workflow(doc)
            print(f"\n\n[{group_id}] {name}\n  {graph_str}\n\n")
            count += 1
        except Exception as e:
            print(f"[{doc.get('group_id','?')}] Rendering error: {type(e).__name__}: {e}\n")

    print(f"Totale CPPS processati: {count}")
