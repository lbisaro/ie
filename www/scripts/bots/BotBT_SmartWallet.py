import pandas as pd
import numpy as np
from scripts.backtesting.backtesting import Strategy 
from scripts.backtesting.lib import resample_apply
from scripts.BotBTLong import BotBTLong

def SMA(values, n):
    """
    Return simple moving average of `values`, at
    each step taking into account `n` previous values.
    """
    return pd.Series(values).rolling(n).mean()

class MyStrat(Strategy):
    
    ma = 0          #Periodos para Media movil simple 
    quote_perc =  0 #% de compra inicial, para stock
    re_buy_perc = 0 #% para recompra luego de una venta
    lot_to_safe = 0 #% a resguardar si supera start_cash

    op_last_price = 0
    
    start_cash = 0.0  #Cash correspondiente a la compra inicial
    pre_start = False #Controla que en la primera vela se compren la sunidades para stock 

    def init(self):
        super().init()
    
    def next(self):
        
        price = self._broker.last_price
        avg_price = (self.data.High[-1]+self.data.Low[-1])/2

        #Compra inicial para estockearse de Monedas
        if not self.pre_start:
            size = (self._broker._cash * (self.quote_perc/100)) / price
            self.buy(size=size)
            self.start_cash = price*size
            self.pre_start = True 

        #Estrategia
        else:
            hold = self._broker.position.size*price

            if avg_price > self.data.sma[-1] and hold > self.start_cash*(1+(self.lot_to_safe/100)):
                size = (hold - self.start_cash)/price
                limit_price = price*(1-(self.re_buy_perc/100))
                self.sell(size=size)
                self.buy(size=size,limit=limit_price)

            elif avg_price < self.data.sma[-1] and hold < self.start_cash*(1-(self.lot_to_safe/100)):
                size = self._broker.position.size*(self.lot_to_safe/100)
                if size*price > 12 : #Intenta recomprar solo si la compra es por las de 12 dolares
                    self.op_last_price = avg_price
                    limit_price = price*(1-(self.re_buy_perc/100))
                    self.sell(size=size)
                    self.buy(size=size,limit=limit_price)

class BotBT_SmartWallet(BotBTLong):

    symbol = ''
    ma = 0.0
    quote_perc = 0.0
    re_buy_perc = 0.0
    lot_to_safe = 0.0
    
    descripcion = 'Bot basado en Backtesting.py \n'\
                  'Realiza una compra al inicio, \n'\
                  'Sobre la MA, Vende parcial para tomar ganancias cuando el capital es mayor a la compra inicial, \n'\
                  'Bajo la MA, Vende parcial a medida que va perdiendo capital, \n'\
                  'Luego de cada venta recompra a un valor mas bajo.'
    
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
                're_buy_perc': {
                        'c' :'re_buy_perc',
                        'd' :'Recompra luego de una venta',
                        'v' :'4',
                        't' :'perc',
                        'pub': True,
                        'sn':'Recompra', },
                'lot_to_safe': {
                        'c' :'lot_to_safe',
                        'd' :'Resguardo si supera la compra inicial',
                        'v' :'2',
                        't' :'perc',
                        'pub': True,
                        'sn':'Resguardo', },
                'ma': {
                        'c' :'ma',
                        'd' :'Periodo de la Media Simple',
                        'v' :'14',
                        't' :'int',
                        'pub': True,
                        'sn':'MA', },

                }

    def valid(self):
        err = []
        if len(self.symbol) < 1:
            err.append("Se debe especificar el Par")
        if self.quote_perc <= 0:
            err.append("El Porcentaje de capital por operacion debe ser mayor a 0")
        if self.re_buy_perc <= 0 or self.re_buy_perc > 100:
            err.append("La recompra debe ser un valor mayor a 0 y menor o igual a 100")
        if self.lot_to_safe <= 0 or self.lot_to_safe > 100:
            err.append("El Resguardo debe ser un valor mayor a 0 y menor o igual a 100")
        if self.ma <= 0:
            err.append("Se debe establecer un periodo de MA mayor a 0")
        
        if len(err):
            raise Exception("\n".join(err))
        
    def signal(self,df):
        df['sma'] = df['close'].rolling(self.ma).mean()      
        return df

    def run(self):
        return self._bt.run(quote_perc=self.quote_perc, 
                            re_buy_perc = self.re_buy_perc, 
                            lot_to_safe = self.lot_to_safe,
                            ma = self.ma,
                            )
    
    def __init__(self):
        self.addStrategy(MyStrat)
        
        
    