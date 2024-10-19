import pandas as pd
from tqdm import tqdm
import os
from joblib import Parallel, delayed

from Functions import *

SLIPPAGE = 2 # unit of index points
MULTIPLIER = 200
multiprocess = True # run in parallel

def calendar_spread_para_list(n_list=range(40, 60, 2), m_list=range(25, 50, 2), g_list=range(10, 30, 2)):
    para_list = []
    for n in n_list:
        for m in m_list:
            for g in g_list:
                if n > m > g:
                    para_list.append([n, m, g])
    return para_list

def backtest_once(df, para):
    df = df.copy()
    # generate signal
    df = calendar_spread_signal(df, para=para)
    # generate positions
    df = calc_positions(df)
    # calculate pnl
    df = calc_pnl(df, slippage=SLIPPAGE)

    df_daily = df.set_index('datetime')[['points_earn']].resample('D').sum()
    performance = get_performance(df_daily['points_earn']*MULTIPLIER, para=para, fig_show=False)
    return performance


df_futures = pd.read_csv('./data/merged_data.csv')
df_futures['datetime'] = pd.to_datetime(df_futures['datetime'])
para_list = calendar_spread_para_list()
if multiprocess:
    result_list = Parallel(n_jobs=os.cpu_count()-2)(delayed(backtest_once)(df_futures, para) for para in tqdm(para_list))
else:
    result_list = []
    for para in tqdm(para_list):
        result = backtest_once(df_futures, para)
        result_list.append(result)
        
result = pd.concat(result_list, ignore_index=True)
result.sort_values(by='Sharpe', ascending=False, inplace=True)
result.reset_index(drop=True, inplace=True)
print(result.head(20))
result.to_csv('result.csv')
