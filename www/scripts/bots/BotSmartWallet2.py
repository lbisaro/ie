from bot.model_kline import *
import pandas as pd
import pandas_ta as pta
from scripts.functions import round_down
from scripts.indicators import trend
from scripts.Bot_Core import Bot_Core
from scripts.Bot_Core_utils import *

class BotSmartWallet2(Bot_Core):

    symbol = ''
    ma = 0          #Periodos para Media movil simple 
    quote_perc =  0 #% de compra inicial, para stock
    re_buy_perc = 0 #% para recompra luego de una venta
    lot_to_safe = 0 #% a resguardar si supera start_cash

    op_last_price = 0
    
    start_cash = 0.0  #Cash correspondiente a la compra inicial
    pre_start = False #Controla que en la primera vela se compren la sunidades para stock 

    def __init__(self):
        self.symbol = ''
        self.quote_perc = 0.0
        self.re_buy_perc = 0.0
        self.lot_to_safe = 0.0  
    
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
                        'v' :'50',
                        't' :'perc',
                        'pub': True,
                        'sn':'Inicio', },
                'lot_to_safe': {
                        'c' :'lot_to_safe',
                        'd' :'Resguardo si supera la compra inicial',
                        'v' :'3',
                        't' :'perc',
                        'pub': True,
                        'sn':'Resguardo', },

                }

    def valid(self):
        err = []
        if len(self.symbol) < 1:
            err.append("Se debe especificar el Par")
        if self.quote_perc <= 0:
            err.append("El Porcentaje de capital por operacion debe ser mayor a 0")
        if self.lot_to_safe <= 0 or self.lot_to_safe > 100:
            err.append("El Resguardo debe ser un valor mayor a 0 y menor o igual a 100")
        
        if len(err):
            raise Exception("\n".join(err))
        
    def start(self):
        self.klines = trend(self.klines)  
        self.klines['signal'] = 'NEUTRO'   

        self.print_orders = True 
        self.graph_open_orders = True
        self.sl_order = 0
    
    def next(self):
        price = self.price
        trend_up = True if self.row['trend_up'] is not None else False
        #trend_down = True if self.row['trend_down'] > 0 else False
        
        #Ajusta la billetera inicial para estockearse de Monedas
        #No hace operacion de Buy para que se puedan interpretar las ordenes
        if not self.pre_start:
            self.start_cash = round(self.wallet_quote * (self.quote_perc/100),self.qd_quote)
            self.pre_start = True 

        #Estrategia
        else:
            

            if trend_up:
                hold = round(self.wallet_base*price,self.qd_quote)
                if hold < 10: 
                    qty = round_down(self.start_cash/self.price,self.qd_qty)
                    self.buy(qty,Order.FLAG_SIGNAL)
                    self.sl_order = 0
                    self.cancel_orders()
                elif hold > self.start_cash*(1+(self.lot_to_safe/100)):
                    qty = round_down((hold - self.start_cash)/price, self.qd_qty)
                    if (qty*self.price)< 11.0:
                        qty = round_down(11.0/price, self.qd_qty)
                    self.sell(qty,Order.FLAG_TAKEPROFIT)
                    self.sl_order = 0
                    self.cancel_orders()
                
                #Procesando stop_loss 
                sl_cash = self.start_cash*(1-((self.lot_to_safe*2)/100))
                sl_price = sl_cash/self.wallet_base
                if self.sl_order == 0:
                    self.sl_order = self.sell_limit(self.wallet_base,Order.FLAG_STOPLOSS,sl_price)

                    
            else:
                if self.wallet_base > 0:
                    self.sell(self.wallet_base,Order.FLAG_SIGNAL)
                    self.cancel_orders()

