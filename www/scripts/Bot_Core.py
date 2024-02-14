import scripts.functions as fn
import pandas as pd
import numpy as np
from scripts.Exchange import Exchange
import datetime as dt
from scripts.Bot_Core_utils import *
from scripts.Bot_Core_stats import *
from scripts.Bot_Core_backtest import *
from scripts.Bot_Core_live import *
from scripts.functions import round_down
import time


class Bot_Core(Bot_Core_stats,Bot_Core_backtest,Bot_Core_live):
        
    DIAS_X_MES = 30.4375 #Resulta de tomar 3 años de 365 dias + 1 de 366 / 4 años / 12 meses
    exch_comision_perc = 0.2 #0.4% - Comision por operacion de compra o venta

    signal = 'NEUTRO'
    order_id = 0

    parametros = {}

    #Trades para gestion de resultados
    _orders = {}
    df_trades_columns = ['start','buy_price','qty','end','sell_price','flag','type','days','result_usd','result_perc','orders'] 
    _trades = {}
    executed_order = False
    print_orders = False #Muestra las ordenes ejecutadas por consola

    quote_qty = 0
    interval_id = ''
    bot_id = None

    base_asset = ''
    quote_asset = ''
    qd_price = 0
    qd_qty = 0
    qd_quote = 0
    
    backtesting = True
    live = False

    exchange = None
    wallet_base = 0.0
    wallet_base_block = 0.0
    wallet_quote = 0.0
    wallet_quote_block = 0.0

    row = pd.DataFrame()

    #Gestion de data sobre ordenes buy_limit, stoploss y takeprofit 
    sl_price_data = []
    tp_price_data = []
    buy_price_data = []
    graph_open_orders = False


    def __init__(self):
        

        self.quote_qty = 0
        self.interval_id = ''
        self.bot_id = None

        self.base_asset = ''
        self.quote_asset = ''
        self.qd_price = 0
        self.qd_qty = 0
        self.qd_quote = 0
        
        self.backtesting = True
        self.exchange = None
        self.wallet_base = 0.0
        self.wallet_quote = 0.0

        self.row = pd.DataFrame()


    def set(self, parametros):
        for v in parametros:
            self.__setattr__(parametros[v]['c'], parametros[v]['v'])
    
    def __setattr__(self, prm, val):
            
        type = 'str'
        if prm in self.parametros:
            type = self.parametros[prm]['t']
            if type == 'perc' or type == 'float':
                self.__dict__[prm] = float(val)
            elif type == 'int':
                self.__dict__[prm] = int(val)
            elif type == 'bin': #Binario
                self.__dict__[prm] = 1 if int(val)>0 else 0
            else:
                self.__dict__[prm] = str(val)
        else:
            self.__dict__[prm] = val

    def valid(self):
        raise Exception(f'\n{self.__class__.__name__} Se debe establecer un metodo valid()')
        
    def start(self):
        raise Exception(f'\n{self.__class__.__name__} Se debe establecer un metodo start(df)')
    
    def next(self):
        raise Exception(f'\n{self.__class__.__name__} Se debe establecer un metodo next(df)')

    def buy(self,qty,flag):
        qty = round_down(qty,self.qd_qty)
        if self.wallet_quote >= qty*self.price and qty*self.price>=10: #Compra solo si hay wallet_quote y si el wallet_quote a comprar es > 10 USD
            self.order_id += 1
            order = Order(self.order_id,Order.TYPE_MARKET,self.row['datetime'],Order.SIDE_BUY,qty,self.price,flag)
            self._orders[order.id] = order
            if self.execute_order(order.id):
                return order.id
        return 0

    def sell(self,qty,flag):
        qty = round_down(qty,self.qd_qty)
        if self.wallet_base >= qty and qty*self.price>=10: #Vende solo si hay wallet_quote y si el wallet_quote a comprar es > 10 USD
            self.order_id += 1
            order = Order(self.order_id,Order.TYPE_MARKET,self.row['datetime'],Order.SIDE_SELL,qty,self.price,flag)
            self._orders[order.id] = order
            if self.execute_order(order.id): 
                return order.id
        return 0
        
    def sell_limit(self,qty,flag,limit_price):
        qty = round(qty,self.qd_qty)
        if self.wallet_base < qty:
            qty = round_down(qty,self.qd_qty)
        if self.wallet_base >= qty and qty*limit_price>=10: #Vende solo si hay wallet_quote y si el wallet_quote a comprar es > 10 USD
            self.order_id += 1
            limit_price = round(limit_price,self.qd_price)
            order = Order(self.order_id,Order.TYPE_LIMIT,self.row['datetime'],Order.SIDE_SELL,qty,limit_price,flag)
            self._orders[order.id] = order
            return order.id
        return 0  
    
    def buy_limit(self,qty,flag,limit_price):
        qty = round_down(qty,self.qd_qty)
        if self.wallet_quote >= qty*self.price and qty*limit_price>=10: #Compra solo si hay wallet_quote y si el wallet_quote a comprar es > 10 USD
            self.order_id += 1
            limit_price = round(limit_price,self.qd_price)
            order = Order(self.order_id,Order.TYPE_LIMIT,self.row['datetime'],Order.SIDE_BUY,qty,limit_price,flag)
            self._orders[order.id] = order
            return order.id
        return 0    
    
    def sell_trail(self,qty,flag,limit_price,activation_price,trail_perc):
        
        qty = round(qty,self.qd_qty)
        if self.wallet_base >= qty and qty*limit_price>=10: #Vende solo si hay wallet_quote y si el wallet_quote a comprar es > 10 USD
            self.order_id += 1
            order = Order(self.order_id,Order.TYPE_TRAILING,self.row['datetime'],Order.SIDE_SELL,qty,limit_price,flag)
            order.activation_price = activation_price
            order.trail_perc = trail_perc
            self._orders[order.id] = order
            return order.id
        return 0    
    
    def buy_trail(self,qty,flag,limit_price,activation_price,trail_perc):
        
        qty = round(qty,self.qd_qty)
        if self.wallet_quote >= qty*limit_price and qty*limit_price>=10: #Compra solo si hay wallet_quote y si el wallet_quote a comprar es > 10 USD
            self.order_id += 1
            order = Order(self.order_id,Order.TYPE_TRAILING,self.row['datetime'],Order.SIDE_BUY,qty,limit_price,flag)
            order.activation_price = activation_price
            order.trail_perc = trail_perc
            self._orders[order.id] = order
            return order.id

        return 0    
          
    def close(self,flag): #Vende el total existente en self.wallet_base
        self.order_id += 1
        qty = self.wallet_base
        if qty > 0:
            order = Order(self.order_id,Order.TYPE_MARKET,self.row['datetime'],Order.SIDE_SELL,qty,self.price,flag)
            self._orders[order.id] = order
            if self.execute_order(order.id):
                return order.id
        return 0
        
    def cancel_order(self,orderid):
        if orderid in self._orders:
            del self._orders[orderid]
        
    def cancel_orders(self):
        self._orders = {}
    
    def is_order(self,orderid):
        if orderid in self._orders:
            return True
        return False
    
    def is_trade(self,orderid):
        if orderid in self._trades:
            return True
        return False
    
    def order_status(self,orderid):
        if self.is_order(orderid):
            return Order.STATE_NEW
        if self.is_trade(orderid):
            return Order.STATE_COMPLETE
        return Order.STATE_CANCEL
    
    def get_order(self,orderid):
        if orderid in self._orders:
            return self._orders[orderid]
        if orderid in self._trades:
            return self._trades[orderid]
        return None

    def check_orders(self):
        if self.backtesting and not self.live:
            return self.backtest_check_orders()
        if not self.backtesting and self.live:
            return self.live_check_orders()
        raise "No se ha definido el entorno de operacion (Live/Backtest)"


    def execute_order(self,orderid):
        #if self.backtesting and not self.live:
        #    return self.backtest_execute_order(orderid)
        #if not self.backtesting and self.live:
        #    return self.live_execute_order(orderid)
        #raise "No se ha definido el entorno de operacion (Live/Backtest)"
        if not( orderid in self._orders):
            raise "La orden a ejecutar no existe en la lista de ordenes abiertas"

        order = self._orders[orderid]
        order.price = order.limit_price
        order.datetime = self.datetime  
        if order.type == Order.TYPE_TRAILING and not order.active:
            order.type = Order.TYPE_LIMIT
        
        if self.print_orders:
            if order.side == Order.SIDE_SELL:
                print(f'\033[31m{order}\033[0m',end=' -> ')
            else:
                print(f'\033[32m{order}\033[0m',end=' -> ')

        execute = False
        if order.side == Order.SIDE_BUY:
            quote_to_sell = round(order.qty*order.price,self.qd_quote)
            comision = round(quote_to_sell*(self.exch_comision_perc/100),4)
            new_wallet_base = round(self.wallet_base + order.qty,self.qd_qty)
            new_wallet_quote = round(self.wallet_quote - quote_to_sell ,self.qd_quote)
            if new_wallet_base >= 0 and new_wallet_quote >= 0:
                self.wallet_base = new_wallet_base 
                self.wallet_quote = round(new_wallet_quote - comision,self.qd_quote)
                execute = True

        elif order.side == Order.SIDE_SELL:
            quote_to_buy = round(order.qty*order.price,self.qd_quote)
            comision = round(quote_to_buy*(self.exch_comision_perc/100),4)
            new_wallet_base = round(self.wallet_base - order.qty,self.qd_qty)
            new_wallet_quote = round(self.wallet_quote + quote_to_buy,self.qd_quote)
            if new_wallet_base >= 0 and new_wallet_quote >= 0:
                self.wallet_base = new_wallet_base
                
                #Cuando se ejecuta una venta, ajusta el saldo para evitar errores de decimales
                if self.wallet_base*self.price < 2:
                    self.wallet_base = 0
                self.wallet_quote = round(new_wallet_quote - comision,self.qd_quote)
                execute = True

        del self._orders[orderid] 
        if execute:
            
            self._trades[order.id] = order
            if self.print_orders:
                print(f' {self.wallet_base} {self.wallet_quote} \033[32mOK\033[0m')
            self.on_order_execute()

        else:
            if self.print_orders:
                print(f' {self.wallet_base} {self.wallet_quote} \033[31mCANCELED\033[0m')
        
        
        return execute        
    
    def on_order_execute(self):
        #Metodo que se 
        pass


