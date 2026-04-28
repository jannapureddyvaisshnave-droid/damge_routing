# ─────────────────────────────────────────────────────────────
#  CargoPath — National Road Network Graph
#
#  NODES  : 10 major Indian city logistics hubs
#  EDGES  : (distance_km, roughness_score)
#
#  roughness scale:
#    1–2  : National Highway / Expressway (very smooth)
#    3–4  : NH / State highway (good)
#    5–6  : State road / mixed quality
#    7–8  : District / rural road (rough)
#    9–10 : Unpaved / village track (very rough)
#
#  Distances are approximate real road distances (km).
#  Roughness reflects actual road quality on that corridor.
# ─────────────────────────────────────────────────────────────

NODE_INFO = {
    "DEL": {"name": "Delhi",      "lat": 28.613,  "lon": 77.209},
    "MUM": {"name": "Mumbai",     "lat": 19.076,  "lon": 72.877},
    "BLR": {"name": "Bangalore",  "lat": 12.972,  "lon": 77.594},
    "HYD": {"name": "Hyderabad",  "lat": 17.385,  "lon": 78.487},
    "CHE": {"name": "Chennai",    "lat": 13.082,  "lon": 80.270},
    "KOL": {"name": "Kolkata",    "lat": 22.572,  "lon": 88.363},
    "VIZ": {"name": "Vizag",      "lat": 17.686,  "lon": 83.218},
    "AMD": {"name": "Ahmedabad",  "lat": 23.023,  "lon": 72.572},
    "PUN": {"name": "Pune",       "lat": 18.520,  "lon": 73.856},
    "LUC": {"name": "Lucknow",    "lat": 26.847,  "lon": 80.947},
}

# Adjacency: node → {neighbor: (distance_km, roughness)}
#
# Edge selection rationale:
#   DEL–LUC  : Agra Expressway + NH-27          → very smooth NH
#   DEL–AMD  : NH-48 via Jaipur                 → good NH, some patches
#   DEL–MUM  : NH-48 full stretch               → long NH, variable quality
#   LUC–KOL  : NH-19 via Varanasi/Dhanbad       → moderate NH
#   LUC–HYD  : NH-44 via Nagpur                 → decent NH
#   AMD–MUM  : NH-48 / Mumbai–Ahmedabad Expwy   → expressway quality
#   AMD–PUN  : NH-48 via Surat                  → good NH
#   MUM–PUN  : Mumbai–Pune Expressway           → smoothest corridor
#   MUM–HYD  : NH-65 via Solapur               → mixed NH/state road
#   PUN–HYD  : NH-65 via Solapur               → state + NH mix
#   PUN–BLR  : NH-48 via Kolhapur              → hilly, moderate roughness
#   HYD–BLR  : NH-44 via Kurnool              → good NH
#   HYD–CHE  : NH-65 via Nellore              → good NH
#   HYD–VIZ  : NH-16 via Vijayawada           → good NH
#   BLR–CHE  : NH-48 (Chennai Expressway)     → excellent
#   CHE–VIZ  : NH-16 coastal                  → good NH
#   KOL–VIZ  : NH-16 via Bhubaneswar          → long NH, some rough patches
#   KOL–LUC  : NH-19 / NH-27 mix             → moderate

GRAPH = {
    "DEL": {
        "LUC": (555,  2),   # Agra Expressway + NH-27 — very smooth
        "AMD": (950,  3),   # NH-48 via Jaipur — good NH
        "MUM": (1400, 3),   # NH-48 full — long but well-maintained
    },
    "LUC": {
        "DEL": (555,  2),
        "KOL": (980,  4),   # NH-19 via Varanasi — moderate NH
        "HYD": (1490, 4),   # NH-44 via Nagpur — decent NH
    },
    "AMD": {
        "DEL": (950,  3),
        "MUM": (530,  2),   # Mumbai–Ahmedabad Expressway — near highway quality
        "PUN": (670,  3),   # NH-48 via Surat — good
    },
    "MUM": {
        "DEL": (1400, 3),
        "AMD": (530,  2),
        "PUN": (150,  1),   # Mumbai–Pune Expressway — smoothest in India
        "HYD": (710,  4),   # NH-65 via Solapur — mix of NH and state
    },
    "PUN": {
        "MUM": (150,  1),
        "AMD": (670,  3),
        "HYD": (560,  4),   # NH-65 via Solapur — similar to MUM–HYD
        "BLR": (840,  5),   # NH-48 via Kolhapur — hilly stretches
    },
    "HYD": {
        "LUC": (1490, 4),
        "MUM": (710,  4),
        "PUN": (560,  4),
        "BLR": (570,  3),   # NH-44 via Kurnool — good NH
        "CHE": (630,  3),   # NH-65 via Nellore — good
        "VIZ": (625,  3),   # NH-16 via Vijayawada — good
    },
    "BLR": {
        "PUN": (840,  5),
        "HYD": (570,  3),
        "CHE": (345,  2),   # NH-48 Chennai Expressway — excellent
    },
    "CHE": {
        "BLR": (345,  2),
        "HYD": (630,  3),
        "VIZ": (790,  3),   # NH-16 coastal — good NH
    },
    "VIZ": {
        "HYD": (625,  3),
        "CHE": (790,  3),
        "KOL": (1070, 5),   # NH-16 via Bhubaneswar — long, some rough patches
    },
    "KOL": {
        "LUC": (980,  4),
        "VIZ": (1070, 5),
    },
}


def get_node_name(code: str) -> str:
    return NODE_INFO.get(code, {}).get("name", code)


def all_nodes() -> list:
    return sorted(NODE_INFO.keys())


def node_display_map() -> dict:
    """Returns {code: full_name} for all nodes."""
    return {k: v["name"] for k, v in NODE_INFO.items()}