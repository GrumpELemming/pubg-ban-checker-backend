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
    clan_cache = {}

    try:
        # Step 1: Lookup all players by name
        resp = requests.get(
            f"{base_url}/players",
            headers=PUBG_HEADERS,
            params={"filter[playerNames]": ",".join(players)},
            timeout=10
        )

        if resp.status_code == 429:
            return jsonify({"error": "Rate limit exceeded. Try fewer players or wait a bit."}), 429
        elif resp.status_code != 200:
            return jsonify({"error": f"PUBG API returned {resp.status_code}"}), resp.status_code

        player_list = resp.json().get("data", [])

        for player_name in players:
            player_entry = next((p for p in player_list if p["attributes"]["name"].lower() == player_name.lower()), None)
            if not player_entry:
                results.append({"player": player_name, "banStatus": "Player not found", "clan": None})
                continue

            player_id = player_entry["id"]

            # Step 2: Get detailed player info
            detail_resp = requests.get(f"{base_url}/players/{player_id}", headers=PUBG_HEADERS, timeout=10)
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

            # Step 3: Resolve clan info if present
            clan_name = None
            clan_rel = detail_data.get("relationships", {}).get("clan", {}).get("data")
            if clan_rel and isinstance(clan_rel, dict):
                clan_id = clan_rel.get("id")
                if clan_id:
                    if clan_id in clan_cache:
                        clan_name = clan_cache[clan_id]
                    else:
                        clan_resp = requests.get(f"{base_url}/clans/{clan_id}", headers=PUBG_HEADERS, timeout=10)
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


@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
