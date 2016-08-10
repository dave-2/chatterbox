#!/usr/bin/env python
import collections
import datetime
import re
import webapp2

import door_status
import time_zone
import twiml


TIME_ZONE = time_zone.PacificTimeZone()
HOST = "http://mytestapp.appspot.com"

class LastUpdatedOrderedDict(collections.OrderedDict):
    'Store items in the order the keys were last added'

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        collections.OrderedDict.__setitem__(self, key, value)


owners = LastUpdatedOrderedDict({})
subscribers = set()
door = door_status.DoorStatus()


def passcode():
    return '123456'


def open_door(response, reason):
    door.on_open()
    response.play(HOST + '/assets/9tone.wav')
    message = 'Door opened because %s.' % reason
    if door.is_unlocked:
        message += (" It's unlocked for %s more minutes" % door.minutes_left)
    else:
        message += " It's now locked."
    for number in subscribers:
        response.sms(message, to=number)


def call_numbers(response, message):
    response.say(message)
    for number in reversed(owners):
        response.dial(number, timeout=12)


class StatusHandler(webapp2.RequestHandler):
    """Handler for when someone visits the website. Prints the door status."""
    def get(self):
        self.response.out.write(door)


class EnterCodeHandler(webapp2.RequestHandler):
    """Callback for when someone at the intercom enters a passcode."""
    def post(self):
        response = twiml.Response()
        digits = self.request.get('Digits')
        if digits == passcode():
            open_door(response, 'someone entered the correct code')
        else:
            call_numbers(response, 'Oops, wrong code.')
        self.response.out.write(response)


class IntercomHandler(webapp2.RequestHandler):
    """Handler for when someone calls the unit at the intercom."""
    def get(self):
        response = twiml.Response()

        if door.is_unlocked:
            open_door(response, '%s unlocked it' % door.unlocker)
        else:
            # http://www.twilio.com/docs/quickstart/python/twiml/connect-call-to-second-person
            with response.gather(numDigits=len(passcode()), action="/entercode",
                                 method="POST", timeout=15) as gather_verb:
                # "Enter a code if you got one."
                gather_verb.play(HOST + '/assets/code01.mp3')
            call_numbers(response, 'Hang on a sec. Calling them.')

        self.response.out.write(response)


class ControlHandler(webapp2.RequestHandler):
    """Handler for when someone texts the Twilio number with a command."""
    def get(self):
        number = self.request.get('From')
        message = self.request.get('Body').strip()

        if number not in owners:
            response = twiml.Response()
            response.sms('No permissions to grant access. :(')
            self.response.out.write(response)
            return

        # Move number to the front (last item in OrderedDict).
        owners[number] = owners[number]

        response = twiml.Response()

        match = re.match('([0-9]+)(\+?)', message)
        if match:
            minutes, allow_multiple_opens = match.groups()
            minutes = int(minutes)
            allow_multiple_opens = bool(allow_multiple_opens)
            if door.set_minutes(owners[number], minutes, allow_multiple_opens):
              response.sms('YO BITCHES! You added %d minutes! '
                           "The door's unlocked %s minutes until %s. "
                           'Just reply LOCK to lock it.' %
                           (minutes, door.minutes_left, door.lock_time_string))
            else:
              response.sms('YO BITCHES! The door was already unlocked by %s! '
                           "The door's unlocked %s minutes until %s. "
                           'Just reply LOCK to lock it.' %
                           (door.unlocker, door.minutes_left, door.lock_time_string))
        elif message.lower() == 'lock' or message.lower() == 'close':
            door.lock()
            response.sms("LISTEN UP YO -- The door's locked. "
                         'Reply back with a number of minutes to re-unlock.')
        else:
            response.sms('Could not understand. :( Try giving me an integer.')

        self.response.out.write(response)


handlers = [
    ('/', StatusHandler),
    ('/entercode', EnterCodeHandler),
    ('/voice', IntercomHandler),
    ('/sms', ControlHandler),
]
app = webapp2.WSGIApplication(handlers, debug=True)
