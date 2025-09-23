from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Store your PUBG API key in an environment variable on Render
API_KEY = os.environ.get("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiIwNjljYjk4MC03YTk2LTAxM2UtNTcyNi0zMjY4NzNhNDM3NzAiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNzU4NjIzMzMzLCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6Ii1jMDc4MzdkZS1jNDQ1LTQ0MzgtYTUyZi00Y2M4NTFmZjMwZjcifQ.0uttT5BKUMN609k9jLBA5hLSykKhtIrD7SQodAHOw1A")

@app.route("/check-ban")
def check_ban():
    player = request.args.get("player")
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
