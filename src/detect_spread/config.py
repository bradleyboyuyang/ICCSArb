import json
from notify.dingding import DingTalkRobot
from notify.wechat import WechatRobot
from notify.telegram import TgRobot

with open(r'config.json', encoding='utf-8') as config_file:
    config_dict = json.load(config_file)

if config_dict['enable_notify'] == "dingding":
    notify_sender = DingTalkRobot(robot_id = config_dict["dingding"]["robot_id"],secret = config_dict["dingding"]["secret"])
elif config_dict['enable_notify'] == "telegram":
    notify_sender = TgRobot(token = config_dict["telegram"]["token"], chat_id = config_dict["telegram"]["chat_id"])
elif config_dict['enable_notify'] == "wechat":
    notify_sender = WechatRobot(config_dict["wechat"]["corpid"], config_dict["wechat"]["secret"], config_dict["wechat"]["agent_id"])
else:
    raise ValueError("框架没有检测到告警机器人配置,请检查!")


if __name__=="__main__":
    notify_sender.send_msg("hello world")    