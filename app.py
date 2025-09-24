from flask import Flask, request, jsonify
import requests
import os
from flask_cors import CORS
from difflib import get_close_matches

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

API_KEY = os.environ.get("PUBG_API_KEY")

# Store recently searched players for suggestions
recent_players = []

@app.route("/check-ban")
def check_ban():
    player = request.args.get("player", "").strip()
    platform = request.args.get("platform", "steam")

    if not player:
        return jsonify({"error": "Missing player parameter"}), 400

    if player not in recent_players:
        recent_players.append(player)
        if len(recent_players) > 100:  # Limit memory
            recent_players.pop(0)

    url = f"https://api.pubg.com/shards/{platform}/players"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/vnd.api+json"
    }

    try:
        resp = requests.get(url, headers=headers, params={"filter[playerNames]": player}, timeout=10)
        if resp.status_code != 200:
            return jsonify({"error": f"PUBG API returned {resp.status_code}"}), resp.status_code

        data = resp.json().get("data", [])
        if not data:
            return jsonify({"banStatus": "Player not found"})

        ban_type = data[0]["attributes"].get("banType", "Unknown")
        mapping = {
            "Innocent": "Not banned",
            "TemporaryBan": "Temporarily banned",
            "PermanentBan": "Permanently banned",
        }
        return jsonify({"banStatus": mapping.get(ban_type, ban_type)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/suggest-players")
def suggest_players():
    query = request.args.get("q", "").lower().strip()
    if not query:
        return jsonify([])

    # Return fuzzy-matched player names from recent_players
    suggestions = get_close_matches(query, recent_players, n=10, cutoff=0.4)
    return jsonify(suggestions)

@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
