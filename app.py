from flask import Flask, request, jsonify
import requests
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

API_KEY = os.environ.get("PUBG_API_KEY")

@app.route("/check-ban")
def check_ban():
    player = request.args.get("player", "").strip()
    platform = request.args.get("platform", "steam")

    if not player:
        return jsonify({"error": "Missing player parameter"}), 400

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

@app.route("/suggest-names")
def suggest_names():
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify({"suggestions": []})

    url = f"https://api.pubg.com/shards/steam/players"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/vnd.api+json"
    }

    try:
        resp = requests.get(url, headers=headers, params={"filter[playerNames]": query}, timeout=10)
        if resp.status_code != 200:
            return jsonify({"suggestions": []})
        data = resp.json().get("data", [])
        suggestions = [player["attributes"]["name"] for player in data]
        return jsonify({"suggestions": suggestions[:10]})
    except Exception:
        return jsonify({"suggestions": []})

@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # <-- Use Render's dynamic port
    app.run(host="0.0.0.0", port=port)
