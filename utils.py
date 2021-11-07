from datetime import datetime, timedelta
from matplotlib import pyplot as plt
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

def display_buckets(buckets, freq, group_field='CrationDate', count_field='PostId'):
    data = []
    for index, bucket in enumerate(buckets):
        data.append(
            bucket['bucket'].groupby(pd.Grouper(key=group_field, freq=freq))[count_field].count().rename(
                "Bucket %d, [%d; %d], total %d" % (
                    index, bucket['low'], bucket['hight'], bucket['total']
                )
            )
        )
    return data
    
def split_into_buckets(df, groupby_field='CreationUserId', count_field='PostId', iterations=3, need_report=True):
    def add_bucket(buckets, sliced, low, hight, index, need_report):
        total = sliced.groupby([groupby_field])[count_field].count().size
        if need_report:
            print("Bucket %f [%d; %d], size %d" % (index, low, hight, total))

        buckets.append({
            "bucket": sliced,
            "low": low,
            "hight": hight,
            "total": total
        })
        
    if need_report:
        print("Total size %s" % (str(df.groupby([groupby_field])[count_field].count().size)))
        
    buckets = []
    threshold_low = 0
    for index in range(iterations):
        tmp_df = df.groupby([groupby_field])[count_field].count()
        q75 = tmp_df.quantile(0.75)
        q25 = tmp_df.quantile(0.25)
        iqr = q75 - q25
        threshold_hight = int(round(q75 + 1.5 * iqr))
        tmp_df = tmp_df[(tmp_df >= threshold_low) & (tmp_df <= threshold_hight)]
        
        the_slice = df[df[groupby_field].isin(set(tmp_df.index))]
        the_rest = df[~df[groupby_field].isin(set(tmp_df.index))]
        add_bucket(buckets, the_slice, threshold_low, threshold_hight, index, need_report)
        threshold_low = threshold_hight + 1
        df = the_rest
        if index+1 == iterations: # the last iteration
            add_bucket(buckets, the_rest, threshold_low, -1, index+1, need_report)
            
        
    return buckets