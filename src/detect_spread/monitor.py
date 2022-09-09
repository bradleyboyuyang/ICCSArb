'''
Description: 
Author: zhanglianzhong
Date: 2021-12-19 15:58:35
LastEditTime: 2021-12-19 23:21:37
LastEditors: zhanglianzhong
Reference:  IC股指期货价差监控,监控主力连合约,季度合约价差
'''
from tqsdk import TqApi, TqAuth, TargetPosTask
import threading
from apscheduler.schedulers.blocking import BlockingScheduler
from config import config_dict,notify_sender
from functions import *
import time

class monitor_task(threading.Thread):
    
    def __init__(self, api,type,near_symbol,deferred_symbol,high_price,low_price):
         threading.Thread.__init__(self)
         self.api = api
         self.type = type
         self.near_symbol = near_symbol
         self.deferred_symbol = deferred_symbol
         self.high_price = high_price
         self.low_price = low_price
 
    def run(self):
        # 创建监控合约盘口实例：
        try:
           quote_near = self.api.get_quote(self.near_symbol)
           quote_deferred = self.api.get_quote(self.deferred_symbol)
        except Exception as e:
           print(e)
           print(f"{self.near_symbol}-{self.deferred_symbol}合约对不存在,请检查配置!")    
           return
        hh_spread = None
        ll_spread = None

        # 进入当日循环
        while True:
            self.api.wait_update(deadline=time.time() + 10)
            run_time = datetime.datetime.now()
            if run_time.minute % (config_dict["notify_inteval"]) == 0 and run_time.second == 0:
                content = f'当前IC对{self.near_symbol}-{self.deferred_symbol}价差统计：\n卖一价差：{spread_ask}\n买一价差：{spread_bid}\n今日最高价差：{hh_spread}\n今日最低价差：{ll_spread}'
                notify_sender.send_msg(content)
            # 收盘判断
            if run_time.hour >= 15:
                self.api.close()
                return 
            if self.api.is_changing(quote_near) or self.api.is_changing(quote_deferred):
                # 当远月合约价格低，近月合约价格高，做价差回归时
                # 要按照买一价（quote_deferred.bid_price1）卖出近月，同时按照卖一价（quote_deferred.ask_price1）买入远月
                spread_bid = round(quote_near.bid_price1 - quote_deferred.ask_price1, 2)
                
                # 当远月合约价格低，近月合约价格高，平仓时，
                # 要按照卖一价（quote_near.ask_price1）买平近月，同时按照买一价（quote_deferred.bid_price1）卖平远月
                spread_ask = round(quote_near.ask_price1 - quote_deferred.bid_price1, 2)  # 卖出价差等于近月的买一价 - 远月的卖一价

                # 计算当日的最高（最低）价
                hh_spread  = max(hh_spread,spread_bid) if hh_spread else spread_bid     
                ll_spread = min(ll_spread,spread_ask)  if ll_spread else spread_ask
                # 此处最低价与最高价取盘口中可交易的价差，会存在最低价比最高价高的情况
                print("\r卖一价:", spread_ask, " 买一价:", spread_bid, '今日最高价:', hh_spread, '今日最低价:', ll_spread, end='')

                send_dingding_message_every_loop(spread_ask, spread_bid, hh_spread, ll_spread,self.high_price,self.low_price)

                save_spread_data(spread_bid, spread_ask, hh_spread, ll_spread, run_time)


def monitor():
    #登陆天勤
    notify_sender.send_msg(f"IC价差监控程序已启动,当前监控任务为{config_dict['monitor_tasks']}")
    for task_config in config_dict['monitor_tasks']:
        api = login_tq_account(config_dict['real_trade'])
        task_thread = monitor_task(api,task_config['type'],task_config['near_symbol'],task_config['deferred_symbol'],task_config['high_price'],task_config['low_price'])
        task_thread.start()
        
        

if __name__ == '__main__':
   scheduler = BlockingScheduler()
   #scheduler.add_job(monitor,'cron',minute='*/3',id = 'monitor')  
   scheduler.add_job(monitor,'cron',day_of_week='mon-fri',hour='9',minute='30',id = 'monitor')  

   scheduler.start()
                               
