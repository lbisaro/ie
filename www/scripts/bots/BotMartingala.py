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

    VELAS_PREVIAS = 100

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
    
    def signal(self,df):
        #Se debe crear una funcion que agregue al dataframe la columna 'signal' con valores: COMPRA, VENTA o NEUTRO
        df['signal'] = 'NEUTRO'
        return df
    """
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
    """

    def reset_pos(self):
        self.buy_orderid = 0
        self.sell_tp_orderid = 0
        self.sell_sl_orderid = 0
        self.qty_compras = 0
        self.stop_loss_over_quote = 0
        self.pos_buy_history = []

    def backtest(self,klines,from_date,to_date,to_get='completed'):
        self.reset_pos()
        self.backtesting = True
        self.data = []
        
        exch = Exchange(type='info',exchange='bnc',prms=None)
        symbol_info = exch.get_symbol_info(self.symbol)
        self.base_asset = symbol_info['base_asset']
        self.quote_asset = symbol_info['quote_asset']
        self.qd_price = symbol_info['qty_decs_price']
        self.qd_qty = symbol_info['qty_decs_qty']
        self.qd_quote = symbol_info['qty_decs_quote']

        self.wallet_base = 0.0
        self.wallet_quote = self.quote_qty

        self.klines = klines
        #Aplicar la señal de compra/venta
        self.klines = self.signal(self.klines)
        
        #quitando las velas previas a la fecha de start
        self.klines = self.klines[self.klines['datetime'] >= pd.to_datetime(from_date)]
        self.klines = self.klines.reset_index(drop=True)

        velas = int(self.klines['datetime'].count())
        if velas<50:
            res = {
                'OK': False,
                'error': 'El intervalo y rango de fechas solicitado genera un total de '+str(velas)+' velas'+\
                    '<br>Se requiere un minimo de '+str(self.VELAS_PREVIAS)+' velas para poder realizar el Backtesting',
                }
            return res
            

        #Calculando HOLD para comparar contra la operacion
        # El hold es la compra del capital a invertir al precio open al inicio + el saldo que queda en USD
        price_to_hold = self.klines.loc[0]['open'] 
        quote_to_hold = round( self.quote_qty , self.qd_quote )
        qty_to_hold = round( ( quote_to_hold / price_to_hold ) , self.qd_qty ) 
        usd_in_hold = round( self.quote_qty - quote_to_hold , self.qd_quote )
        self.klines['base_qty'] = 0.0
        self.klines['quote_qty'] = 0.0
        self.klines['usd_hold'] = round( self.klines['open'] * qty_to_hold + usd_in_hold, self.qd_quote )

        self.klines['unix_dt'] = (self.klines['datetime'] - datetime(1970, 1, 1)).dt.total_seconds() * 1000 +  10800000
        
        #Eventos para el grafico
        self.klines['sB'] = None
        self.klines['sS'] = None
        self.klines['by'] = None
        self.klines['sls'] = None
        self.klines['slsl'] = None
        self.klines['sltp'] = None
        self.klines['SL'] = None
        self.klines['TP'] = None
        self.klines['BY'] = None

        #Se ejecuta la funcion next para cada registro del dataframe
        proc_start = dt.datetime.now()
        for i,kline in self.klines.iterrows():
            print(f'                                                                                         Procesando {i+1}/{velas} velas',end="\r")
            self.signal = self.klines.iloc[i-1]['signal']
            self.kline = kline
            self.price = float(kline['open'])
            self.unix_dt = self.kline['unix_dt']

            self.klines.loc[i] = self.next()
            self.update_pos_limits()

            #prepara los datos para graficar solo en Backtest Simple
            if to_get=='completed':
                data = {'dt': self.unix_dt,
                        'o': self.kline['open'],
                        'h': self.kline['high'],
                        'l': self.kline['low'],
                        'c': self.kline['close'],
                        'v': self.kline['volume'],
                        'uH': self.kline['usd_hold'],
                        'uW': round( self.kline['close'] * self.kline['base_qty'] + self.kline['quote_qty'], self.qd_quote ),
                        'sB': self.kline['sB'],
                        'sS': self.kline['sS'],
                        'by': self.kline['by'],
                        'sls': self.kline['sls'],
                        'slsl': self.kline['slsl'],
                        'sltp': self.kline['sltp'],
                        'SL': self.kline['SL'],
                        'TP': self.kline['TP'],
                        'BY': self.kline['BY'],
                    }
                self.data.append(data)
        
            self.klines['usd_strat'] = round( self.klines['close'] * self.klines['base_qty'] + self.klines['quote_qty'], self.qd_quote )
        
        print('')
        proc_end = dt.datetime.now()
        proc_diff = proc_end-proc_start
        print('Microseconds: ',proc_diff.microseconds)
        ms_x_kline = proc_diff.microseconds/velas
        print('Microseconds/Velas: ',ms_x_kline)
        self.cancel_open_orders()

        #print(self.klines[self.klines['signal'] != 'NEUTRO'])
        #print(self.klines.tail(10))
        #print(self.orders)
        #print(self.trades)

    
        if to_get=='ind':
            return self.get_resultados()
        
        elif to_get=='completed':
            res = {'ok': True,
                'error': False,
                'order_side': { 
                        self.ORD_SIDE_BUY:'BUY',
                        self.ORD_SIDE_SELL:'SELL',
                        },
                'order_flag': { 
                        self.ORD_FLAG_SIGNAL:'SIGNAL',
                        self.ORD_FLAG_STOPLOSS:'STOP-LOSS',
                        self.ORD_FLAG_TAKEPROFIT:'TAKE-PROFIT',
                        },
                'qd_price': self.qd_price, 
                'qd_qty': self.qd_qty, 
                'qd_quote': self.qd_quote, 
                'data': self.data, 
                'orders': [], 
                'trades': [], 
                }

            for i,trade in self.trades.iterrows():
                trd = [
                    trade['start'],
                    trade['buy_price'],
                    trade['qty'],
                    trade['end'],
                    trade['sell_price'],
                    trade['flag'],
                    trade['days'],
                    trade['result_usd'],
                    trade['result_perc'],
                    trade['mef'],
                    trade['mea'],
                    ]
                res['trades'].append(trd)

            for i,order in self.orders.iterrows():
                ord = [
                        order['datetime'],
                        self.symbol,
                        order['side'],
                        order['qty'],
                        order['price'],
                        order['flag'],
                        round(order['comision'],4),
                    ]
                res['orders'].append(ord)
            
            res['brief'] = self.get_brief()
                            
            return res
    

    def next(self):
         
        price = self.price

        if self.qty_compras == 0:  #Inicia la posicion
            self.quote_pos = self.calculate_pos((self.wallet_quote*0.99), self.qty_pos, self.mult_pos)
            
            quote_to_sell = round(self.quote_pos[0] , self.qd_quote ) 
            base_to_buy = round_down((quote_to_sell/price) , self.qd_qty) 
            buy_orderid = self.order_market_buy(base_to_buy,self.ORD_FLAG_SIGNAL)
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
                    
        
        self.kline['base_qty'] = self.wallet_base
        self.kline['quote_qty'] = self.wallet_quote

        return self.kline


