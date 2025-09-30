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

    url = f"https://api.pubg.com/shards/{platform}/players"

    try:
        resp = requests.get(
            url,
            headers=PUBG_HEADERS,
            params={"filter[playerNames]": ",".join(players)},
            timeout=10
        )

        if resp.status_code == 429:
            return jsonify({"error": "Rate limit exceeded. Try fewer players or wait a bit."}), 429
        elif resp.status_code != 200:
            return jsonify({"error": f"PUBG API returned {resp.status_code}"}), resp.status_code

        data = resp.json().get("data", [])
        results = []
        clan_cache = {}

        for player_name in players:
            player_data = next((p for p in data if p["attributes"]["name"].lower() == player_name.lower()), None)
            if not player_data:
                results.append({"player": player_name, "banStatus": "Player not found"})
                continue

            attrs = player_data.get("attributes", {})
            ban_type = attrs.get("banType", "Unknown")
            mapping = {
                "Innocent": "Not banned",
                "TemporaryBan": "Temporarily banned",
                "PermanentBan": "Permanently banned",
            }

            # Default: no clan
            clan_name = None

            # Look for clan relationship
            rel = player_data.get("relationships", {}).get("clan", {}).get("data")
            if rel and isinstance(rel, dict):
                clan_id = rel.get("id")
                if clan_id:
                    # Check cache first
                    if clan_id in clan_cache:
                        clan_name = clan_cache[clan_id]
                    else:
                        # Fetch clan details
                        clan_url = f"https://api.pubg.com/shards/{platform}/clans/{clan_id}"
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

@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
