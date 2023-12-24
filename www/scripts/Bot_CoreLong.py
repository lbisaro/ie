from bot.model_kline import *
import pandas as pd
from scripts.Bot_Core import Bot_Core
from scripts.functions import round_down

class Bot_CoreLong(Bot_Core):

    symbol = ''
    quote_perc = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    interes = ''

    def __init__(self):
        self.symbol = ''
        self.quote_perc = 0.0
        self.stop_loss = 0.0
        self.take_profit = 0.0
        self.interes = ''        

    descripcion = 'Bot Core v2 \n'\
                  'Ejecuta la compra al recibir una señal de Compra, '\
                  'y cierra la operación por Stop Loss o Take Profit (Si se definen con un % mayor a cero) '\
                  'o cuando recibe una señal de Venta.'
    
    parametros = {'symbol':  {  
                        'c' :'symbol',
                        'd' :'Par',
                        'v' :'BTCUSDT',
                        't' :'symbol',
                        'pub': True,
                        'sn':'Sym',},
                 'quote_perc': {
                        'c' :'quote_perc',
                        'd' :'Operacion sobre capital',
                        'v' :'100',
                        't' :'perc',
                        'pub': True,
                        'sn':'Quote', },
                'stop_loss': {
                        'c' :'stop_loss',
                        'd' :'Stop Loss',
                        'v' :'2',
                        't' :'perc',
                        'pub': True,
                        'sn':'SL', },
                'take_profit': {
                        'c' :'take_profit',
                        'd' :'Take Profit',
                        'v' :'0',
                        't' :'perc',
                        'pub': True,
                        'sn':'TP', },
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
        if self.quote_perc <= 0 or self.quote_perc > 100:
            err.append("El Porcentaje de capital por operacion debe ser un valor entre 0.01 y 100")
        if self.stop_loss < 0 or self.stop_loss > 100:
            err.append("El Stop Loss debe ser un valor entre 0 y 100")
        if self.take_profit < 0 or self.take_profit > 100:
            err.append("El Take Profit debe ser un valor entre 0 y 100")
        if self.interes != 'c' and self.interes != 's':
            err.append("Se debe establecer el tipo de interes. (Simple o Compuesto)")

        if len(err):
            raise Exception("\n".join(err))
    
    def get_symbols(self):
        return [self.symbol]

    def execute(self,exchange,signal,price,wallet,pos_orders):
        self.backtesting = False
        json_rsp = {}
        symbol_info = exchange.get_symbol_info(self.symbol)
        self.base_asset = symbol_info['base_asset']
        self.quote_asset = symbol_info['quote_asset']
        self.qd_price = symbol_info['qty_decs_price']
        self.qd_qty = symbol_info['qty_decs_qty']
        self.qd_quote = symbol_info['qty_decs_quote']

        #Calculo del estado de la posicion actual
        base_qty = 0
        base_in_usd = 0
        quote_qty = 0
        for order in pos_orders:
            if order.completed == 0:
                json_rsp['error'] = 'Existen ordenes incompletas'
                return json_rsp
            
            order_quote = round( round(order.qty,self.qd_qty) * round(order.price,self.qd_price) , self.qd_quote)
            if order.side == self.SIDE_BUY:
                
                quote_qty -= order_quote
                base_qty += order.qty
                base_in_usd += order_quote
            else:
                quote_qty += order_quote 
                base_qty -= order.qty
                base_in_usd -= order_quote
        
        base_qty    = round(base_qty,self.qd_qty)
        base_in_usd = round(base_in_usd,self.qd_quote)
        quote_qty   = round(quote_qty,self.qd_quote)

        if base_qty > 0:
            price_calculated = base_in_usd / base_qty
            stop_loss_price = round( price_calculated - (price_calculated * ( self.stop_loss/100) ) , self.qd_price )
            take_profit_price = round( price_calculated + (price_calculated * ( self.take_profit/100) ) , self.qd_price )

        venta_por_SLTP = False
        if base_qty > 0:
            if self.stop_loss > 0 and stop_loss_price > price:
                if wallet[self.base_asset]['free'] >= base_qty:
                    qty = base_qty
                    if self.market_sell(exchange,self.symbol,qty,self.FLAG_STOPLOSS):
                        venta_por_SLTP = True
                        json_rsp['execute'] = 'CLOSE'
                    else:
                        json_rsp['error'] = 'ORDER_NOT_PLACED'
                
            if not venta_por_SLTP and self.take_profit > 0 and take_profit_price < price:
                if wallet[self.base_asset]['free'] >= base_qty:
                    qty = base_qty
                    if self.market_sell(exchange,self.symbol,qty,self.FLAG_TAKEPROFIT):
                        json_rsp['execute'] = 'CLOSE'
                    else:
                        json_rsp['error'] = 'ORDER_NOT_PLACED'
    
        if not venta_por_SLTP and signal == 'COMPRA' and quote_qty == 0:
            if self.interes == 's': #Interes Simple
                quote_to_sell = round( self.quote_qty*(self.quote_perc/100) , self.qd_quote )
            else: #Interes Compuesto
                quote_to_sell = round( self.quote_qty*(self.quote_perc/100) , self.qd_quote )   
            if wallet[self.quote_asset]['free'] >= quote_to_sell:
                qty = round( ( quote_to_sell / price ) , self.qd_qty )            
                if self.market_buy(exchange,self.symbol,qty,self.FLAG_SIGNAL):
                    json_rsp['execute'] = 'OPEN'
                else:
                    json_rsp['error'] = 'ORDER_NOT_PLACED'

        elif not venta_por_SLTP and signal == 'VENTA' and base_qty > 0:
            if wallet[self.base_asset]['free'] >= base_qty:
                qty = base_qty
                if self.market_sell(exchange,self.symbol,qty,self.FLAG_SIGNAL):
                    json_rsp['execute'] = 'CLOSE'
                else:
                    json_rsp['error'] = 'ORDER_NOT_PLACED'

        
        return json_rsp



    def next(self):
        signal = self.signal
        
        price = self.price
            
        if signal == 'COMPRA' and self.wallet_quote > 0:
            #self.kline['sB'] = self.price
            if self.interes == 's': #Interes Simple
                quote_qty = self.quote_qty if self.wallet_quote >= self.quote_qty else self.wallet_quote
                quote_to_sell = round(quote_qty*(self.quote_perc/100) , self.qd_quote )
            elif self.interes == 'c': #Interes Compuesto
                quote_to_sell = round(self.wallet_quote*(self.quote_perc/100) , self.qd_quote ) 
            
            quote_to_sell = round(quote_to_sell , self.qd_quote ) 
            
            base_to_buy = round_down((quote_to_sell/price) , self.qd_qty) 
            
            orderid_buy = self.order_market_buy(base_to_buy,self.ORD_FLAG_SIGNAL)
            if orderid_buy>0:
                if self.stop_loss:
                    stop_loss_price = round(self.price - self.price*(self.stop_loss/100) , self.qd_price)
                    orderid_sl = self.order_limit_sell(base_to_buy,stop_loss_price,self.ORD_FLAG_STOPLOSS)
                if self.take_profit:
                    take_profit_price = round(self.price + self.price*(self.take_profit/100) , self.qd_price)
                    orderid_sl = self.order_limit_sell(base_to_buy,take_profit_price,self.ORD_FLAG_TAKEPROFIT)                
            else:
                print(self.kline['datetime'],'BUY price',self.price,'USD',quote_to_sell,self.wallet_quote)
                print('ERROR')
            

        elif signal == 'VENTA' and self.wallet_base > 0:
            #self.kline['sS'] = self.price
            base_to_sell = self.wallet_base
            orderid_sell = self.order_market_sell(base_to_sell,self.ORD_FLAG_SIGNAL)
            if orderid_sell > 0:
                self.cancel_open_orders()
            else:
                print(self.kline['datetime'],'SELL price',self.price,'USD',base_to_sell*self.price)
                print('ERROR')




