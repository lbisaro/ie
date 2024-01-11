from bot.model_kline import *
import pandas as pd
import time
from scripts.Exchange import Exchange
from scripts.BotBase import BotBase
from django.utils import timezone
from scripts.functions import round_down

class BotBaseLong(BotBase):

    symbol = ''
    quote_perc = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    stop_loss_price = None
    take_profit_price = None

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
        if self.quote_perc <= 0:
            err.append("El Porcentaje de capital por operacion debe ser mayor a 0")
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
    
    def get_signal(self):
        json_rsp = {}
        self.backtesting = False
        
        self.klines = Kline.get_df(self.symbol, self.interval_id, limit=self.VELAS_PREVIAS)

        velas = int(self.klines['datetime'].count())
        
        if velas<self.VELAS_PREVIAS:
            json_rsp['ok'] = False
            json_rsp['error'] = 'El intervalo y rango de fechas solicitado genera un total de '+str(velas)+' velas'+\
                    '<br>Se requiere un minimo de '+str(self.VELAS_PREVIAS)+' velas'
        else:
            self.klines = self.signal(self.klines)
            json_rsp['signal'] = self.klines.iloc[-1]['signal']
            json_rsp['ok'] = True


        return json_rsp
    
    def execute_live(self,exchange,signal,price,wallet,pos_orders):
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
    
    def backtest(self,klines,from_date,to_date,to_get='complete'):
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
        self.klines = klines
        #Aplicar la señal de compra/venta
        self.klines = self.signal(self.klines)
        #quitando las velas previas a la fecha de start
        self.klines = self.klines[self.klines['datetime'] >= pd.to_datetime(from_date)]
        self.klines = self.klines.reset_index(drop=True)
        
        
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

        #Calculando HOLD para comparar contra la operacion
        # El hold es la compra del capital a invertir al precio open al inicio + el saldo que queda en USD 
        quote_to_hold = round( self.quote_qty*(self.quote_perc/100) , self.qd_quote )
        price_to_hold = float(self.klines.loc[0]['open'])
        qty_to_hold = round( ( quote_to_hold / price_to_hold ) , self.qd_qty ) 
        usd_in_hold = round( self.quote_qty - quote_to_hold , self.qd_quote )

        self.row_signal = 'NEUTRO'

        for i,kline in self.klines.iterrows():
            k_open = float(kline['open'])
            k_high = float(kline['high'])
            k_low = float(kline['low'])
            k_close = float(kline['close'])

            k_sig_buy = k_low if self.row_signal == 'COMPRA' else None
            k_sig_sell = k_high if self.row_signal == 'VENTA' else None
            
            timestamp = pd.Timestamp(kline['datetime']).timestamp()
            unix_dt = int( (timestamp*1000) +  10800000 ) #Convierte a milisegundos y agrega 3 horas 
            data = {'dt': unix_dt,
                    'dt_': kline['datetime'],
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
            
            venta_por_SLTP = False
            if self.stop_loss_price:
                if k_low < self.stop_loss_price:
                    qty = self.wallet_base
                    price = self.stop_loss_price

                    if self.bt_order_market_sell(qty,price,self.FLAG_STOPLOSS):
                        data['slsl'] = price
                        data['fl'] = 'Stop Loss'
                        venta_por_SLTP = True
                        self.stop_loss_price = None
                        self.take_profit_price = None 

            if not venta_por_SLTP and self.take_profit_price:
                if k_high > self.take_profit_price:
                    qty = self.wallet_base
                    price = self.take_profit_price

                    if self.bt_order_market_sell(qty,price,self.FLAG_TAKEPROFIT):
                        data['sltp'] = price
                        data['fl'] = 'Take Profit'
                        self.stop_loss_price = None
                        self.take_profit_price = None 

            if not venta_por_SLTP and self.row_signal == 'COMPRA' and self.wallet_base == 0:
                if self.interes == 's': #Interes Simple
                    quote_qty = self.quote_qty if self.wallet_quote >= self.quote_qty else self.wallet_quote
                    quote_to_sell = round( quote_qty*(self.quote_perc/100) , self.qd_quote )
                elif self.interes == 'c': #Interes Compuesto
                    quote_to_sell = round( self.wallet_quote*(self.quote_perc/100) , self.qd_quote )
                price = k_open
                
                qty = round_down( ( quote_to_sell / price ) , self.qd_qty )
                if self.bt_order_market_buy(qty,price,self.FLAG_SIGNAL):
                    data['by'] = price
                    data['fl'] = 'Signal'
                    self.stop_loss_price = None
                    self.take_profit_price = None 
                    if self.stop_loss > 0:
                        self.stop_loss_price = round( price - (price * ( self.stop_loss/100) ) , self.qd_price )
                    if self.take_profit > 0:
                        self.take_profit_price = round( price + (price * ( self.take_profit/100) ) , self.qd_price )
               
            elif not venta_por_SLTP and self.row_signal == 'VENTA' and self.wallet_base > 0:
                qty = self.wallet_base
                price = k_open

                if self.bt_order_market_sell(qty,price,self.FLAG_SIGNAL):
                    data['sls'] = price
                    data['fl'] = 'Signal'
                    self.stop_loss_price = None
                    self.take_profit_price = None 
 
            if self.stop_loss_price:
                data['SL'] = round( self.stop_loss_price, self.qd_price) 
            if self.take_profit_price:
                data['TP'] = round( self.take_profit_price, self.qd_price) 
            data['uH'] = round( (qty_to_hold * k_open)      + usd_in_hold      , self.qd_quote )
            data['uW'] = round( (self.wallet_base * k_open) + self.wallet_quote , self.qd_quote )
            
            self.update_pos(k_low,k_high)
            self.res['data'].append(data)
            self.row_signal = kline['signal']

        end = time.time()
        duration = end-start
        self.res['duration_proc'] = round(duration,2)

        if to_get=='ind':
            return self.get_resultados()
    
        self.res['brief'] = self.get_brief()
                        
        return self.res
    