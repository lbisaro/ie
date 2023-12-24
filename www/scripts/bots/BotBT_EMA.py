import pandas as pd
import numpy as np
from scripts.backtesting.backtesting import Strategy 
from scripts.backtesting.lib import resample_apply
from scripts.BotBTLong import BotBTLong



def NONE(values):
    return pd.Series(values)

class EmaCross(Strategy):
    
    pema = 21

    quote_qty = 0
    quote_perc = 0
    stop_loss = 0
    stop_loss_price = None
    take_profit = 0
    take_profit_price = None
    interes = ''

    orderid = 0
    
    signal = 'NEUTRO'
    
    def init(self):
        #self.pend =  self.I(NONE, self.data.ema_pend , overlay=True)
        pass
    
    def next(self):
        
        price = self._broker.last_open
        
        if self.signal == 'COMPRA' and self._broker.position.size == 0:
            
            applicable_cash = self._broker.equity
            if self.interes == 's': #interes simple
                if self._broker.equity > self.quote_qty:
                    applicable_cash = self.quote_qty
           
            size = (applicable_cash * (self.quote_perc/100)) / price

            if self.stop_loss > 0: 
                self.stop_loss_price = price * (1-(self.stop_loss/100))
            if self.take_profit > 0: 
                self.take_profit_price = price * (1+(self.take_profit/100))

            self.orderid +=1
            tag = f'ORD {self.orderid} '
            order = self.buy(size=size,tag = tag)

        if self._broker.position.size > 0:
            close = False
            if self.signal == 'VENTA':
                close_signal = BotBTLong.ORD_FLAG_SIGNAL
                close = True
            if self.stop_loss_price is not None and self.stop_loss_price > price:
                close_signal = BotBTLong.ORD_FLAG_STOPLOSS
                close = True
            if self.take_profit_price is not None and self.take_profit_price < price:
                close_signal = BotBTLong.ORD_FLAG_TAKEPROFIT
                close = True

            if close:
                self.position.close(tag=close_signal)
                self.stop_loss_price = None
                self.take_profit_price = None

        self.signal = self.data.signal[-1]

class BotBT_EMA(BotBTLong):

    def signal(self,df):
        df['ema'] = df['close'].ewm(span=16, adjust=False).mean()
        df['ema_perc'] = ((df['ema']/df['ema'].mean())-1) * 100
        df['ema_pend'] = df['ema_perc'].diff(1)
        df['ema_pend2'] = df['ema_perc'].diff(10)

        df['signal'] = np.where((df['ema_pend']>0.5) & (df['ema_pend2']>2), 'COMPRA', 'NEUTRO')
        df['signal'] = np.where(df['ema_pend']<-0.5, 'VENTA',df['signal'] ) 
        
        return df
    
    def run(self):
        return self._bt.run(stop_loss=self.stop_loss, 
                        take_profit = self.take_profit, 
                        interes = self.interes,
                        quote_perc = self.quote_perc,
                        quote_qty = self.quote_qty,
                        )
    
    def __init__(self):
        self.addStrategy(EmaCross)
        
        
    