from datetime import datetime, timedelta
import numpy as np

def _np_dt_to_timedelta(dt64):
    # https://stackoverflow.com/a/13704307/564240
    ts = (dt64 - np.datetime64('1970-01-01T00:00:00Z')) / np.timedelta64(1, 's')
    return datetime.utcfromtimestamp(ts) 