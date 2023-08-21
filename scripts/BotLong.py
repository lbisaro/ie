from .BotBase import BotBase
from bot.model_kline import *
from django.db.models import Q
import pandas as pd
import datetime

class BotLong(BotBase):

    symbol = ''
    quote_perc = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    
    parametros = {'symbol':  {  
                        'c' :'symbol',
                        'd' :'Symbol',
                        'v' :'BTCUSDT',
                        't' :'symbol'},
                'quote_perc': {
                        'c' :'quote_perc',
                        'd' :'Porcentaje de capital por operacion',
                        'v' :'70',
                        't' :'perc' },
                
                'stop_loss': {
                        'c' :'stop_loss',
                        'd' :'Stop Loss',
                        'v' :'2',
                        't' :'perc' },
                'take_profit': {
                        'c' :'take_profit',
                        'd' :'Take Profit',
                        'v' :'6',
                        't' :'perc' },
                }

    def valid(self):
        err = []
        if len(self.symbol) < 1:
            err.append("Se debe especificar el Par")
        if self.quote_perc <= 0:
            err.append("El Porcentaje de capital por operacion debe ser mayor a 0")
        if self.stop_loss < 0 or self.stop_loss > 100:
            err.append("El Stop Loss debe ser un valor entre 0 y 100")
        if self.take_profit < 0 or self.take_profit > 100:
            err.append("El Take Profit debe ser un valor entre 0 y 100")
        
        if len(err):
            raise Exception("\n".join(err))
        

    def start(self):
        super().start()
        if self.valid():
            return True
    
    def run(self):
        print('El bot en RUN') 
        pass

    def backtesting(self):
        klines = Kline.get_df(self.symbol, self.interval_id, 200)
        
         
        
        print(klines)


    def get_symbols(self):
        return [self.symbol]

