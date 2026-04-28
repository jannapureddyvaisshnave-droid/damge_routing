# ─────────────────────────────────────────────────────────────
#  CargoPath — Cargo & Crop Data Registry
#  fragility : 1 (robust) → 10 (extremely fragile)
#  profit_per_km : estimated revenue in ₹ per km per unit
#  handling_cost : fixed extra cost per route due to care needed
# ─────────────────────────────────────────────────────────────

CARGO_DATA = {
    # ── Non-crop goods ──────────────────────────────────────
    "furniture": {
        "fragility": 4,
        "profit_per_km": 12,
        "handling_cost": 50,
        "category": "goods",
        "notes": "Bulky but moderately tolerant of road vibrations."
    },
    "electronics": {
        "fragility": 8,
        "profit_per_km": 35,
        "handling_cost": 120,
        "category": "goods",
        "notes": "Sensitive to shocks; requires cushioning and smooth roads."
    },
    "glassware": {
        "fragility": 9,
        "profit_per_km": 20,
        "handling_cost": 150,
        "category": "goods",
        "notes": "Extremely fragile; minimal bumps tolerated."
    },
    "textiles": {
        "fragility": 2,
        "profit_per_km": 8,
        "handling_cost": 20,
        "category": "goods",
        "notes": "Very robust; road quality barely matters."
    },
    "machinery": {
        "fragility": 3,
        "profit_per_km": 25,
        "handling_cost": 40,
        "category": "goods",
        "notes": "Heavy and sturdy; slight roughness acceptable."
    },
    "pharmaceuticals": {
        "fragility": 7,
        "profit_per_km": 50,
        "handling_cost": 100,
        "category": "goods",
        "notes": "Temperature + vibration sensitive."
    },

    # ── Crops ───────────────────────────────────────────────
    "tomato": {
        "fragility": 9,
        "profit_per_km": 18,
        "handling_cost": 130,
        "category": "crop",
        "notes": "Highly perishable; bruises easily on rough roads."
    },
    "potato": {
        "fragility": 3,
        "profit_per_km": 7,
        "handling_cost": 25,
        "category": "crop",
        "notes": "Dense and robust; handles moderate roughness well."
    },
    "onion": {
        "fragility": 4,
        "profit_per_km": 9,
        "handling_cost": 30,
        "category": "crop",
        "notes": "Moderate fragility; some bruising on very rough roads."
    },
    "mango": {
        "fragility": 8,
        "profit_per_km": 30,
        "handling_cost": 110,
        "category": "crop",
        "notes": "Soft skin bruises easily; smooth roads preferred."
    },
    "grapes": {
        "fragility": 10,
        "profit_per_km": 40,
        "handling_cost": 180,
        "category": "crop",
        "notes": "Extremely fragile clusters; require near-perfect roads."
    },
    "wheat": {
        "fragility": 1,
        "profit_per_km": 5,
        "handling_cost": 10,
        "category": "crop",
        "notes": "Grain cargo; completely indifferent to road roughness."
    },
    "rice": {
        "fragility": 2,
        "profit_per_km": 6,
        "handling_cost": 15,
        "category": "crop",
        "notes": "Packaged grain; very resilient."
    },
    "banana": {
        "fragility": 7,
        "profit_per_km": 22,
        "handling_cost": 90,
        "category": "crop",
        "notes": "Bruises on bumpy roads; moderate care needed."
    },
    "apple": {
        "fragility": 6,
        "profit_per_km": 28,
        "handling_cost": 80,
        "category": "crop",
        "notes": "Skin bruises; prefers smoother routes."
    },
    "cabbage": {
        "fragility": 3,
        "profit_per_km": 8,
        "handling_cost": 20,
        "category": "crop",
        "notes": "Leafy but compact; fairly tolerant."
    },
    "cauliflower": {
        "fragility": 5,
        "profit_per_km": 14,
        "handling_cost": 55,
        "category": "crop",
        "notes": "Head can break on sharp jolts."
    },
    "strawberry": {
        "fragility": 10,
        "profit_per_km": 45,
        "handling_cost": 200,
        "category": "crop",
        "notes": "Ultra-fragile; requires refrigerated, ultra-smooth transport."
    },
    "sugarcane": {
        "fragility": 2,
        "profit_per_km": 6,
        "handling_cost": 15,
        "category": "crop",
        "notes": "Fibrous stalks; very resilient to bumps."
    },
    "cotton": {
        "fragility": 1,
        "profit_per_km": 10,
        "handling_cost": 10,
        "category": "crop",
        "notes": "Baled cotton is practically indestructible in transit."
    },
}

# All crops (for follow-up prompting)
CROP_NAMES = sorted([k for k, v in CARGO_DATA.items() if v["category"] == "crop"])
GOODS_NAMES = sorted([k for k, v in CARGO_DATA.items() if v["category"] == "goods"])


def get_cargo(name: str):
    """Return cargo dict or None."""
    return CARGO_DATA.get(name.lower().strip())


def list_all():
    return {
        "crops": CROP_NAMES,
        "goods": GOODS_NAMES
    }