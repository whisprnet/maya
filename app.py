from flask import Flask, request, jsonify
from flask_socketio import SocketIO
import requests
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

SLACK_BOT = os.getenv("SLACK_BOT_TOKEN")
CHANNEL_ID = os.getenv("SLACK_CHANNEL")

# 🔧 Get username from Slack API if userId is present (for human users)
def get_username_from_user_id(user_id):
    if not user_id:
        return "Unknown"
    try:
        url = "https://slack.com/api/users.info"
        headers = {
            "Authorization": f"Bearer {SLACK_BOT}"
        }
        params = {
            "user": user_id
        }
        res = requests.get(url, headers=headers, params=params).json()
        return res.get("user", {}).get("real_name", "Unknown")
    except Exception as e:
        print(f"Error fetching username for {user_id}: {e}")
        return "Unknown"

# 🟢 Route to fetch Slack messages
@app.route("/slack-messages", methods=["GET"])
def get_slack_messages():
    try:
        url = "https://slack.com/api/conversations.history"
        headers = {
            "Authorization": f"Bearer {SLACK_BOT}"
        }
        params = {
            "channel": CHANNEL_ID
        }
        response = requests.get(url, headers=headers, params=params).json()

        raw_messages = response.get("messages", [])
        user_messages = [msg for msg in raw_messages if "subtype" not in msg]

        messages = []
        for msg in user_messages:
            user_id = msg.get("user") or msg.get("bot_profile", {}).get("user_id")
            
            if "bot_profile" in msg and "name" in msg["bot_profile"]:
                username = msg["bot_profile"]["name"]
            else:
                username = get_username_from_user_id(user_id)

            messages.append({
                "user_id": user_id,
                "username": username,
                "text": msg.get("text", ""),
                "app_id": msg.get("app_id")
            })

        print(messages)
        socketio.emit("slack_messages", messages)
        return jsonify(status="ok", messages=messages)
    except Exception as e:
        print(f"Slack API error: {e}")
        return jsonify(error="Failed to fetch messages from Slack"), 500

# WebSocket connection
@socketio.on("connect")
def handle_connect():
    print("Client connected via WebSocket")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    socketio.run(app, host="0.0.0.0", port=port)
