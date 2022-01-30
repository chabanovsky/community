import os
import re
from datetime import datetime, timedelta
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd


from scipy.stats import chisquare

def read_csvs_in_folder(source_folder):
    files = [os.path.join(source_folder, f)  for f in os.listdir(source_folder) if re.match(r'.*.csv', f)] 
    if len(files) == 1:
        pd.read_csv(files[0])
    dfs = [pd.read_csv(file_) for file_ in files]
    return pd.concat(dfs)     

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

def display_buckets(buckets, freq, group_field='CrationDate', count_field='PostId', long_name=False, unique=False):
    data = []
    for index, bucket in enumerate(buckets):
        tmp = bucket['bucket'].groupby(pd.Grouper(key=group_field, freq=freq))
        tmp = tmp[count_field].nunique() if unique else tmp[count_field].count()
        tmp = tmp.rename(
            "Bucket %d, [%d; %d], total %d" % (
                index, bucket['low'], bucket['hight'], bucket['total']
            ) if long_name else "Bucket_%d" % (index)
        )
        data.append(tmp)
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
        if len(tmp_df.index) == 0:
            return buckets        

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

def split_by_year(df, date_field='CreationDate'):
    return {y: df[df[date_field].dt.year == y] for y in df[date_field].dt.year.unique()}        

def test_further_participation(success, unsuccess, test_field="Outcome", test_val_yes=1):
    s_yes, s_no = len(success[success[test_field] == test_val_yes].index), len(success[success[test_field] != test_val_yes].index)
    u_yes, u_no = len(unsuccess[unsuccess[test_field] == test_val_yes].index), len(unsuccess[unsuccess[test_field] != test_val_yes].index)

    total  = (s_yes + u_yes) + (s_no + u_no)
    t_yes  = s_yes + u_yes
    t_no   = s_no + u_no
    t_succ = s_yes + s_no
    t_uns  = u_yes + u_no

    crosstbl = pd.DataFrame(data={
            "SuccessfulPost": [s_yes,  s_no, t_succ],
            "UnsuccessfulPost": [u_yes,  u_no, t_uns],
            "Total": [t_yes,  t_no, total]
        }, index=["Continued", "Left", "Total"])

    exp_s_yes = t_succ * t_yes / total
    exp_u_yes = t_uns  * t_yes / total
    exp_s_no  = t_succ * t_no  / total
    exp_u_no  = t_uns  * t_no  / total

    expectedtbl = pd.DataFrame(data={
           "SuccessfulPost": [exp_s_yes, exp_s_no, exp_s_yes+exp_s_no],
           "UnsuccessfulPost": [exp_u_yes, exp_u_no, exp_u_yes+exp_u_no],
           "Total": [exp_s_yes+exp_u_yes, exp_s_no+exp_u_no, (exp_s_yes+exp_u_yes)+(exp_s_no+exp_u_no)]
        }, index=["Continued", "Left", "Total"])

    f_obs = [s_yes, u_yes, s_no, u_no]
    f_exp = [exp_s_yes, exp_u_yes, exp_s_no,  exp_u_no] 

    return chisquare(f_obs, f_exp=f_exp, ddof=1), crosstbl, expectedtbl
