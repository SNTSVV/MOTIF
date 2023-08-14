import math


def convert_time_for_SLURM( _timevalue):
    MAX_REQUEST_TIME = 86400*2
    if _timevalue < 0:
        return None
    if _timevalue > MAX_REQUEST_TIME: _timevalue = MAX_REQUEST_TIME

    sec = _timevalue % 60
    _timevalue = math.floor(_timevalue / 60)
    min = _timevalue % 60
    _timevalue = math.floor(_timevalue / 60)
    hour = _timevalue % 24
    day = math.floor(_timevalue / 24)

    if day > 0:
        time_string = "%d-%02d:%02d:%02d"% (day, hour, min, sec)
    else:
        time_string = "%02d:%02d:%02d"% (hour, min, sec)
    return time_string