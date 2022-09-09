import base64
import datetime
import hashlib
import hmac
import json
import os
import time
from ast import literal_eval
from urllib import parse
import requests
from config import config_dict
import pandas as pd
from tqsdk import TqApi, TqAuth, TqKq, TqAccount
from config import notify_sender

# 登录期货账户，若real_trade为1，进入实盘模式。否则进入模拟盘
def login_tq_account(real_trade):
    if real_trade == 0:
        print('当前为模拟交易模式，登录天勤快期模拟账户')
        api = TqApi(TqKq(), auth=TqAuth(config_dict['tq_id'], config_dict['tq_password']))
    elif real_trade == 1:
        company_name = config_dict['company_name']
        account = config_dict['account']
        print(f'登录{company_name}账户{account}，开始实盘交易。')
        api = TqApi(TqAccount(company_name, account, config_dict['password']), auth=TqAuth(config_dict['tq_id'], config_dict['tq_password']))
    return api




def send_dingding_message_every_loop(spread_ask, spread_bid, hh_spread, ll_spread,high_price,low_price):
    content = f'当前IC价差：\n卖一价：{spread_ask}\n买一价：{spread_bid}\n最高价：{hh_spread}\n最低价：{ll_spread}'

    if spread_bid > high_price:
        content += f'\n当前价差已达到观察区间的高点{high_price}点以上，可以考虑做空价差啦~'
        notify_sender.send_msg(content)
    elif spread_ask < low_price:
        content += f'\n当前价差已达到观察区间的低点{low_price}点以下，可以考虑平空价差或开多价差啦~'
        notify_sender.send_msg(content)
      




def save_spread_data(spread_bid, spread_ask, hh_spread, ll_spread, run_time):
    """
    用于保存价差信息
    :param spread_bid:
    :param spread_ask:
    :param hh_spread:
    :param ll_spread:
    :return:
    """
    date = datetime.datetime.now().date()
    path = f'spread_data\\{date}.csv'
    # 判断以当前日期为文件名的数据文件是否存在，若不存在，创建新的。
    col = ['买1价', '卖1价', '最高价', '最低价']
    df = pd.DataFrame(columns=col)
    df.loc[run_time] = [spread_bid, spread_ask, hh_spread, ll_spread]
    if os.path.exists(path):
        # 若文件存在，则用追加模式mode='a'，且不写入列名header=False
        df.to_csv(path, mode='a', index=True, header=False)
    else:
        # 若文件本身不存在，则用写入模式mode='w'，且需要写入列名header=True
        df.to_csv(path, mode='w', index=True, header=True)

        

def check_order_status(api, order_near, order_deferred):
    """
    检查当前订单状态，若5秒后仍未成交，发送钉钉提醒
    :param api:
    :param order_near:
    :param order_deferred:
    :return:
    """
    chick_time = datetime.datetime.now()
    while True:
        api.wait_update()
        if order_near.status == 'FINISHED' and order_deferred.status == 'FINISHED':
            trade_price = order_near.trade_price - order_deferred.trade_price
            content = f'\n执行价差卖出操作成功，成交价格：{trade_price}，程序退出。'
            print(content)
            break
        else:
            # 超过5秒未成交，发送钉钉提醒。
            if (datetime.datetime.now() - chick_time).seconds > 5:
                content = '超过5秒未成交，请手动检查当前订单执行状况，防止单腿！'
                print(content)
                break
    return content