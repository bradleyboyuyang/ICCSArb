import numpy as np
import pandas as pd
from tqdm import tqdm
from Functions import *

# hyperparameters
DATA_PATH = './data/stock_if_min_cffex/'
FUTURE = 'IC'
PARA_LIST = [54, 29, 14]
# PARA_LIST = [100, 80, 60]
SLIPPAGE = 2 # unit of index points
MULTIPLIER = 200

files = os.listdir(DATA_PATH + FUTURE + '/')
files = sorted(files)
df_list = []

# read data
for i in tqdm(range(0, len(files)-1)):
        
    # front-month
    df1 = pd.read_csv(DATA_PATH + FUTURE + '/' + files[i], parse_dates=['datetime'])
    df1['front_month'] = files[i].split('.')[0]
    df1.sort_values(by=['datetime'], inplace=True)

    # back-month
    df2 = pd.read_csv(DATA_PATH + FUTURE + '/' + files[i+1], parse_dates=['datetime'])
    df2['back_month'] = files[i+1].split('.')[0]
    df2.sort_values(by=['datetime'], inplace=True)

    df_merge = pd.merge(left=df1, right=df2, on=['datetime'], how='left', sort=True)
    df_merge.drop(['volume_x', 'volume_y'], axis=1, inplace=True)  
    
    # generate a column to indicate 1 days within delivery day
    delivery_day = df_merge['datetime'].dt.date.max()
    df_merge['delivery'] = (delivery_day - df_merge['datetime'].dt.date).dt.days <= 1
    df_merge.dropna(inplace=True)
    df_list.append(df_merge)

df = pd.concat(df_list, ignore_index=True)

# drop duplicate timestamps (we trade one pair of contracts at a time)
df.drop_duplicates(subset='datetime', inplace=True)

# when close to delivery day, price difference becomes extremely unstable
# significantly improve result
df = df[~df['delivery']]

# delete boundary timestamp 9:30, 11:30, 13:00, 15:00 (usually not tradable)
df = df[~df['datetime'].dt.strftime('%H:%M').isin(['09:30', '11:30', '13:00', '15:00'])]
# calculate spread
df['diff'] = df['price_x'] - df['price_y']
df.sort_values('datetime', inplace=True)
df.reset_index(drop=True, inplace=True)

df.to_csv('./data/merged_data.csv', index=False)

# print(df['diff'].describe())
# exit()

# generate signal
df = calendar_spread_signal(df, para=PARA_LIST)

# generate positions
df = calc_positions(df)

df = calc_pnl(df, slippage=SLIPPAGE)

# generate summary dataframe
summary_df = df[pd.notna(df['points_earn'])] 
summary_df = summary_df[['start_time', 'datetime', 'long_contract', 'short_contract', 'pos', 'open_pos_price', 'close_pos_price', 'points_earn']].reset_index(drop=True)
summary_df.rename(columns={'datetime': 'end_time', 'open_pos_price': 'open_diff', 'close_pos_price': 'close_diff', 'pos': 'position', 'long_contract':'long', 'short_contract':'short'}, inplace=True)
summary_df['cum_pnl'] = (summary_df['points_earn']*MULTIPLIER).cumsum() 

# calculate performance metrics and plot
df_daily = df.set_index('datetime')[['points_earn']].resample('D').sum()
performance = get_performance(df_daily['points_earn']*MULTIPLIER, para=PARA_LIST, fig_show=True)
print(summary_df)
print(performance)

