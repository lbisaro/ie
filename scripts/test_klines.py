from bot.model_kline import Kline
from bot.models import Bot
from django.utils import timezone
import pandas as pd
import numpy as np
from scripts.BotBase import BotBase
import functions as fn




def run():

    bot_id = 1
    bot = Bot.objects.get(pk=bot_id)
    orders = bot.get_orders()
    botClass = bot.get_instance()
    last_posorder_id = 0
    for o in orders:
        comision = round(o.price * o.qty * (BotBase.exch_comision_perc/100) ,4)
        order_datetime = o.datetime.replace(second=0, microsecond=0)
        if o.completed > 0 and o.pos_order_id > 0:
            order_datetime = pd.to_datetime(o.datetime)
            order_datetime = order_datetime.floor('5T')
            
            order = [
                order_datetime,
                o.symbol.symbol,
                o.side,
                o.qty,
                o.price,
                o.flag,
                comision,
            ] 

            order_datetime = o.datetime.strftime("%Y-%m-%d %H:%M")
            if o.pos_order_id != last_posorder_id:
                last_posorder_id = o.pos_order_id
                botClass.open_pos(order_datetime,o.price,o.qty)
            else:
                botClass.close_pos(order_datetime,o.price,o.flag)

            botClass.res['orders'].append(order)
    
    order_columns = ['datetime','symbol','side','qty','price','flag','comision']
    df_orders = pd.DataFrame(botClass.res['orders'], columns=order_columns)
    df_orders.set_index('datetime', inplace=True)
    print(df_orders)
    print(df_orders.count())


    order_datetime = pd.to_datetime('2023-10-16 02:31:00+00:00')
    print(order_datetime)
    order_datetime = order_datetime.floor('5T')
    print(order_datetime)
    order_datetime = o.datetime.strftime("%Y-%m-%d %H:%M")
    print(order_datetime)
