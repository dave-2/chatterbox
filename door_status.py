import datetime
from typing import Optional

import time_zone


TIME_ZONE = time_zone.PacificTimeZone()


class DoorStatus(object):

    _unlocker: Optional[str] = None
    _allow_multiple_opens: bool = False
    _lock_time: datetime.datetime = datetime.datetime.now(TIME_ZONE)

    def __str__(self) -> str:
        if self.is_unlocked:
            s = f'The door was unlocked by {self.unlocker}'
            if self._allow_multiple_opens:
                s += (f" The door's unlocked {self.minutes_left} minutes "
                      f'until {self.lock_time_string}.')
            else:
                s += (f" The door's unlocked {self.minutes_left} minutes "
                      f'until {self.lock_time_string} or someone opens it.')
            return s
        else:
            return "The door's locked."

    @property
    def is_unlocked(self) -> bool:
        return datetime.datetime.now(TIME_ZONE) < self._lock_time

    @property
    def minutes_left(self) -> int:
        time_left = self._lock_time - datetime.datetime.now(TIME_ZONE)
        return int(round(time_left.total_seconds() / 60))

    @property
    def lock_time_string(self) -> Optional[str]:
        if self.is_unlocked:
            return self._lock_time.strftime('%I:%M %p')
        else:
            return None

    @property
    def unlocker(self) -> str:
        return self._unlocker

    def set_minutes(self, unlocker: str, minutes: int,
                    allow_multiple_opens: bool) -> bool:
        new_lock_time = (datetime.datetime.now(TIME_ZONE) +
                         datetime.timedelta(minutes=minutes))
        if new_lock_time <= self._lock_time:
            return False

        self._lock_time = new_lock_time
        self._unlocker = unlocker
        self._allow_multiple_opens = allow_multiple_opens
        return True

    def on_open(self) -> None:
        if not self._allow_multiple_opens:
            self.lock()

    def lock(self) -> None:
        self._lock_time = datetime.datetime.now(TIME_ZONE)
