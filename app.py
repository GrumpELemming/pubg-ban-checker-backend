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

    # Split by comma and strip spaces
    players = [p.strip() for p in players_param.split(",") if p.strip()]
    results = []

    url = f"https://api.pubg.com/shards/{platform}/players"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/vnd.api+json"
    }

    for player in players:
        try:
            resp = requests.get(url, headers=headers, params={"filter[playerNames]": player}, timeout=10)
            if resp.status_code != 200:
                results.append({"player": player, "banStatus": f"PUBG API returned {resp.status_code}"})
                continue

            data = resp.json().get("data", [])
            if not data:
                results.append({"player": player, "banStatus": "Player not found"})
                continue

            ban_type = data[0]["attributes"].get("banType", "Unknown")
            mapping = {
                "Innocent": "Not banned",
                "TemporaryBan": "Temporarily banned",
                "PermanentBan": "Permanently banned",
            }
            results.append({"player": player, "banStatus": mapping.get(ban_type, ban_type)})

        except Exception as e:
            results.append({"player": player, "banStatus": f"Error: {str(e)}"})

    return jsonify({"results": results})

@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
