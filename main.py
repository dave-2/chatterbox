#!/usr/bin/env python
import collections
import os
import re
from typing import OrderedDict, Set

import flask
from twilio.twiml import messaging_response
from twilio.twiml import voice_response

import door_status
import time_zone


app = flask.Flask(__name__)

TIME_ZONE = time_zone.PacificTimeZone()

OWNERS: OrderedDict[str, str] = collections.OrderedDict({})
SUBSCRIBERS: Set[str] = set()
door: door_status.DoorStatus = door_status.DoorStatus()


def passcode() -> str:
    return '123456'


def open_door(response: voice_response.VoiceResponse, reason: str) -> None:
    door.on_open()
    response.play(digits=9)
    message = f'Door opened because {reason}.'
    if door.is_unlocked:
        message += f" It's unlocked for {door.minutes_left} more minutes."
    else:
        message += " It's now locked."
    for number in SUBSCRIBERS:
        # TODO: <Sms> is deprecated: https://www.twilio.com/docs/voice/twiml/sms
        # "To send a text message in response to an incoming phone call, use a
        # webhook to trigger your own application code and use the REST API to
        # send a text message."
        response.sms(message, to=number)


def call_numbers(response: voice_response.VoiceResponse, message: str) -> None:
    response.say(message)
    for number in reversed(OWNERS):
        response.dial(number, timeout=12)


@app.route('/')
def status() -> str:
    return str(door)


@app.route('/entercode', methods=['POST'])
def enter_code() -> str:
    """Callback for when someone at the intercom enters a passcode."""
    response = voice_response.VoiceResponse()
    digits = flask.request.args.get('Digits')
    if digits == passcode():
        open_door(response, 'someone entered the correct code')
    else:
        call_numbers(response, 'Oops, wrong code.')
    return str(response)


@app.route('/voice')
def intercom() -> str:
    """Handler for when someone calls the unit at the intercom."""
    response = voice_response.VoiceResponse()

    if door.is_unlocked:
        open_door(response, f'{door.unlocker} unlocked it')
    else:
        with response.gather(numDigits=len(passcode()), action="/entercode",
                             method="POST", timeout=15) as gather_verb:
            # "Enter a code if you got one."
            if 'GAE_APPLICATION' in os.environ:
                application_id = os.environ['GAE_APPLICATION']
                hostname = f"https://{application_id.split('~')[1]}.appspot.com"
            else:
                hostname = 'https://localhost:5000'
            gather_verb.play(f'{hostname}/static/code01.mp3')
        call_numbers(response, 'Hang on a sec. Calling them.')

    return str(response)


@app.route('/sms')
def control() -> str:
    """Handler for when someone texts the Twilio number with a command."""
    number = flask.request.args.get('From')
    message = flask.request.args.get('Body', '').strip()

    response = messaging_response.MessagingResponse()

    if number not in OWNERS:
        response.message('No permissions to grant access. :(')
        return str(response)

    # Move number to the front (last item in OrderedDict).
    OWNERS.move_to_end(number)

    match = re.match(r'([0-9]+)(\+?)', message)
    if match:
        minutes, allow_multiple_opens = match.groups()
        minutes = int(minutes)
        allow_multiple_opens = bool(allow_multiple_opens)
        if door.set_minutes(OWNERS[number], minutes, allow_multiple_opens):
            response.message(
                f'YO BITCHES! You added {minutes} minutes! '
                f"The door's unlocked {door.minutes_left} minutes until "
                f'{door.lock_time_string}. Just reply LOCK to lock it.')
        else:
            response.message(
                'YO BITCHES! '
                f'The door was already unlocked by {door.unlocker}! '
                f"The door's unlocked {door.minutes_left} minutes until "
                f'{door.lock_time_string}. Just reply LOCK to lock it.')
    elif message.lower() == 'lock' or message.lower() == 'close':
        door.lock()
        response.message("LISTEN UP YO -- The door's locked. "
                         'Reply back with a number of minutes to re-unlock.')
    else:
        response.message('Could not understand. :( Try giving me an integer.')

    return str(response)


if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app.
    app.run(debug=True)
