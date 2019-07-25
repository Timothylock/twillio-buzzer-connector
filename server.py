from flask import Flask, request
from flask import send_from_directory
import os
from twilio.twiml.voice_response import VoiceResponse
import sqlite3
import datetime

app = Flask(__name__)

# Initiate Database
db = sqlite3.connect('storage.db')
c = db.cursor()
c.execute("CREATE TABLE IF NOT EXISTS events(validuntil INTEGER)")

# Buzzer
##########################################################################
@app.route("/buzzer/webhook", methods=['GET', 'POST'])
def voice():
    """Respond to incoming phone calls"""
    resp = VoiceResponse()

    # Reject call if the originating number is not from the intercom system
    # Does not incur any cost on twillio but is a shitty user experience
    if False:
        resp.reject("not allowed to buzz")

    # Tell the user a nice message that they are not permitted to enter
    if not allowedToBuzz():
        resp.say("The system cannot let you in. Please tell the host to click allow on their phone")
        return str(resp)

    # Otherwise, unlock the door
    resp.say("unlocking door. Please wait.")
    resp.play(digits='6666')
    resp.say("code injected. If you still hear this, please contact whoever you are trying to reach as the unlock has failed. Goodbye")

    return str(resp)

@app.route("/buzzer/status/allow", methods=['GET'])
def statusAllow():
    """Tells the buzzer to unlock the door for the next 30 minutes"""
    expire = datetime.datetime.now() + datetime.timedelta(minutes=30)

    db = sqlite3.connect('storage.db')
    c = db.cursor()
    c.execute('''INSERT INTO events(validuntil) VALUES(?)''', (expire.timestamp(),))
    db.commit()

    return str("Success. Will buzz everybody in until " + expire.strftime("%m/%d/%Y, %H:%M:%S"))

@app.route("/buzzer/status/", methods=['GET'])
def status():
    """Fetches whether the system will buzz people in"""
    return str(allowedToBuzz())

def allowedToBuzz():
    """Fetches whether the system is allowed to buzz somebody in"""
    now = datetime.datetime.now()

    db = sqlite3.connect('storage.db')
    c = db.cursor()
    c.execute('''SELECT COUNT(validuntil) FROM events WHERE validuntil > ?''', (now.timestamp(),))
    db.commit()

    return c.fetchone()[0] >= 1

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
