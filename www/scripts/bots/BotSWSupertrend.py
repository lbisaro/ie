from bot.model_kline import *
import pandas as pd
import numpy as np
from scripts.functions import round_down
from scripts.indicators import supertrend
from scripts.Bot_Core import Bot_Core
from scripts.Bot_Core_utils import *

class BotSWSupertrend(Bot_Core):

    symbol = ''
    ma = 0          #Periodos para Media movil simple 
    quote_perc =  0 #% de compra inicial, para stock
    re_buy_perc = 0 #% para recompra luego de una venta
    lot_to_safe = 0 #% a resguardar si supera start_cash
    re_buy_perc = 0 #% para recompra luego de una venta

    op_last_price = 0
    
    start_cash = 0.0  #Cash correspondiente a la compra inicial
    pre_start = False #Controla que en la primera vela se compren la sunidades para stock 

    def __init__(self):
        self.symbol = ''
        self.quote_perc = 0.0
        self.lot_to_safe = 0.0
        self.re_buy_perc = 0.0  
    
    descripcion = 'Bot de Balanceo de Billetera \n'\
                  ' \n'\
                  'Con tendencia alcista, Realiza una compra al inicio, y Vende parcial para tomar ganancias cuando el capital es mayor a la compra inicial, \n'\
                  'Con tendencia bajista, Vende el total'
    
    parametros = {'symbol':  {  
                        'c' :'symbol',
                        'd' :'Par',
                        'v' :'BTCUSDT',
                        't' :'symbol',
                        'pub': True,
                        'sn':'Par',},
                'quote_perc': {
                        'c' :'quote_perc',
                        'd' :'Compra inicial para stock',
                        'v' :'100',
                        't' :'perc',
                        'pub': True,
                        'sn':'Inicio', },
                'lot_to_safe': {
                        'c' :'lot_to_safe',
                        'd' :'Resguardo si supera la compra inicial',
                        'v' :'2',
                        't' :'perc',
                        'pub': True,
                        'sn':'Resguardo', },
                're_buy_perc': {
                        'c' :'re_buy_perc',
                        'd' :'Recompra luego de una venta',
                        'v' :'2',
                        't' :'perc',
                        'pub': True,
                        'sn':'Recompra', },

                }

    def valid(self):
        err = []
        if len(self.symbol) < 1:
            err.append("Se debe especificar el Par")
        if self.quote_perc <= 0:
            err.append("El Porcentaje de capital por operacion debe ser mayor a 0")
        if self.lot_to_safe <= 0 or self.lot_to_safe > 100:
            err.append("El Resguardo debe ser un valor mayor a 0 y menor o igual a 100")
        if self.re_buy_perc < 0 or self.re_buy_perc > 100:
            err.append("La recompra debe ser un valor mayor o igual a 0 y menor o igual a 100")
        
        if len(err):
            raise Exception("\n".join(err))
        
    def start(self):
        self.klines = supertrend(self.klines)  
        self.klines['signal'] = np.where(self.klines['st_trigger']>1 , 'COMPRA' , 'NEUTRO')  
        self.klines['signal'] = np.where(self.klines['st_trigger']<0 , 'VENTA'  , self.klines['signal']) 
        self.print_orders = False 
        self.graph_open_orders = False
        
        self.start_cash = round(self.wallet_quote * (self.quote_perc/100),self.qd_quote)
   
    
    def next(self):
        price = self.price

        hold = round(self.wallet_base*price,self.qd_quote)
        
        if hold < 10 and (self.signal == 'COMPRA' or self.row['st_trend'] > 0 ):
            cash = self.start_cash if self.start_cash <= self.wallet_quote else self.wallet_quote
            qty = round_down(cash/self.price,self.qd_qty)
            self.buy(qty,Order.FLAG_SIGNAL)
            self.sl_order = 0

                
        elif self.signal == 'VENTA':
            self.close(Order.FLAG_SIGNAL)
            self.cancel_orders()


        elif hold > self.start_cash*(1+(self.lot_to_safe/100)):
            qty = round_down(((hold - self.start_cash)/price), self.qd_qty)
            if (qty*self.price)< 11.0:
                qty = round_down(11.0/price, self.qd_qty)
            self.sell(qty,Order.FLAG_TAKEPROFIT)
            if self.re_buy_perc > 0:
                limit_price = price*(1-(self.re_buy_perc/100))
                self.buy_limit(qty,Order.FLAG_TAKEPROFIT,limit_price)