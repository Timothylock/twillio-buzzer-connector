from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
import datetime
import os
import json
import http.client

app = Flask(__name__)
allowUntil = datetime.datetime.now()

# Fetch env vars
whitelisted_numbers = os.environ['WHITELISTED_NUMBERS'].split(",")  # Numbers allowed to dial into the system
forward_number = os.environ['FORWARD_NUMBER']                       # Number that will be forwarded to if not whitelisted
forward_number_from = os.environ['FORWARD_NUMBER_FROM']             # Number that will be forwarded to if not whitelisted
buzzcode = os.environ['BUZZCODE']                                   # Digits to dial to let them in
minutes = int(os.environ['MINUTES'])                                # Number of minutes to unlock the system
slack_path = os.environ['SLACK_PATH']                               # Slack path for slack message
say_message = os.environ['SAY_MESSAGE']                             # The message to be said to the dialer
say_language = os.environ['TTS_LANG']                               # The language for the TTS


# Buzzer
##########################################################################
@app.route("/buzzer/webhook", methods=['GET', 'POST'])
def voice():
    """Respond to incoming phone calls"""
    resp = VoiceResponse()
    incoming_number = request.values['From']

    # If an unknown number, filter out robo callers and forward to cell
    if incoming_number not in whitelisted_numbers:
        gather = Gather(num_digits=1, action='/buzzer/forward')
        gather.say('Press 1 to continue')
        resp.append(gather)

        return str(resp)

    # Tell the user a nice message that they are not permitted to enter
    if not allowed_to_buzz():
        resp.say("The system cannot let you in. Did you dial the right buzzcode?")
        send_message("A visitor was just rejected as the buzzer system was not unlocked")
        return str(resp)

    # Otherwise, unlock the door
    resp.say(say_message, language=say_language)
    resp.play(digits=buzzcode)
    send_message("A visitor was just let in")

    return str(resp)

@app.route("/buzzer/forward", methods=['GET', 'POST'])
def forward():
    resp = VoiceResponse()
    incoming_number = request.values['From']
    send_message("About to forward a call from " + str(incoming_number))

    resp.say("Please note your call may be recorded for the benefit of both parties")
    resp.dial(forward_number, caller_id=forward_number_from)
    return str(resp)


@app.route("/buzzer/state", methods=['POST'])
def change_state():
    """Tells the buzzer to unlock the door for the next 30 minutes"""
    global allowUntil
    c = request.json

    if "active" not in c:
        return "missing \"active\" field", 400

    if c["active"] == "true":
        allowUntil = datetime.datetime.now() + datetime.timedelta(minutes=minutes)

    if c["active"] == "false":
        allowUntil = datetime.datetime.now()

    return "OK", 200


@app.route("/buzzer/state", methods=['GET'])
def status():
    """Fetches whether the system will buzz people in"""
    return json.dumps({"is_active": str(allowed_to_buzz()).lower()}), 200


def allowed_to_buzz():
    """Fetches whether the system is allowed to buzz somebody in"""
    global allowUntil
    return allowUntil > datetime.datetime.now()


def send_message(message):
    try:
        conn = http.client.HTTPSConnection("hooks.slack.com")

        payload = "{\"text\": \"" + message + "\"}"

        headers = {
            'content-type': "application/json",
        }

        conn.request("POST", slack_path, payload, headers)

        conn.getresponse()
    except:
        print("error sending message")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
