from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)


SLACK_BOT = os.getenv("SLACK_BOT_TOKEN")
CHANNEL_ID = os.getenv("SLACK_CHANNEL")
ML_MODEL_URL = "http://localhost:5000/generate"  # ML model endpoint

def get_username_from_user_id(user_id):
    """Fetch Slack username from user ID"""
    if not user_id:
        return "Unknown"
    try:
        response = requests.get(
            "https://slack.com/api/users.info",
            headers={"Authorization": f"Bearer {SLACK_BOT}"},
            params={"user": user_id}
        )
        return response.json().get("user", {}).get("real_name", "Unknown")
    except Exception as e:
        print(f"Error fetching username: {e}")
        return "Unknown"

@app.route("/slack-messages", methods=["GET", "POST"])
def handle_slack_messages():
    """Endpoint to fetch and process Slack messages"""
    try:
        # get messages from slack
        slack_response = requests.get(
            "https://slack.com/api/conversations.history",
            headers={"Authorization": f"Bearer {SLACK_BOT}"},
            params={"channel": CHANNEL_ID}
        )
        slack_response.raise_for_status()
        
        messages = []
        for msg in slack_response.json().get("messages", []):
            if "subtype" in msg:  # remove sub mesage
                continue

            # extract message data
            user_id = msg.get("user") or msg.get("bot_profile", {}).get("user_id")
            username = (msg["bot_profile"]["name"] 
                       if "bot_profile" in msg 
                       else get_username_from_user_id(user_id))
            text = msg.get("text", "")

            # ml process
            try:
                ml_response = requests.post(
                    ML_MODEL_URL,
                    json={"text": text},
                    timeout=5  
                )
                ml_response.raise_for_status()
                ml_output = ml_response.json().get("output", "")
            except requests.exceptions.RequestException as e:
                print(f"ML model error: {e}")
                ml_output = f"Model error: {str(e)}"

            messages.append({
                "user_id": user_id,
                "username": username,
                "text": text,
                "ml_output": ml_output,
                "app_id": msg.get("app_id")
            })

        return jsonify({
            "status": "success",
            "message_count": len(messages),
            "messages": messages
        })

    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False) 