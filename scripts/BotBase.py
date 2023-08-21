#from abc import ABC, abstractmethod
from bot.models import *
import functions as fn
import my_logging as mylog
from django.utils import timezone


from bot.models import *

class BotBase():
    SIDE_BUY = 0
    SIDE_SELL = 1

    FLAG_SIGNAL = 0
    FLAG_STOPLOSS = 1
    FLAG_TAKEPROFIT = 2

    quote_qty = 0
    interval_id = ''

    ##@abstractmethod
    #def run(self):
    #    pass

    def __init__(self):
        pass

    def start(self,bot_id,client):
        self.bot_id = bot_id
        self.bot = Bot.objects.get(pk=self.bot_id)
        self.client = client

        prms = self.bot.parse_parametros()
        for p in prms:
            self.__setattr__(p['c'],p['v'])

    def set(self, parametros):
        for v in parametros:
            self.__setattr__(parametros[v]['c'], parametros[v]['v'])

    def __setattr__(self, prm, val):
        type = 'str'
        if prm == 'quote_qty' or prm == 'interval_id':
            self.__dict__[prm] = val
        else:
            type = self.parametros[prm]['t']
            if type == 'perc' or type == 'float':
                self.__dict__[prm] = float(val)
            elif type == 'int':
                self.__dict__[prm] = int(val)
            else:
                self.__dict__[prm] = str(val)
    
    def get_symbols(self):
        # metodo que devuelve una lista con los symbols afectados al Bot Ej: ['BTCUSDT','TRXUSDT']
        pass 

    def create_market_order(self,base_asset,quote_asset,side,quantity):
        symbol = base_asset+quote_asset
        try:
            if side == self.SIDE_BUY:
                order = self.client.order_market_buy(symbol=symbol, quantity= quantity)
            else:
                order = self.client.order_market_sell(symbol=symbol, quantity= quantity)
                
            completed = 1 if order['status'] == 'FILLED' else 0
            if completed == 1:
                price = round(float(order['cummulativeQuoteQty'])/float(order['executedQty']),self.qty_dec_price)
                qty = round(float(order['executedQty']),self.qty_dec_qty)
                
            bot_order = Order()
            bot_order.bot_id = self.bot_id
            bot_order.datetime = timezone.now()
            bot_order.base_asset = base_asset
            bot_order.quote_asset = quote_asset
            bot_order.side = side
            bot_order.completed = 1
            bot_order.qty = qty
            bot_order.price = price
            bot_order.orderid = order['orderId']
            bot_order.pos_order_id = completed
            bot_order.save()
                        
            return bot_order
        
        except Exception as e:
            msg_text = f'{e} '+ symbol+" "+self.client.SIDE_BUY+" "+quantity
            mylog.error(msg_text)
            return False
                

    
