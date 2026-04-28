"""
app.py — CargoPath Flask Application
=====================================
PAGE ROUTES:
  GET  /                    → index.html
  GET  /route-planner       → route.html
  GET  /history             → history.html
  GET  /about               → about.html
  GET  /contact             → contact.html
  GET  /profile             → profile.html   (sign in / sign up landing)
  GET  /signin              → signin.html
  GET  /signup              → signup.html

API ROUTES:
  GET    /api/cargo
  POST   /api/route                 ← saves to DB, links to user if logged in
  GET    /api/route/alternatives
  GET    /api/history               ← all routes (global)
  GET    /api/history/stats         ← global stats
  DELETE /api/history/<id>
  GET    /api/history/mine          ← routes for logged-in user ★ NEW
  GET    /api/history/mine/stats    ← stats for logged-in user  ★ NEW
  DELETE /api/history/mine/<id>     ← delete own route          ★ NEW
  POST   /api/auth/register
  POST   /api/auth/login
  POST   /api/auth/logout           ★ NEW
  GET    /api/auth/me               ← current session user      ★ NEW
  GET    /health
"""

import os
from flask import Flask, request, jsonify, render_template, session
import google.generativeai as genai

from data.cargo_data import CARGO_DATA, CROP_NAMES, GOODS_NAMES, get_cargo
from data.graph_data import node_display_map, all_nodes, get_node_name
from algorithm import damage_aware_dijkstra, compute_profit_analysis, find_top_routes
from database import (
    init_db, save_route,
    get_history, get_route_by_id, delete_route, get_stats,
    get_user_history, get_user_stats, delete_user_route, get_user_by_id,
    register_user, login_user,
)

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)
app.secret_key = os.environ.get("SECRET_KEY", "cargopath-dev-secret-change-in-prod")


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

#  GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAa9wueZb4ino9M3fLgbbN1blP0AwdfIh8")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# Create DB tables on startup
init_db()


# ── Helpers ───────────────────────────────────────────────────

def _error(message, code=400, **extra):
    return jsonify({"success": False, "error": message, **extra}), code


def _build_gemini_prompt(cargo_name, cargo, route, profit):
    path_str = " -> ".join(f"{get_node_name(n)} ({n})" for n in route["path"])
    seg_lines = "\n".join(
        f"  * {s['from_name']} -> {s['to_name']}: {s['distance_km']} km, roughness {s['roughness']}/10"
        for s in route["segments"]
    )
    return (
        f"You are a logistics expert for CargoPath.\n"
        f"Cargo: {cargo_name.title()}, Fragility {cargo['fragility']}/10. Route: {path_str}.\n"
        f"Distance: {route['total_distance_km']} km. Net Profit: Rs.{profit['net_profit_inr']}.\n"
        f"Segments:\n{seg_lines}\n"
        f"Write 3 concise paragraphs (no bullets, under 180 words):\n"
        f"1. Why this route suits this cargo's fragility.\n"
        f"2. Most critical/risky segments.\n"
        f"3. Driver recommendations to minimise damage."
    )


def _gemini_explain(prompt):
    try:
        return gemini_model.generate_content(prompt).text.strip()
    except Exception as e:
        return f"[AI explanation unavailable: {e}]"


# ── Page routes ───────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/route-planner", methods=["GET"])
def route_planner_page():
    return render_template("route.html")

@app.route("/history", methods=["GET"])
def history_page():
    return render_template("history.html")

@app.route("/about", methods=["GET"])
def about_page():
    return render_template("about.html")

@app.route("/contact", methods=["GET"])
def contact_page():
    return render_template("contact.html")

@app.route("/profile", methods=["GET"])
def profile_page():
    return render_template("profile.html")

@app.route("/signin", methods=["GET"])
def signin_page():
    return render_template("signin.html")

@app.route("/signup", methods=["GET"])
def signup_page():
    return render_template("signup.html")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "app": "CargoPath"})


# ── Auth API ──────────────────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
def api_register():
    body = request.get_json(silent=True)
    if not body:
        return _error("Request body must be valid JSON.")
    full_name = (body.get("full_name") or "").strip()
    email     = (body.get("email") or "").strip()
    password  = (body.get("password") or "")
    if not full_name: return _error("Full name is required.")
    if not email:     return _error("Email address is required.")
    if not password:  return _error("Password is required.")
    if len(password) < 6: return _error("Password must be at least 6 characters.")
    result = register_user(full_name, email, password)
    if result["success"]:
        # Auto-login after register
        session["user_id"]    = result["user"]["id"]
        session["user_name"]  = result["user"]["full_name"]
        session["user_email"] = result["user"]["email"]
        return jsonify({"success": True, "user": result["user"]})
    return _error(result["error"])


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    body = request.get_json(silent=True)
    if not body:
        return _error("Request body must be valid JSON.")
    email    = (body.get("email") or "").strip()
    password = (body.get("password") or "")
    if not email:    return _error("Email address is required.")
    if not password: return _error("Password is required.")
    result = login_user(email, password)
    if result["success"]:
        session["user_id"]    = result["user"]["id"]
        session["user_name"]  = result["user"]["full_name"]
        session["user_email"] = result["user"]["email"]
        return jsonify({"success": True, "user": result["user"]})
    return _error(result["error"], 401)


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/auth/me", methods=["GET"])
def api_me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"logged_in": False})
    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "user": user})


# ── Per-user history API ──────────────────────────────────────

@app.route("/api/history/mine", methods=["GET"])
def api_user_history():
    user_id = session.get("user_id")
    if not user_id:
        return _error("Not logged in.", 401)
    limit  = min(int(request.args.get("limit",  50)), 200)
    offset = max(int(request.args.get("offset",  0)),  0)
    rows   = get_user_history(user_id, limit=limit, offset=offset)
    return jsonify({"success": True, "count": len(rows), "routes": rows})


@app.route("/api/history/mine/stats", methods=["GET"])
def api_user_stats():
    user_id = session.get("user_id")
    if not user_id:
        return _error("Not logged in.", 401)
    return jsonify({"success": True, "stats": get_user_stats(user_id)})


@app.route("/api/history/mine/<int:route_id>", methods=["DELETE"])
def api_user_delete_route(route_id):
    user_id = session.get("user_id")
    if not user_id:
        return _error("Not logged in.", 401)
    if not delete_user_route(route_id, user_id):
        return _error("Route not found or does not belong to you.", 404)
    return jsonify({"success": True, "deleted_id": route_id})


# ── Cargo API ─────────────────────────────────────────────────

@app.route("/api/cargo", methods=["GET"])
def list_cargo():
    return jsonify({
        "crops": {n: {"fragility": CARGO_DATA[n]["fragility"], "profit_per_km": CARGO_DATA[n]["profit_per_km"], "notes": CARGO_DATA[n]["notes"]} for n in CROP_NAMES},
        "goods": {n: {"fragility": CARGO_DATA[n]["fragility"], "profit_per_km": CARGO_DATA[n]["profit_per_km"], "notes": CARGO_DATA[n]["notes"]} for n in GOODS_NAMES},
    })


# ── Route API — FIXED: now saves to database ─────────────────

@app.route("/api/route", methods=["POST"])
def get_route():
    body = request.get_json(silent=True)
    if not body:
        return _error("Request body must be valid JSON.")

    start = (body.get("start") or "").strip().upper()
    dest  = (body.get("destination") or "").strip().upper()
    good  = (body.get("good") or "").strip().lower()

    if not start: return _error("Missing field: 'start'.")
    if not dest:  return _error("Missing field: 'destination'.")
    if not good:  return _error("Missing field: 'good'.")

    valid_nodes = all_nodes()
    if start not in valid_nodes:
        return _error(f"Unknown node '{start}'.", 400, available_nodes=node_display_map())
    if dest not in valid_nodes:
        return _error(f"Unknown node '{dest}'.",  400, available_nodes=node_display_map())

    if good == "crop":
        crop_name = (body.get("crop") or "").strip().lower()
        if not crop_name:
            return jsonify({
                "success": False, "follow_up_required": True,
                "question": "Specify which crop.",
                "available_crops": {n: {"fragility": CARGO_DATA[n]["fragility"], "notes": CARGO_DATA[n]["notes"]} for n in CROP_NAMES}
            }), 422
        cargo = get_cargo(crop_name)
        if cargo is None:
            return _error(f"Unknown crop '{crop_name}'.", 400, available_crops=CROP_NAMES)
        cargo_name = crop_name
    else:
        cargo = get_cargo(good)
        if cargo is None:
            return _error(f"Unknown cargo '{good}'.", 400, available_crops=CROP_NAMES, available_goods=GOODS_NAMES)
        cargo_name = good

    units     = max(1, int(body.get("units", 1)))
    fragility = cargo["fragility"]
    route     = damage_aware_dijkstra(start, dest, fragility)

    if not route["found"]:
        return _error(route["error"], 404)

    profit         = compute_profit_analysis(route, cargo, units)
    ai_explanation = _gemini_explain(_build_gemini_prompt(cargo_name, cargo, route, profit))

    # ── SAVE TO DATABASE ─────────────────────────────────────
    history_id = save_route(
        start_code=start,
        start_name=get_node_name(start),
        dest_code=dest,
        dest_name=get_node_name(dest),
        cargo_name=cargo_name,
        cargo_category=cargo["category"],
        fragility=fragility,
        units=units,
        route=route,
        profit=profit,
        ai_explanation=ai_explanation,
        user_id=session.get("user_id"),   # None if not logged in
    )

    return jsonify({
        "success":    True,
        "history_id": history_id,
        "cargo": {
            "name":      cargo_name,
            "category":  cargo["category"],
            "fragility": fragility,
            "notes":     cargo["notes"],
            "units":     units,
        },
        "route": {
            "path":               [{"code": n, "name": get_node_name(n)} for n in route["path"]],
            "path_codes":         route["path"],
            "total_distance_km":  route["total_distance_km"],
            "total_weighted_cost": route["total_cost"],
            "total_roughness_sum": route["total_roughness_sum"],
            "segments":           route["segments"],
        },
        "financial_analysis": profit,
        "ai_explanation":     ai_explanation,
    })


@app.route("/api/route/alternatives", methods=["GET"])
def get_alternatives():
    start  = (request.args.get("start") or "").strip().upper()
    dest   = (request.args.get("destination") or "").strip().upper()
    good   = (request.args.get("good") or "").strip().lower()
    crop_q = (request.args.get("crop") or "").strip().lower()

    if not start or not dest or not good:
        return _error("Params 'start', 'destination', 'good' required.")

    cargo_key = crop_q if good == "crop" else good
    cargo = get_cargo(cargo_key)
    if cargo is None:
        return _error(f"Unknown cargo '{cargo_key}'.")

    units      = int(request.args.get("units", 1))
    top_routes = find_top_routes(start, dest, cargo["fragility"], top_n=3)
    if not top_routes:
        return _error("No routes found.", 404)

    result = []
    for i, r in enumerate(top_routes, 1):
        p = compute_profit_analysis(r, cargo, units)
        result.append({
            "rank":               i,
            "path_codes":         r["path"],
            "path_names":         [get_node_name(n) for n in r["path"]],
            "total_distance_km":  r["total_distance_km"],
            "total_weighted_cost": r["total_cost"],
            "net_profit_inr":     p.get("net_profit_inr"),
            "profitable":         p.get("profitable"),
            "segments":           r["segments"],
        })
    return jsonify({"success": True, "cargo": cargo_key, "fragility": cargo["fragility"], "alternatives": result})


# ── History API — reads from database ────────────────────────

@app.route("/api/history", methods=["GET"])
def api_history():
    limit  = min(int(request.args.get("limit",  50)), 200)
    offset = max(int(request.args.get("offset",  0)),  0)
    rows   = get_history(limit=limit, offset=offset)
    return jsonify({"success": True, "count": len(rows), "routes": rows})


@app.route("/api/history/stats", methods=["GET"])
def api_history_stats():
    return jsonify({"success": True, "stats": get_stats()})


@app.route("/api/history/<int:route_id>", methods=["GET"])
def api_history_detail(route_id):
    row = get_route_by_id(route_id)
    if not row:
        return _error("Not found.", 404)
    return jsonify({"success": True, "route": row})


@app.route("/api/history/<int:route_id>", methods=["DELETE"])
def api_history_delete(route_id):
    if not delete_route(route_id):
        return _error("Not found.", 404)
    return jsonify({"success": True, "deleted_id": route_id})


if __name__ == "__main__":
    app.run(host ="0.0.0.0", port=5000)