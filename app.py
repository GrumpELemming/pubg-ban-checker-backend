from flask import Flask, request, jsonify
import requests
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

API_KEY = os.environ.get("PUBG_API_KEY")

@app.route("/check-ban")
def check_ban():
    players_param = request.args.get("player", "").strip()
    platform = request.args.get("platform", "steam")

    if not players_param:
        return jsonify({"error": "Missing player parameter"}), 400

    # Split and clean names
    players = [p.strip() for p in players_param.split(",") if p.strip()]
    if not players:
        return jsonify({"error": "No valid player names provided"}), 400

    url = f"https://api.pubg.com/shards/{platform}/players"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/vnd.api+json"
    }

    try:
        # Send all player names in a single request
        resp = requests.get(
            url,
            headers=headers,
            params={"filter[playerNames]": ",".join(players)},
            timeout=10
        )

        if resp.status_code == 429:
            return jsonify({"error": "Rate limit exceeded. Try fewer players or wait a bit."}), 429
        elif resp.status_code != 200:
            return jsonify({"error": f"PUBG API returned {resp.status_code}"}), resp.status_code

        data = resp.json().get("data", [])
        results = []

        # Map PUBG response to your format
        for player_name in players:
            player_data = next((p for p in data if p["attributes"]["name"].lower() == player_name.lower()), None)
            if not player_data:
                results.append({"player": player_name, "banStatus": "Player not found"})
                continue

            ban_type = player_data["attributes"].get("banType", "Unknown")
            mapping = {
                "Innocent": "Not banned",
                "TemporaryBan": "Temporarily banned",
                "PermanentBan": "Permanently banned",
            }
            results.append({"player": player_name, "banStatus": mapping.get(ban_type, ban_type)})

        return jsonify({"results": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
