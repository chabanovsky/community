from datetime import datetime, timedelta
import numpy as np
import pandas as pd

def np_dt_to_timedelta(dt64):
    # https://stackoverflow.com/a/13704307/564240
    ts = (dt64 - np.datetime64('1970-01-01T00:00:00Z')) / np.timedelta64(1, 's')
    return datetime.utcfromtimestamp(ts) 

def date_moving_avarage(df, date_field, group_field, period=29, day_threshold=1):
    end_dates = df[date_field].dt.round("D").unique()
    dates = pd.DataFrame(data={
        "StartDate": end_dates - pd.to_timedelta(period, unit='d'), 
        "EndDate": end_dates + pd.to_timedelta(1, unit='d'),
        "Index": end_dates
    })
    dates = dates.sort_values(by=["EndDate"])
    result_idx = list()
    result_values = list()
    for index, row in dates.iterrows():
        sd = row.StartDate
        ed = row.EndDate
        i = row.Index

        tmp = df[(df[date_field] > sd) & (df[date_field] <= ed)]
        tmp = tmp.groupby(by=[group_field])[date_field].count().rename("Number").to_frame()
        tmp = tmp[tmp["Number"] >= day_threshold]
        result_idx.append(i)
        result_values.append(len(tmp.index))

    return pd.DataFrame(data={
        "OnDate": result_idx,
        "Value": result_values
    })     