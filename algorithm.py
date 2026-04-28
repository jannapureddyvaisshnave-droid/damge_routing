"""
algorithm.py — CargoPath Damage-Aware Dijkstra
================================================
Cost function:  edge_cost = distance + (roughness × fragility)
Returns:        best route + full analysis (distance, damage cost,
                profit, net value, per-segment breakdown).
"""
import heapq
from data.graph_data import GRAPH, NODE_INFO, get_node_name


# ──────────────────────────────────────────────────────────────────────────────
#  Core: Modified Dijkstra
# ──────────────────────────────────────────────────────────────────────────────

def damage_aware_dijkstra(start: str, end: str, fragility: int) -> dict:
    """
    Run damage-aware Dijkstra from start → end.

    Parameters
    ----------
    start, end  : node codes (e.g. "HYD", "WAR")
    fragility   : int 1–10 from cargo/crop data

    Returns
    -------
    dict with keys:
        found        bool
        path         list[str]   e.g. ["HYD", "SNG", "WAR"]
        total_cost   float       weighted Dijkstra cost
        total_distance_km float
        total_roughness_sum float
        segments     list[dict]  per-edge breakdown
        error        str | None
    """
    if start not in GRAPH:
        return _err(f"Start node '{start}' not found in graph.")
    if end not in GRAPH:
        return _err(f"End node '{end}' not found in graph.")
    if start == end:
        return _err("Start and destination are the same node.")

    # heap entry: (cumulative_cost, node, path_so_far, segments_so_far)
    queue = [(0.0, start, [start], [])]
    visited = set()

    while queue:
        cost, node, path, segments = heapq.heappop(queue)

        if node in visited:
            continue
        visited.add(node)

        if node == end:
            total_dist = sum(s["distance_km"] for s in segments)
            total_roughness = sum(s["roughness"] for s in segments)
            return {
                "found": True,
                "path": path,
                "total_cost": round(cost, 2),
                "total_distance_km": round(total_dist, 2),
                "total_roughness_sum": round(total_roughness, 2),
                "segments": segments,
                "error": None,
            }

        for neighbor, (distance, roughness) in GRAPH.get(node, {}).items():
            if neighbor in visited:
                continue
            edge_cost = distance + (roughness * fragility)
            seg = {
                "from": node,
                "from_name": get_node_name(node),
                "to": neighbor,
                "to_name": get_node_name(neighbor),
                "distance_km": distance,
                "roughness": roughness,
                "edge_cost": round(edge_cost, 2),
            }
            heapq.heappush(
                queue,
                (cost + edge_cost, neighbor, path + [neighbor], segments + [seg])
            )

    return _err(f"No path found between '{start}' and '{end}'.")


def _err(msg: str) -> dict:
    return {
        "found": False,
        "path": [],
        "total_cost": None,
        "total_distance_km": None,
        "total_roughness_sum": None,
        "segments": [],
        "error": msg,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Profit / Cost Analysis
# ──────────────────────────────────────────────────────────────────────────────

FUEL_COST_PER_KM = 8.0          # ₹ per km (diesel truck avg)
DRIVER_COST_PER_KM = 2.5        # ₹ per km labour
DAMAGE_LOSS_PER_ROUGHNESS_UNIT = 5.0  # ₹ lost per roughness × fragility unit


def compute_profit_analysis(route_result: dict, cargo: dict, units: int = 1) -> dict:
    """
    Compute profit/cost breakdown for a route.

    Parameters
    ----------
    route_result : output of damage_aware_dijkstra
    cargo        : dict from cargo_data.CARGO_DATA
    units        : number of cargo units being transported

    Returns
    -------
    dict with revenue, costs, net_profit, profit_per_km
    """
    if not route_result["found"]:
        return {"error": route_result["error"]}

    dist = route_result["total_distance_km"]
    roughness_sum = route_result["total_roughness_sum"]
    fragility = cargo["fragility"]

    revenue = cargo["profit_per_km"] * dist * units
    fuel_cost = FUEL_COST_PER_KM * dist
    driver_cost = DRIVER_COST_PER_KM * dist
    handling_cost = cargo["handling_cost"] * units
    damage_loss = DAMAGE_LOSS_PER_ROUGHNESS_UNIT * roughness_sum * fragility * units
    total_cost = fuel_cost + driver_cost + handling_cost + damage_loss

    net_profit = revenue - total_cost
    profit_per_km = net_profit / dist if dist > 0 else 0

    return {
        "units": units,
        "distance_km": round(dist, 2),
        "revenue_inr": round(revenue, 2),
        "fuel_cost_inr": round(fuel_cost, 2),
        "driver_cost_inr": round(driver_cost, 2),
        "handling_cost_inr": round(handling_cost, 2),
        "damage_loss_inr": round(damage_loss, 2),
        "total_cost_inr": round(total_cost, 2),
        "net_profit_inr": round(net_profit, 2),
        "profit_per_km": round(profit_per_km, 2),
        "profitable": net_profit > 0,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Alternative Route Comparison
# ──────────────────────────────────────────────────────────────────────────────

def find_top_routes(start: str, end: str, fragility: int, top_n: int = 3) -> list:
    """
    Find top N distinct routes using a modified k-shortest-paths approach.
    Uses edge exclusion to discover alternatives after the best path is found.
    Returns list of route dicts sorted by total_cost ascending.
    """
    routes = []

    # Primary best route
    best = damage_aware_dijkstra(start, end, fragility)
    if not best["found"]:
        return []
    routes.append(best)

    # Generate alternatives by temporarily removing one edge from best path at a time
    best_segments = best["segments"]
    seen_paths = {tuple(best["path"])}

    for i, seg in enumerate(best_segments):
        # Clone graph without this edge
        modified = _graph_without_edge(seg["from"], seg["to"])
        alt = _dijkstra_on_modified(modified, start, end, fragility)
        if alt["found"] and tuple(alt["path"]) not in seen_paths:
            routes.append(alt)
            seen_paths.add(tuple(alt["path"]))
        if len(routes) >= top_n:
            break

    routes.sort(key=lambda r: r["total_cost"])
    return routes[:top_n]


def _graph_without_edge(node_a: str, node_b: str) -> dict:
    """Return a copy of GRAPH with the edge a↔b removed."""
    modified = {}
    for node, neighbors in GRAPH.items():
        modified[node] = {}
        for nbr, val in neighbors.items():
            if (node == node_a and nbr == node_b) or (node == node_b and nbr == node_a):
                continue
            modified[node][nbr] = val
    return modified


def _dijkstra_on_modified(graph: dict, start: str, end: str, fragility: int) -> dict:
    """Run Dijkstra on an arbitrary graph dict (same structure as GRAPH)."""
    queue = [(0.0, start, [start], [])]
    visited = set()

    while queue:
        cost, node, path, segments = heapq.heappop(queue)
        if node in visited:
            continue
        visited.add(node)
        if node == end:
            total_dist = sum(s["distance_km"] for s in segments)
            total_roughness = sum(s["roughness"] for s in segments)
            return {
                "found": True,
                "path": path,
                "total_cost": round(cost, 2),
                "total_distance_km": round(total_dist, 2),
                "total_roughness_sum": round(total_roughness, 2),
                "segments": segments,
                "error": None,
            }
        for neighbor, (distance, roughness) in graph.get(node, {}).items():
            if neighbor in visited:
                continue
            edge_cost = distance + (roughness * fragility)
            seg = {
                "from": node,
                "from_name": get_node_name(node),
                "to": neighbor,
                "to_name": get_node_name(neighbor),
                "distance_km": distance,
                "roughness": roughness,
                "edge_cost": round(edge_cost, 2),
            }
            heapq.heappush(
                queue,
                (cost + edge_cost, neighbor, path + [neighbor], segments + [seg])
            )

    return _err(f"No path found between '{start}' and '{end}' in modified graph.")