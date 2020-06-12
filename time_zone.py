import datetime


class PacificTimeZone(datetime.tzinfo):
    """Implementation of the Pacific timezone."""

    def utcoffset(self, dt: datetime.datetime) -> datetime.timedelta:
        return datetime.timedelta(hours=-8) + self.dst(dt)

    def dst(self, dt: datetime.datetime) -> datetime.timedelta:
        # 2 am on the second Sunday in March
        dst_start = _first_sunday(datetime.datetime(dt.year, 3, 8, 2))
        # 1 am on the first Sunday in November
        dst_end = _first_sunday(datetime.datetime(dt.year, 11, 1, 1))

        if dst_start <= dt.replace(tzinfo=None) < dst_end:
            return datetime.timedelta(hours=1)
        return datetime.timedelta(hours=0)

    def tzname(self, dt: datetime.datetime) -> str:
        if self.dst(dt) == datetime.timedelta(hours=0):
            return 'PST'
        return 'PDT'


def _first_sunday(dt: datetime.datetime) -> datetime.datetime:
    """First Sunday on or after dt."""
    return dt + datetime.timedelta(days=(6-dt.weekday()))
