import asyncio
from datetime import datetime, timedelta, timezone

import pytz

us_central_tz = pytz.timezone("US/Central")


async def wait_until(dt):
    """ Sleep until the specified datetime. Expects UTC """
    now = datetime.now(timezone.utc)
    await asyncio.sleep((dt - now).total_seconds())


def calc_tomorrow_at_time(hour, min):
    """Calculate tomorrow in US Central time. Convert to UTC. Return.
    Arguments are hour in military (24hr) time, min
    """
    tmwr_ct = datetime.now(us_central_tz) + timedelta(days=1)
    tmwr_ct = tmwr_ct.replace(hour=hour, minute=min, second=0, microsecond=0)
    tmrw_utc = tmwr_ct.astimezone(timezone.utc)
    return tmrw_utc


def calc_tomorrow_6am():
    return calc_tomorrow_at_time(6, 0)


def calc_tomorrow_7am():
    return calc_tomorrow_at_time(7, 0)


def calc_tomorrow_4pm():
    return calc_tomorrow_at_time(16, 0)


def naive_to_us_central(naive_datetime):
    utc_datetime = naive_datetime.replace(tzinfo=timezone.utc)
    return utc_datetime.astimezone(us_central_tz)


def fmt_datetime_to_minute(dtm):
    return dtm.strftime("%Y-%m-%d at %I:%M %p")
