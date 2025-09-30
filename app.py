from flask import Flask, request, jsonify
import requests
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("PUBG_API_KEY")

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
        # ✅ Single batch request
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

        # Map by lowercase name for easy lookup
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

            # ✅ Still fetch detail per player for clanId
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
