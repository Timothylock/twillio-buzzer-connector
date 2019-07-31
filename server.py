from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import datetime
import os
import json
import http.client

app = Flask(__name__)
allowUntil = datetime.datetime.now()

# Fetch env vars
whitelisted_numbers = os.environ['WHITELISTED_NUMBERS'].split(",")          # Numbers allowed to dial into the system
buzzcode = os.environ['BUZZCODE']                                           # Digits to dial to let them in
minutes = int(os.environ['MINUTES'])                                        # Number of minutes to unlock the system


# Buzzer
##########################################################################
@app.route("/buzzer/webhook", methods=['GET', 'POST'])
def voice():
    """Respond to incoming phone calls"""
    resp = VoiceResponse()
    incoming_number = request.values['From']

    # Reject call if the originating number is not from the intercom system
    # Does not incur any cost on twillio but is a shitty user experience
    if incoming_number not in whitelisted_numbers:
        resp.reject("not allowed to buzz")
        return str(resp)

    # Tell the user a nice message that they are not permitted to enter
    if not allowed_to_buzz():
        resp.say("The system cannot let you in. Please tell the host to click allow on their phone")
        send_message("A visitor was just rejected as the buzzer system was not unlocked")
        return str(resp)

    # Otherwise, unlock the door
    resp.say("unlocking door. Please wait.")
    resp.play(digits=buzzcode)
    resp.say("code injected. If you still hear this, please contact whoever you are trying to reach manually. Goodbye")
    send_message("A visitor was just let in")


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
        conn = http.client.HTTPConnection("10.88.111.31:9090")

        payload = "{\"room\": \"#general\", \"message\": \"" + message + "\"}"

        headers = {
            'content-type': "application/json",
        }

        conn.request("POST", "/incoming/something", payload, headers)

        conn.getresponse()
    except:
        print("error sending message")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
