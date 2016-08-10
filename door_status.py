import datetime

import time_zone


TIME_ZONE = time_zone.PacificTimeZone()


class DoorStatus(object):
    def __init__(self):
        self._unlocker = None
        self._allow_multiple_opens = False
        self._reset_time()

    def __str__(self):
        if self.is_unlocked:
            s = 'The door was unlocked by %s.' % self.unlocker
            if self._allow_multiple_opens:
                s += (" The door's unlocked %d minutes until %s." %
                      (self.unlocker, self.minutes_left, self.lock_time_string))
            else:
                s += (" The door's unlocked %d minutes until %s or "
                      'until someone opens it.' %
                      (self.unlocker, self.minutes_left, self.lock_time_string))
            return s
        else:
            return "The door's locked."

    def _reset_time(self):
        self._lock_time = datetime.datetime.now(TIME_ZONE)

    @property
    def is_unlocked(self):
        return datetime.datetime.now(TIME_ZONE) < self._lock_time

    @property
    def minutes_left(self):
        time_left = self._lock_time - datetime.datetime.now(TIME_ZONE)
        return int(round(time_left.total_seconds() / 60))

    @property
    def lock_time_string(self):
        if self.is_unlocked:
            return self._lock_time.strftime('%I:%M %p')
        else:
            return None

    @property
    def unlocker(self):
        return self._unlocker

    def set_minutes(self, unlocker, minutes, allow_multiple_opens):
        new_lock_time = (datetime.datetime.now(TIME_ZONE) +
                         datetime.timedelta(minutes=minutes))
        if new_lock_time <= self._lock_time:
            return False

        self._lock_time = new_lock_time
        self._unlocker = unlocker
        self._allow_multiple_opens = allow_multiple_opens
        return True

    def on_open(self):
        if not self._allow_multiple_opens:
            self.lock()

    def lock(self):
        self._reset_time()
