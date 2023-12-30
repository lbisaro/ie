from bot.model_kline import *
import pandas as pd
from scripts.Exchange import Exchange
from scripts.Bot_Core import Bot_Core
import datetime as dt
from scripts.functions import round_down

class BotMartingala(Bot_Core):

    symbol = ''
    qty_pos = 0.0
    mult_pos = 0.0
    mult_perc = 0.0
    stop_loss = 0.0
    take_profit = 0.0

    descripcion = 'Bot Core v2 \n'\
                  'Bot de Martingala.'
        
    parametros = {'symbol':  {  
                        'c' :'symbol',
                        'd' :'Par',
                        'v' :'BTCUSDT',
                        't' :'symbol',
                        'pub': True,
                        'sn':'Sym',},
                 'qty_pos': {
                        'c' :'qty_pos',
                        'd' :'Cantidad de posiciones',
                        'v' :'5',
                        't' :'int',
                        'pub': True,
                        'sn':'Pos', },
                 'mult_pos': {
                        'c' :'mult_pos',
                        'd' :'Multiplicador de compra',
                        'v' :'2',
                        't' :'float',
                        'pub': True,
                        'sn':'Mult.Pos', },
                 'mult_perc': {
                        'c' :'mult_perc',
                        'd' :'Multiplicador Porcentaje',
                        'v' :'0.5',
                        't' :'float',
                        'pub': True,
                        'sn':'Mult.Perc', },
                'take_profit': {
                        'c' :'take_profit',
                        'd' :'Take Profit',
                        'v' :'1',
                        't' :'perc',
                        'pub': True,
                        'sn':'TP', },
                 'stop_loss': {
                        'c' :'stop_loss',
                        'd' :'Stop Loss',
                        'v' :'4',
                        't' :'perc',
                        'pub': True,
                        'sn':'SL', },

                }
    
    #Datos correspondientes a la posicion
    qty_compras = 0
    buy_orderid = 0
    sell_bt_orderid = 0
    sell_tp_orderid = 0
    stop_loss_over_quote = 0
    pos_buy_history = []

    def valid(self):
        err = []
        if len(self.symbol) < 1:
            err.append("Se debe especificar el Par")
        if self.qty_pos <= 2 or self.qty_pos > 10:
            err.append("La cantidad de posiciones debe ser un valor entre 2 y 10")
        if self.mult_pos < 1 or self.mult_pos > 5:
            err.append("Multiplicador de compra debe ser un valor entre 1 y 5")
        if self.mult_perc <= 0 or self.mult_perc > 10:
            err.append("Multiplicador de porcentaje debe ser un valor entre 0.01 y 10")
        if self.stop_loss < 0 or self.stop_loss > 100:
            err.append("El Stop Loss debe ser un valor entre 0 y 100")
        if self.take_profit < 0 or self.take_profit > 100:
            err.append("El Take Profit debe ser un valor entre 0 y 100")
        
        if len(err):
            raise Exception("\n".join(err))
    
    def get_symbols(self):
        return [self.symbol]

    def calculate_pos(self,quote, qty_pos, mult):
        pos = []
        for i in range(qty_pos):
            pos_amount = quote * (1 - (1 / mult)) / (1 - 1 / mult**(qty_pos - i))
            pos.append(round(pos_amount, 2))
            quote -= pos_amount
        return pos[::-1]  # Invierte la lista
    
    def start(self,df):
        df['signal'] = 'NEUTRO'
        return df
    
    def reset_pos(self):
        self.buy_orderid = 0
        self.sell_tp_orderid = 0
        self.sell_sl_orderid = 0
        self.qty_compras = 0
        self.stop_loss_over_quote = 0
        self.pos_buy_history = []

    def next(self):
         
        price = self.price

        if self.qty_compras == 0:  #Inicia la posicion
            self.quote_pos = self.calculate_pos((self.wallet_quote*0.99), self.qty_pos, self.mult_pos)
            
            quote_to_sell = round(self.quote_pos[0] , self.qd_quote ) 
            base_to_buy = round_down((quote_to_sell/price) , self.qd_qty) 
            buy_orderid = self.buy(base_to_buy,self.ORD_FLAG_SIGNAL)
            if buy_orderid>0:
                self.pos_buy_history.append({'base': base_to_buy,
                                             'price': self.price,
                                             'quote': base_to_buy*self.price,})
                self.qty_compras = 1
                
                if self.stop_loss:
                    self.stop_loss_over_quote = self.wallet_quote * (self.stop_loss/100)
                    if self.stop_loss_over_quote < quote_to_sell:
                        stop_loss_quote = quote_to_sell-self.stop_loss_over_quote
                        stop_loss_price = round(stop_loss_quote/base_to_buy , self.qd_price)
                        self.sell_sl_orderid = self.order_limit_sell(base_to_buy,stop_loss_price,self.ORD_FLAG_STOPLOSS)
                
                take_profit_price = round(self.price + self.price*(self.take_profit/100) , self.qd_price)
                self.sell_tp_orderid = self.order_limit_sell(base_to_buy,take_profit_price,self.ORD_FLAG_TAKEPROFIT)                

                palanca_price = round(self.price - self.price*(self.mult_perc/100),self.qd_price)
                quote_to_sell = round(self.quote_pos[1] , self.qd_quote ) 
                base_to_buy = round_down((quote_to_sell/price) , self.qd_qty) 
                self.buy_orderid = self.order_limit_buy(base_to_buy,palanca_price,self.ORD_FLAG_SIGNAL) 
                
        if self.check_open_orders(): #Devuelve True si se ejecuto alguna orden abierta (Limit o Trail)
                
            #Venta por stop-loss
            if self.is_order(self.sell_sl_orderid):
                if self.is_order_completed(self.sell_sl_orderid):
                    self.cancel_open_orders()
                    self.reset_pos()
            
            #Venta por take-profit
            if self.is_order(self.sell_tp_orderid):
                if self.is_order_completed(self.sell_tp_orderid):
                    self.cancel_open_orders()
                    self.reset_pos()
            
            #Compra
            if self.is_order(self.buy_orderid):
                if self.is_order_completed(self.buy_orderid):
                    self.cancel_open_orders()

                    last_buy_order = self.get_order(self.buy_orderid)

                    self.pos_buy_history.append({'base': last_buy_order['qty'],
                                'price': last_buy_order['price'],
                                'quote': last_buy_order['qty']*last_buy_order['price'],})
                    
                    base_buyed = 0
                    quote_buyed = 0
                    for buy in self.pos_buy_history:
                        base_buyed += buy['base']
                        quote_buyed += buy['quote']

                    if base_buyed>0:
                        
                        take_profit_quote = round(quote_buyed+quote_buyed*(self.take_profit/100), self.qd_quote)
                        take_profit_price = round(take_profit_quote/base_buyed , self.qd_price)
                        self.sell_tp_orderid = self.order_limit_sell(base_buyed,take_profit_price,self.ORD_FLAG_TAKEPROFIT)                
                    
                    if self.stop_loss:
                        if self.stop_loss_over_quote < quote_buyed:
                            stop_loss_quote = quote_buyed-self.stop_loss_over_quote
                            stop_loss_price = round(stop_loss_quote/base_buyed , self.qd_price)
                            self.sell_sl_orderid = self.order_limit_sell(base_buyed,stop_loss_price,self.ORD_FLAG_STOPLOSS)

                    palanca_price = round(last_buy_order['price']*(1-((self.mult_perc*self.qty_compras)/100)),self.qd_price)
                    if self.qty_compras<self.qty_pos:
                        quote_to_sell = round(self.quote_pos[self.qty_compras] , self.qd_quote ) 
                        base_to_buy = round_down((quote_to_sell/price) , self.qd_qty) 
                        self.buy_orderid = self.order_limit_buy(base_to_buy,palanca_price,self.ORD_FLAG_SIGNAL) 
                    
                    self.qty_compras += 1
                    
        return round(self.wallet_base*price + self.wallet_quote,2)


