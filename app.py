from flask import Flask, request, jsonify
import requests
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ======================================================
# PUBG API setup
# ======================================================
API_KEY = os.environ.get("PUBG_API_KEY") or "PUT-YOUR-API-KEY-HERE"

PUBG_HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/vnd.api+json"
}

# ======================================================
# Route 1: Ban-only checker (optimized for 10 names)
# ======================================================
@app.route("/check-ban")
def check_ban():
    players_param = request.args.get("player", "").strip()
    platform = request.args.get("platform", "steam")

    if not players_param:
        return jsonify({"error": "Missing player parameter"}), 400

    players = [p.strip() for p in players_param.split(",") if p.strip()]
    if not players:
        return jsonify({"error": "No valid player names provided"}), 400

    base_url = f"https://api.pubg.com/shards/{platform}"
    results = []

    try:
        resp = requests.get(
            f"{base_url}/players",
            headers=PUBG_HEADERS,
            params={"filter[playerNames]": ",".join(players)},
            timeout=10
        )

        if resp.status_code == 429:
            return jsonify({"error": "Rate limit exceeded"}), 429
        elif resp.status_code != 200:
            return jsonify({"error": f"PUBG API returned {resp.status_code}"}), resp.status_code

        player_list = resp.json().get("data", [])
        player_map = {p["attributes"]["name"].lower(): p for p in player_list}

        for player_name in players:
            entry = player_map.get(player_name.lower())
            if not entry:
                results.append({"player": player_name, "banStatus": "Player not found"})
                continue

            ban_type = entry["attributes"].get("banType", "Unknown")
            mapping = {
                "Innocent": "Not banned",
                "TemporaryBan": "Temporarily banned",
                "PermanentBan": "Permanently banned",
            }

            results.append({
                "player": player_name,
                "banStatus": mapping.get(ban_type, ban_type)
            })

        return jsonify({"results": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ======================================================
# Route 2: Ban + Clan checker (experimental, heavier)
# ======================================================
@app.route("/check-ban-clan")
def check_ban_clan():
    players_param = request.args.get("player", "").strip()
    platform = request.args.get("platform", "steam")

    if not players_param:
        return jsonify({"error": "Missing player parameter"}), 400

    players = [p.strip() for p in players_param.split(",") if p.strip()]
    if not players:
        return jsonify({"error": "No valid player names provided"}), 400

    base_url = f"https://api.pubg.com/shards/{platform}"
    results = []
    clan_cache = {}

    try:
        resp = requests.get(
            f"{base_url}/players",
            headers=PUBG_HEADERS,
            params={"filter[playerNames]": ",".join(players)},
            timeout=10
        )

        if resp.status_code == 429:
            return jsonify({"error": "Rate limit exceeded"}), 429
        elif resp.status_code != 200:
            return jsonify({"error": f"PUBG API returned {resp.status_code}"}), resp.status_code

        player_list = resp.json().get("data", [])

        for player_name in players:
            player_entry = next((p for p in player_list if p["attributes"]["name"].lower() == player_name.lower()), None)
            if not player_entry:
                results.append({"player": player_name, "banStatus": "Player not found", "clan": None})
                continue

            player_id = player_entry["id"]

            detail_url = f"{base_url}/players/{player_id}"
            detail_resp = requests.get(detail_url, headers=PUBG_HEADERS, timeout=10)
            if detail_resp.status_code != 200:
                results.append({"player": player_name, "banStatus": "Error fetching details", "clan": None})
                continue

            detail_data = detail_resp.json().get("data", {})
            attrs = detail_data.get("attributes", {})
            ban_type = attrs.get("banType", "Unknown")
            mapping = {
                "Innocent": "Not banned",
                "TemporaryBan": "Temporarily banned",
                "PermanentBan": "Permanently banned",
            }

            clan_name = None
            clan_id = attrs.get("clanId")
            if clan_id:
                if clan_id in clan_cache:
                    clan_name = clan_cache[clan_id]
                else:
                    clan_url = f"{base_url}/clans/{clan_id}"
                    clan_resp = requests.get(clan_url, headers=PUBG_HEADERS, timeout=10)
                    if clan_resp.status_code == 200:
                        clan_data = clan_resp.json().get("data", {})
                        clan_attrs = clan_data.get("attributes", {})
                        clan_name = clan_attrs.get("clanTag") or clan_attrs.get("clanName")
                        clan_cache[clan_id] = clan_name

            results.append({
                "player": player_name,
                "clan": clan_name,
                "banStatus": mapping.get(ban_type, ban_type)
            })

        return jsonify({"results": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ======================================================
# Health check
# ======================================================
@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})


# ======================================================
# Secret Resolver (hidden page + endpoints)
# ======================================================
@app.route("/resolver-secret")
def resolver_page():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>PUBG Secret Resolver</title></head>
    <body style="font-family:sans-serif; background:#111; color:#eee; text-align:center; padding:20px;">
        <h1>PUBG Secret Resolver</h1>

        <div>
            <h2>Resolve by Name</h2>
            <input id="name" placeholder="Enter current PUBG name">
            <button onclick="resolveName()">Get ID</button>
            <pre id="outName"></pre>
        </div>

        <div>
            <h2>Resolve by Account ID</h2>
            <input id="accid" placeholder="Enter account ID">
            <button onclick="resolveId()">Get Current Name</button>
            <pre id="outId"></pre>
        </div>

        <script>
        async function resolveName() {
          const n = document.getElementById("name").value;
          const res = await fetch('/api/resolve-by-name?name='+encodeURIComponent(n));
          document.getElementById("outName").textContent = JSON.stringify(await res.json(), null, 2);
        }
        async function resolveId() {
          const i = document.getElementById("accid").value;
          const res = await fetch('/api/resolve-by-id?id='+encodeURIComponent(i));
          document.getElementById("outId").textContent = JSON.stringify(await res.json(), null, 2);
        }
        </script>
    </body>
    </html>
    """

@app.route("/api/resolve-by-name")
def api_resolve_name():
    player_name = request.args.get("name", "").strip()
    if not player_name:
        return jsonify({"error": "Missing name"}), 400
    r = requests.get(
        "https://api.pubg.com/shards/steam/players",
        headers=PUBG_HEADERS,
        params={"filter[playerNames]": player_name},
        timeout=10
    )
    if r.status_code != 200:
        return jsonify({"error": f"PUBG API {r.status_code}"}), r.status_code
    data = r.json().get("data", [])
    if not data:
        return jsonify({"error": "Player not found"}), 404
    player = data[0]
    return jsonify({"accountId": player["id"], "currentName": player["attributes"]["name"]})

@app.route("/api/resolve-by-id")
def api_resolve_id():
    accid = request.args.get("id", "").strip()
    if not accid:
        return jsonify({"error": "Missing id"}), 400
    r = requests.get(
        f"https://api.pubg.com/shards/steam/players/{accid}",
        headers=PUBG_HEADERS,
        timeout=10
    )
    if r.status_code != 200:
        return jsonify({"error": f"PUBG API {r.status_code}"}), r.status_code
    player = r.json().get("data", {})
    if not player:
        return jsonify({"error": "Player not found"}), 404
    return jsonify({"accountId": player["id"], "currentName": player["attributes"]["name"]})


# ======================================================
# Main entry point
# ======================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
