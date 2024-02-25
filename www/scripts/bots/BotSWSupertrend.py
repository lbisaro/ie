import pandas as pd
import numpy as np
from scripts.functions import round_down
from scripts.indicators import supertrend, volume_level
from scripts.Bot_Core import Bot_Core
from scripts.Bot_Core_utils import Order
from django.utils import timezone as dj_timezone
import datetime as dt


class BotSWSupertrend(Bot_Core):

    symbol = ''
    ma = 0          #Periodos para Media movil simple 
    quote_perc =  0 #% de compra inicial, para stock
    re_buy_perc = 0 #% para recompra luego de una venta
    lot_to_safe = 0 #% a resguardar si supera start_cash
    re_buy_perc = 0 #% para recompra luego de una venta
    interes = '' 

    
    def __init__(self):
        self.symbol = ''
        self.quote_perc = 0.0
        self.lot_to_safe = 0.0
        self.re_buy_perc = 0.0  
        self.interes = '' 
    
    descripcion = 'Bot de Balanceo de Billetera \n'\
                  'Con tendencia alcista, Realiza una compra al inicio, y Vende parcial para tomar ganancias cuando el capital es mayor a la compra inicial, \n'\
                  'Con tendencia bajista, Vende el total.'
    
    parametros = {'symbol':  {  
                        'c' :'symbol',
                        'd' :'Par',
                        'v' :'BTCUSDT',
                        't' :'symbol',
                        'pub': True,
                        'sn':'Par',},
                'quote_perc': {
                        'c' :'quote_perc',
                        'd' :'Compra inicial',
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
                'interes': {
                        'c' :'interes',
                        'd' :'Tipo de interes',
                        'v' :'c',
                        't' :'t_int',
                        'pub': True,
                        'sn':'Int', },

                }

    def valid(self):
        err = []
        if len(self.symbol) < 1:
            err.append("Se debe especificar el Par")
        if self.quote_perc <= 0:
            err.append("El Porcentaje de capital por operacion debe ser mayor a 0")
        if self.lot_to_safe < 0 or self.lot_to_safe > 100:
            err.append("El Resguardo debe ser un valor mayor o igual a 0 y menor o igual a 100")
        if self.re_buy_perc < 0 or self.re_buy_perc > 100:
            err.append("La recompra debe ser un valor mayor o igual a 0 y menor o igual a 100")
        
        if len(err):
            raise Exception("\n".join(err))
    
    def get_status(self):
        status_datetime = dt.datetime.now()
        status = super().get_status()
        if 'st_trend' in self.row:
            if self.row['st_trend'] > 0:
                tendencia = 'Alcista '+status_datetime.strftime('%d-%m-%Y %H:%M')
                cls = 'text-success'
            elif self.row['st_trend'] < 0:
                tendencia = 'Bajista '+status_datetime.strftime('%d-%m-%Y %H:%M')
                cls = 'text-danger'
            else:
                tendencia = 'Neutral '+status_datetime.strftime('%d-%m-%Y %H:%M')
                cls = 'text-secondary'
            status['trend'] = {'l': 'Tendencia','v': tendencia, 'r': self.row['st_trend'], 'cls': cls}

        if self.signal != 'NEUTRO':
            if self.signal == 'COMPRA':
                cls = 'text-success'
            else: 
                cls = 'text-danger'
            status['signal'] = {'l': 'Ultima señal','v': self.signal+' '+status_datetime.strftime('%d-%m-%Y %H:%M'), 'r': self.signal, 'cls': cls}
        return status
        
        
    def start(self):
        self.klines = supertrend(self.klines)  
        #self.klines = volume_level(self.klines,period=200)  
        
        self.klines['signal'] = np.where((self.klines['st_trigger']>0) , 'COMPRA' , 'NEUTRO')  #& (self.klines['vol_signal']>0)
        self.klines['signal'] = np.where((self.klines['st_trigger']<0)  , 'VENTA'  , self.klines['signal'])  #& (self.klines['vol_signal']<0)

        self.klines['ma'] = self.klines['close'].rolling(window=150).mean()

        self.print_orders = False 
        self.graph_open_orders = False
        self.graph_signals = False

    def on_order_execute(self,order):
        if order.side == Order.SIDE_SELL and order.flag == Order.FLAG_SIGNAL:
            self.cancel_orders()
    
    def next(self):
        start_cash = round(self.quote_qty * (self.quote_perc/100),self.qd_quote)
        price = self.price

        hold = round(self.wallet_base*price,self.qd_quote)
        
        """
        La linea
            if 'st_trend' in self.row
        Representa que entro en next, cuando aplicaba el check de la señal de acuerdo al timeframe aplicable

        """
        if 'st_trend' in self.row and hold < 10 and (self.signal == 'COMPRA' or self.row['st_trend'] > 0 ):
            
            if self.interes == 's': #Interes Simple
                cash = start_cash if start_cash <= self.wallet_quote else self.wallet_quote
            else: #Interes Compuesto
                cash = self.wallet_quote

            qty = round_down(cash/self.price,self.qd_qty)
            buy_order_id = self.buy(qty,Order.FLAG_SIGNAL)
            buy_order = self.get_order(buy_order_id)
            buy_order.tag = 'ma_'+str(self.row['ma'])
                
        elif 'st_trend' in self.row and hold > 10 and self.signal == 'VENTA': 
            self.close(Order.FLAG_SIGNAL)
            
        else:
            if self.lot_to_safe > 0 and hold > start_cash*(1+(self.lot_to_safe/100)):
                qty = round_down(((hold - start_cash)/price) , self.qd_qty)
                if (qty*self.price) < 15.0:
                    qty = round_down(15.0/price, self.qd_qty)
                sell_order_id = self.sell(qty,Order.FLAG_TAKEPROFIT)
                
                if sell_order_id > 0:
                    if self.re_buy_perc > 0:
                        sell_order = self.get_order(sell_order_id)
                        limit_price = round(sell_order.price*(1-(self.re_buy_perc/100)),self.qd_price)
                        self.buy_limit(qty,Order.FLAG_TAKEPROFIT,limit_price)            