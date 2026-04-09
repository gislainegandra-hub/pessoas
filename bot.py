import os
import re
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
from anthropic import Anthropic

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

client = Anthropic()

SYSTEM_PROMPT = """Voce e o assistente de onboarding da Telavita. Responda perguntas dos colaboradores sobre politicas internas de forma cordial e objetiva."""

conversation_history = {}

def get_ai_response(user_id, user_message):
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    conversation_history[user_id].append({"role": "user", "content": user_message})
    if len(conversation_history[user_id]) > 10:
        conversation_history[user_id] = conversation_history[user_id][-10:]
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=conversation_history[user_id]
    )
    assistant_message = response.content[0].text
    conversation_history[user_id].append({"role": "assistant", "content": assistant_message})
    return assistant_message

@app.event("app_mention")
def handle_app_mention(event, say):
    user_id = event["user"]
    text = re.sub(r"<@[A-Z0-9]+>", "", event["text"]).strip()
    if not text:
        say("Ola! Como posso te ajudar?")
        return
    say(get_ai_response(user_id, text))

@app.event("message")
def handle_direct_message(event, say):
    if event.get("bot_id") or event.get("channel_type") != "im":
        return
    user_id = event["user"]
    text = event.get("text", "").strip()
    if not text:
        return
    say(get_ai_response(user_id, text))

flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

@flask_app.route("/health", methods=["GET"])
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    flask_app.run(host="0.0.0.0", port=port)
