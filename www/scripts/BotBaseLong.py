from bot.model_kline import *
from django.db.models import Q
import pandas as pd
import numpy as np
import time
from scripts.Exchange import Exchange
from scripts.BotBase import BotBase
from django.utils import timezone

class BotBaseLong(BotBase):

    symbol = ''
    quote_perc = 0.0
    stop_loss = 0.0
    take_profit = 0.0

    VELAS_PREVIAS = 100

    descripcion = 'Opera en largo \n'\
                  'Ejecuta la compra al recibir una señal de Compra, '\
                  'y cierra la operación por Stop Loss o Take Profit (Si se definen con un % mayor a cero) '\
                  'o cuando recibe una señal de Venta.'
    
    parametros = {'symbol':  {  
                        'c' :'symbol',
                        'd' :'Par',
                        'v' :'BTCUSDT',
                        't' :'symbol',
                        'pub': True,},
                'quote_perc': {
                        'c' :'quote_perc',
                        'd' :'Operacion sobre capital',
                        'v' :'70',
                        't' :'perc',
                        'pub': True, },
                'stop_loss': {
                        'c' :'stop_loss',
                        'd' :'Stop Loss',
                        'v' :'2',
                        't' :'perc',
                        'pub': True, },
                'take_profit': {
                        'c' :'take_profit',
                        'd' :'Take Profit',
                        'v' :'0',
                        't' :'perc',
                        'pub': True, },
                'interes': {
                        'c' :'interes',
                        'd' :'Tipo de interes',
                        'v' :'c',
                        't' :'t_int',
                        'pub': True, },
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
    
    def get_symbols(self):
        return [self.symbol]
    
    def get_signal(self):
        jsonRsp = {}
        self.backtesting = False
        
        self.klines = Kline.get_df(self.symbol, self.interval_id, limit=self.VELAS_PREVIAS)

        velas = int(self.klines['datetime'].count())
        
        if velas<self.VELAS_PREVIAS:
            jsonRsp['ok'] = False
            jsonRsp['error'] = 'El intervalo y rango de fechas solicitado genera un total de '+str(velas)+' velas'+\
                    '<br>Se requiere un minimo de '+str(self.VELAS_PREVIAS)+' velas'
        else:
            self.klines = self.signal(self.klines)
            jsonRsp['signal'] = self.klines.iloc[-1]['signal']
            jsonRsp['ok'] = True


        return jsonRsp
    
    def execute(self,exchange,signal,price,wallet,pos_orders):
        self.backtesting = False
        jsonRsp = {}
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
                jsonRsp['error'] = 'Existen ordenes incompletas'
                return jsonRsp
            
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

    
        if signal == 'COMPRA' and quote_qty == 0:
            if self.interes == 's': #Interes Simple
                quote_to_sell = round( self.quote_qty*(self.quote_perc/100) , self.qd_quote )
            else: #Interes Compuesto
                quote_to_sell = round( self.quote_qty*(self.quote_perc/100) , self.qd_quote )   
            if wallet[self.quote_asset]['free'] >= quote_to_sell:
                qty = round( ( quote_to_sell / price ) , self.qd_qty )            
                if self.market_buy(exchange,self.symbol,qty,self.FLAG_SIGNAL):
                    jsonRsp['execute'] = 'OPEN'
                else:
                    jsonRsp['error'] = 'ORDER_NOT_PLACED'

        elif signal == 'VENTA' and base_qty > 0:
            if wallet[self.base_asset]['free'] >= base_qty:
                qty = base_qty
                if self.market_sell(exchange,self.symbol,qty,self.FLAG_SIGNAL):
                    jsonRsp['execute'] = 'CLOSE'
                else:
                    jsonRsp['error'] = 'ORDER_NOT_PLACED'

        else: #Si no hay una señal de compra venta, revisa Stop-Loss y Take-Profit
            if base_qty > 0:
                if self.stop_loss > 0 and stop_loss_price > price:
                    if wallet[self.base_asset]['free'] >= base_qty:
                        qty = base_qty
                        if self.market_sell(exchange,self.symbol,qty,self.FLAG_STOPLOSS):
                            jsonRsp['execute'] = 'CLOSE'
                        else:
                            jsonRsp['error'] = 'ORDER_NOT_PLACED'
                    
                if self.take_profit > 0 and take_profit_price < price:
                    if wallet[self.base_asset]['free'] >= base_qty:
                        qty = base_qty
                        if self.market_sell(exchange,self.symbol,qty,self.FLAG_TAKEPROFIT):
                            jsonRsp['execute'] = 'CLOSE'
                        else:
                            jsonRsp['error'] = 'ORDER_NOT_PLACED'
        
        return jsonRsp
    
    def backtesting(self,from_date,to_date):
        func_start = timezone.now()
        self.reset_res()
        self.reset_pos()
        self.backtesting = True


        exch = Exchange(type='info',exchange='bnc',prms=None)
        symbol_info = exch.get_symbol_info(self.symbol)
        self.base_asset = symbol_info['base_asset']
        self.quote_asset = symbol_info['quote_asset']
        self.qd_price = symbol_info['qty_decs_price']
        self.qd_qty = symbol_info['qty_decs_qty']
        self.qd_quote = symbol_info['qty_decs_quote']

        start = time.time()
        self.klines = Kline.get_df(self.symbol, self.interval_id, from_date=from_date, to_date=to_date)
        print('class: BotBaseLong.backtesting() - Kline OK',(timezone.now()-func_start))
        
        end = time.time()
        duration = end-start
        self.res['duration_klines'] = round(duration,2)
        start = time.time()

        velas = int(self.klines['datetime'].count())

        if velas<50:
            self.res['ok'] = False
            self.res['error'] = 'El intervalo y rango de fechas solicitado genera un total de '+str(velas)+' velas'+\
                    '<br>Se requiere un minimo de '+str(self.VELAS_PREVIAS)+' velas para poder realizar el Backtesting'
            return self.res
        
        self.wallet_base = 0.0
        self.wallet_quote = self.quote_qty

        self.res['symbol'] = self.symbol
        self.res['from'] = from_date+' 00:00'
        self.res['to'] = to_date+' 23:59'
        self.res['periods'] = velas
        self.res['base_asset'] = self.wallet_base
        self.res['quote_asset'] = self.wallet_quote
        self.res['qd_price'] = self.qd_price
        self.res['qd_qty'] = self.qd_qty
        self.res['qd_quote'] = self.qd_quote
        
        #Aplicar la señal de compra/venta
        self.klines = self.signal(self.klines)

        #Calculando HOLD para comparar contra la operacion
        # El hold es la compra del capital a invertir al precio open al inicio + el saldo que queda en USD 
        quote_to_hold = round( self.quote_qty*(self.quote_perc/100) , self.qd_quote )
        price_to_hold = float(self.klines.loc[0]['open'])
        qty_to_hold = round( ( quote_to_hold / price_to_hold ) , self.qd_qty ) 
        usd_in_hold = round( self.quote_qty - quote_to_hold , self.qd_quote )

        for i,kline in self.klines.iterrows():
            k_open = float(kline['open'])
            k_high = float(kline['high'])
            k_low = float(kline['low'])
            k_close = float(kline['close'])

            k_sig_buy = k_low if kline['signal'] == 'COMPRA' else None
            k_sig_sell = k_high if kline['signal'] == 'VENTA' else None
            
            timestamp = pd.Timestamp(kline['datetime']).timestamp()
            unix_dt = int( (timestamp*1000) +  10800000 ) #Convierte a milisegundos y agrega 3 horas 
            data = {'dt': unix_dt,
                    'o': kline['open'],
                    'h': kline['high'],
                    'l': kline['low'],
                    'c': kline['close'],
                    'v': kline['volume'],
                    'uH': 0.0,
                    'uW': 0.0,
                    'dd': 0.0,
                }
            
            if k_sig_buy:
                data['sB'] = k_sig_buy
            if k_sig_sell:
                data['sS'] = k_sig_sell
            
            self.bt_index = pd.to_datetime(self.klines.iloc[i]['datetime']).strftime('%Y-%m-%d %H:%M')
             
            signal = self.klines.iloc[i-1]['signal']
            
            if signal == 'COMPRA' and self.wallet_base == 0:
                
                if self.interes == 's': #Interes Simple
                    quote_to_sell = round( self.quote_qty*(self.quote_perc/100) , self.qd_quote )
                elif self.interes == 'c': #Interes Compuesto
                    quote_to_sell = round( self.wallet_quote*(self.quote_perc/100) , self.qd_quote )

                price = k_open
                qty = round( ( quote_to_sell / price ) , self.qd_qty )
                if self.bt_order_market_buy(qty,price,self.FLAG_SIGNAL):
                    data['by'] = price
                    data['fl'] = 'Signal'
               
            elif signal == 'VENTA' and self.wallet_base > 0:
                qty = self.wallet_base
                price = k_open

                if self.bt_order_market_sell(qty,price,self.FLAG_SIGNAL):
                    data['sls'] = price
                    data['fl'] = 'Signal'
            
            else:
                if self.stop_loss_price:
                    if k_low < self.stop_loss_price:
                        qty = self.wallet_base
                        price = self.stop_loss_price

                        if self.bt_order_market_sell(qty,price,self.FLAG_STOPLOSS):
                            data['slsl'] = price
                            data['fl'] = 'Stop Loss'

                if self.take_profit_price:
                    if k_high > self.take_profit_price:
                        qty = self.wallet_base
                        price = self.take_profit_price

                        if self.bt_order_market_sell(qty,price,self.FLAG_TAKEPROFIT):
                            data['sltp'] = price
                            data['fl'] = 'Take Profit'

            if self.stop_loss_price:
                data['SL'] = round( self.stop_loss_price, self.qd_price) 
            if self.take_profit_price:
                data['TP'] = round( self.take_profit_price, self.qd_price) 
            data['uH'] = round( (qty_to_hold * k_open)      + usd_in_hold      , self.qd_quote )
            data['uW'] = round( (self.wallet_base * k_open) + self.wallet_quote, self.qd_quote )
            
            self.update_pos(k_low,k_high)
            self.res['data'].append(data)

        end = time.time()
        duration = end-start
        self.res['duration_proc'] = round(duration,2)

        self.res['brief'] = self.get_brief()


        print('class: BotBaseLong.backtesting() - End',(timezone.now()-func_start))
                        
        return self.res

    def signal(self,df):
        
        #df['signal'] puede devolver NEUTRO, COMPRA o VENTA
        df['signal'] = 'NEUTRO'
        
        return df


