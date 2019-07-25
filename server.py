from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import sqlite3
import datetime
import os
import json

app = Flask(__name__)

# Initiate Database
db = sqlite3.connect('storage.db')
c = db.cursor()
c.execute("CREATE TABLE IF NOT EXISTS events(validuntil INTEGER)")

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

    # Tell the user a nice message that they are not permitted to enter
    if not allowed_to_buzz():
        resp.say("The system cannot let you in. Please tell the host to click allow on their phone")
        return str(resp)

    # Otherwise, unlock the door
    resp.say("unlocking door. Please wait.")
    resp.play(digits=buzzcode)
    resp.say("code injected. If you still hear this, please contact whoever you are trying to reach manually. Goodbye")

    return str(resp)


@app.route("/buzzer/state/", methods=['POST'])
def change_state():
    """Tells the buzzer to unlock the door for the next 30 minutes"""
    content = request.json
    if content["allow"] == "true":
        expire = datetime.datetime.now() + datetime.timedelta(minutes=minutes)

        db = sqlite3.connect('storage.db')
        c = db.cursor()
        c.execute('''INSERT INTO events(validuntil) VALUES(?)''', (expire.timestamp(),))
        db.commit()

        return "OK", 200
    else:
        db = sqlite3.connect('storage.db')
        c = db.cursor()
        c.execute("DELETE FROM events")
        db.commit()

        return "OK", 200



@app.route("/buzzer/state/", methods=['GET'])
def status():
    """Fetches whether the system will buzz people in"""
    return json.dumps({"is_active": str(allowed_to_buzz()).lower()}), 200


def allowed_to_buzz():
    """Fetches whether the system is allowed to buzz somebody in"""
    now = datetime.datetime.now()

    db = sqlite3.connect('storage.db')
    c = db.cursor()
    c.execute('''SELECT COUNT(validuntil) FROM events WHERE validuntil > ?''', (now.timestamp(),))
    db.commit()

    return c.fetchone()[0] >= 1


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
