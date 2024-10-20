import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objs as go
from plotly.offline import plot
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings("ignore")

pd.set_option('expand_frame_repr', True)  
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)
pd.set_option('display.width', 180) 
pd.set_option('display.max_rows', 5000) 


def calendar_spread_signal(df, para=[60, 45, 40]):
    max_limit, sell_close, min_limit = para
    
    # short signal: short front month, long back month
    condition1 = df['diff'] > max_limit
    condition2 = df['diff'].shift(1) <= max_limit
    df.loc[condition1 & condition2, 'signal_short'] = -1 
    
    # close short signal
    condition1 = df['diff'] < sell_close 
    condition2 = df['diff'].shift(1) >= sell_close  
    condition3 = df['front_month'] != df['front_month'].shift(-1) # deliver day
    df.loc[(condition1 & condition2) | condition3, 'signal_short'] = 0
    
    # long signal: long front month, short back month
    condition1 = df['diff'] < min_limit  
    condition2 = df['diff'].shift(1) >= min_limit  
    df.loc[condition1 & condition2, 'signal_long'] = 1  

    # close long signal
    condition1 = df['diff'] > sell_close
    condition2 = df['diff'].shift(1) <= sell_close
    condition3 = df['front_month'] != df['front_month'].shift(-1) # deliver day
    df.loc[(condition1 & condition2) | condition3, 'signal_long'] = 0
    
    # merge long and short signals
    df['signal'] = df[['signal_long', 'signal_short']].sum(axis=1, min_count=1, skipna=True)
    
    # remove duplicate signals
    temp = df[df['signal'].notnull()][['signal']]
    temp = temp[temp['signal'] != temp['signal'].shift(1)]
    df['signal'] = temp['signal']
    return df


def calc_positions(df):
    df['signal_'] = df['signal']
    df['signal_'].fillna(method='ffill', inplace=True)
    df['signal_'].fillna(value=0, inplace=True) 
    df['pos'] = df['signal_'].shift()
    df['pos'].fillna(value=0, inplace=True)  

    # close position on delivery day
    condition1 = df['front_month'] != df['front_month'].shift(-1)
    df.loc[condition1, 'pos'] = 0

    df.loc[df['pos'] == 1, 'long_contract'] = df['front_month']
    df.loc[df['pos'] == 1, 'short_contract'] = df['back_month']

    df.loc[df['pos'] == -1, 'long_contract'] = df['back_month']
    df.loc[df['pos'] == -1, 'short_contract'] = df['front_month']
    return df


def calc_pnl(df, slippage=2):
    condition1 = df['pos'] != 0
    condition2 = df['pos'] != df['pos'].shift(1)  
    open_pos_condition = condition1 & condition2

    condition1 = df['pos'] != 0  
    condition2 = df['pos'] != df['pos'].shift(-1)
    close_pos_condition = condition1 & condition2

    # calculate start time of each trade
    df.loc[open_pos_condition, 'start_time'] = df['datetime']
    df['start_time'].fillna(method='ffill', inplace=True)
    df.loc[df['pos'] == 0, 'start_time'] = pd.NaT

    # the price of open position: close price + slippage
    df.loc[open_pos_condition, 'open_pos_price'] = df['diff'] + (slippage * df['pos'])
    for _ in ['open_pos_price']:
        df[_].fillna(method='ffill', inplace=True)
    df.loc[df['pos'] == 0, ['open_pos_price']] = None
    
    # close position price: close price + slippage
    df.loc[close_pos_condition, 'close_pos_price'] = df['diff'] - (slippage * df['pos'])
    condition3 = pd.notna(df['open_pos_price']) & pd.notna(df['close_pos_price'])
    df.loc[condition3, 'points_earn'] = (df['close_pos_price'] - df['open_pos_price']) * df['pos']

    df['points_sum'] = df['points_earn'].expanding(min_periods=1).sum()
    return df


def get_performance(pnl_series: pd.Series, para, fig_show=True):
    """
    pnl_series: pandas Series with date as index and pnl as values
    """
    # Convert pnl_series to a DataFrame
    aa = pnl_series.to_frame(name="final.pnl")
    aa.index = pd.to_datetime(aa.index)

    # Calculate cumulative PnL
    pnl = aa["final.pnl"].cumsum()
    date_format = aa.index
    
    # Calculate performance metrics
    daily_return = aa["final.pnl"]
    if daily_return.std() == 0:
        sharpe = 0
        sortino = 0
    else:
        sharpe = daily_return.mean() / daily_return.std() * np.sqrt(250)
        downside_std = daily_return[daily_return < 0].std()
        sortino = daily_return.mean() / downside_std * np.sqrt(250) if downside_std != 0 else 0

    drawdown = ((pnl.cummax() - pnl).max() / pnl.cummax().max()) if pnl.cummax().max() != 0 else 0
    win_ratio = sum(daily_return > 0) / sum(daily_return != 0) if sum(daily_return != 0) != 0 else 0

    # Create a dict with all performance metrics
    performance_df = pd.DataFrame({
        "Param": [str(para)],
        "Cum_PnL": [pnl[-1].round()],
        "Sharpe": [sharpe],
        "Sortino": [sortino],
        "Max Drawdown": [-drawdown],
        "Win Ratio": [win_ratio]
    })
    
    # Plot the performance
    if fig_show:
        fig, ax = plt.subplots(sharex=True, figsize=(10, 6))
        sns.lineplot(x=date_format, y=pnl, ax=ax, dashes=True, color='brown')
        title = f"Param: {para}, Cum_PnL: {pnl[-1]:.2f}, Sharpe: {sharpe:.2f}, Sortino: {sortino:.2f}, Max Drawdown: {drawdown:.2f}, Win Ratio: {win_ratio:.2f}"
        ax.set_title(title)
        ax.set_xlabel("Date")
        ax.set_ylabel("PNL")
        plt.grid(True)
        plt.show()

    return performance_df


def draw_thermodynamic_diagram(df, title, z, show=True, save_path=os.path.join('thermo_pic.html')):
    hot_df = df.copy()
    hot_df.reset_index(inplace=True, drop=True)
    layout = go.Layout(
        plot_bgcolor='red',  
        paper_bgcolor='white',
        autosize=True,
        width=1200,
        height=800,
        title=title,
        titlefont=dict(size=30, color='gray'),

        legend=dict(
            x=0.02,
            y=0.02
        ),

        xaxis=dict(title='lower_bound', 
                   titlefont=dict(color='red', size=20),
                   tickfont=dict(color='blue', size=18, ),
                   tickangle=45,  
                   showticklabels=True,  
                #    autorange=False,
                   # range=[0, 100],
                   type='linear',
                   ),

        yaxis=dict(title='upper_bound',  
                   titlefont=dict(color='blue', size=18),  
                   tickfont=dict(color='green', size=20, ),  
                   showticklabels=True,  
                   tickangle=-45,
                   autorange=True,
                   # range=[0, 100],
                   type='linear',
                   ),
    )

    fig = go.Figure(data=go.Heatmap(
        showlegend=True,
        name='data',
        x=hot_df['x'],
        y=hot_df['y'],
        z=hot_df[z],
        type='heatmap',
    ),
        layout=layout
    )

    fig.update_layout(margin=dict(t=100, r=150, b=100, l=100), autosize=True)

    plot(figure_or_data=fig, filename=save_path, auto_open=False)

    if show:
        res = os.system('start ' + save_path)
        if res != 0:
            os.system('open ' + save_path)