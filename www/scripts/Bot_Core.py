from bot.models import *
import scripts.functions as fn
import pandas as pd
import numpy as np
from scripts.Exchange import Exchange
import datetime as dt
from scripts.Bot_Core_utils import *
from scripts.functions import round_down


class Bot_Core():
        
    DIAS_X_MES = 30.4375 #Resulta de tomar 3 años de 365 dias + 1 de 366 / 4 años / 12 meses
    exch_comision_perc = 0.2 #0.4% - Comision por operacion de compra o venta

    signal = 'NEUTRO'
    order_id = 0

    #Trades para gestion de resultados
    orders = {}
    trade = {}
    df_trades_columns = ['start','buy_price','qty','end','sell_price','flag','type','days','result_usd','result_perc'] 
    df_trades = pd.DataFrame(columns=df_trades_columns)
    trades = {}
    executed_order = False
    print_orders = False #Muestra las ordenes ejecutadas por consola

    quote_qty = 0
    interval_id = ''
    bot_id = None

    base_asset = ''
    quote_asset = ''
    qd_price = 0
    qd_qty = 0
    qd_quote = 0
    
    backtesting = True
    exchange = None
    wallet_base = 0.0
    wallet_quote = 0.0

    row = pd.DataFrame()

    #Gestion de data sobre ordenes buy_limit, stoploss y takeprofit 
    sl_price_data = []
    tp_price_data = []
    buy_price_data = []


    def __init__(self):
        self.signal = 'NEUTRO'
        self.order_id = 0

        #Trades y Orders para gestion de resultados
        self.orders = {}
        self.trade = {}
        self.df_trades = pd.DataFrame(columns=self.df_trades_columns)
        self.trades = {}
        self.executed_order = False

        self.quote_qty = 0
        self.interval_id = ''
        self.bot_id = None

        self.base_asset = ''
        self.quote_asset = ''
        self.qd_price = 0
        self.qd_qty = 0
        self.qd_quote = 0
        
        self.backtesting = True
        self.exchange = None
        self.wallet_base = 0.0
        self.wallet_quote = 0.0

        self.row = pd.DataFrame()


    def set(self, parametros):
        for v in parametros:
            self.__setattr__(parametros[v]['c'], parametros[v]['v'])
    
    def __setattr__(self, prm, val):
            
        type = 'str'
        if prm in self.parametros:
            type = self.parametros[prm]['t']
            if type == 'perc' or type == 'float':
                self.__dict__[prm] = float(val)
            elif type == 'int':
                self.__dict__[prm] = int(val)
            elif type == 'bin': #Binario
                self.__dict__[prm] = 1 if int(val)>0 else 0
            else:
                self.__dict__[prm] = str(val)
        else:
            self.__dict__[prm] = val

    def valid(self):
        raise Exception(f'\n{self.__class__.__name__} Se debe establecer un metodo valid()')
    def get_symbols(self):
        raise Exception(f'\n{self.__class__.__name__} Se debe establecer un metodo get_symbols()')
    def start(self):
        raise Exception(f'\n{self.__class__.__name__} Se debe establecer un metodo start(df)')
    def next(self):
        raise Exception(f'\n{self.__class__.__name__} Se debe establecer un metodo next(df)')

    def backtest(self,klines,from_date,to_date,to_get='completed'):

        self.backtesting = True
                
        exch = Exchange(type='info',exchange='bnc',prms=None)
        symbol_info = exch.get_symbol_info(self.symbol)
        self.base_asset = symbol_info['base_asset']
        self.quote_asset = symbol_info['quote_asset']
        self.qd_price = symbol_info['qty_decs_price']
        self.qd_qty = symbol_info['qty_decs_qty']
        self.qd_quote = symbol_info['qty_decs_quote']

        self.wallet_base = 0.0
        self.wallet_quote = self.quote_qty
        
        #Aplicar la señal de compra/venta
    
        self.klines = klines.copy()
        self.start()
        
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
        
        
        #Se ejecuta la funcion next para cada registro del dataframe
        proc_start = dt.datetime.now()
        self.klines['usd_strat'] = self.klines.apply(self._next, axis=1)
        proc_end = dt.datetime.now()
        proc_diff = proc_end-proc_start
        print('Duracion: ',f"Proceso demoro {proc_diff.total_seconds():.4f} segundos.")

        #Calculando HOLD para comparar contra la operacion
        # El hold es la compra del capital a invertir al precio open al inicio + el saldo que queda en USD
        price_to_hold = self.klines.loc[0]['open'] 
        quote_to_hold = round( self.quote_qty, self.qd_quote )
        qty_to_hold = round( ( quote_to_hold / price_to_hold ) , self.qd_qty ) 
        self.klines['usd_hold'] = round( self.klines['open'] * qty_to_hold , self.qd_quote )
        self.klines['unix_dt'] = (self.klines['datetime'] - dt.datetime(1970, 1, 1)).dt.total_seconds() * 1000 +  10800000

        #Procesando eventos de Señanes de compra/venta y ordenes
        if self.interval_id < '2d01':
            agg_funcs = {
                    "unix_dt": "first",
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                    "usd_hold": "last",
                    "usd_strat": "last",
                }   
            new_df = self.klines[['datetime','unix_dt','open','high','low','close','volume','usd_hold','usd_strat']].resample('1D', on="datetime").agg(agg_funcs).reset_index()
        else:
            new_df = self.klines[['datetime','unix_dt','open','high','low','close','volume','usd_hold','usd_strat']]

        rename_columns = {'datetime': 'dt', 
                          'open': 'o', 
                          'high': 'h', 
                          'low': 'l', 
                          'close': 'c', 
                          'volume': 'v', 
                          'usd_hold': 'uH', 
                          'usd_strat': 'uW'}
        ohlc = new_df[['datetime','open','high','low','close','volume','usd_hold','usd_strat']].rename(columns=rename_columns).to_dict(orient='records')
    
        new_df = self.klines[['datetime','signal','low','high']]
        sB = self.klines[self.klines['signal']=='COMPRA'][['datetime','low']].rename(columns={'datetime':'dt','low':'sB'}).to_dict(orient='records')
        sS = self.klines[self.klines['signal']=='VENTA'][['datetime','high']].rename(columns={'datetime':'dt','high':'sS'}).to_dict(orient='records')
        events = sB+sS
        events += self.sl_price_data+self.tp_price_data+self.buy_price_data
        if to_get=='ind':
            return self.get_resultados()
        
        elif to_get=='completed':
            self.make_trades()
            res = {'ok': True,
                'error': False,
                'order_side': { 
                        Order.SIDE_BUY:'BUY',
                        Order.SIDE_SELL:'SELL',
                        },
                'order_flag': { 
                        Order.FLAG_SIGNAL:'SIGNAL',
                        Order.FLAG_STOPLOSS:'STOP-LOSS',
                        Order.FLAG_TAKEPROFIT:'TAKE-PROFIT',
                        },
                'order_type': { 
                        Order.TYPE_MARKET:'',
                        Order.TYPE_LIMIT:'LIMIT',
                        Order.TYPE_TRAILING:'TRAIL',
                        },
                'qd_price': self.qd_price, 
                'qd_qty': self.qd_qty, 
                'qd_quote': self.qd_quote, 
                'data': [], 
                'events': [],
                'trades': [], 
                }
            
            #Trades (Lista de trades y Events)
            by = []
            sls = []
            slsl = []
            sltp = []
            for i,trade in self.df_trades.iterrows():
                
                trd = [
                    trade['start'].strftime('%d/%m/%Y %H:%M'),
                    trade['buy_price'],
                    trade['qty'],
                    trade['end'].strftime('%d/%m/%Y %H:%M'),
                    trade['sell_price'],
                    trade['flag'],
                    trade['days'],
                    trade['result_usd'],
                    trade['result_perc'],
                    trade['type'],
                    ]
                res['trades'].append(trd)

            
            for i in self.trades:
                order = self.trades[i]
                #unix_dt = order.datetime.timestamp() * 1000 +  10800000
                
                if order.side==Order.SIDE_BUY:
                    by.append({'dt':order.datetime,'by':order.price})
                if order.side==Order.SIDE_SELL and order.flag == Order.FLAG_SIGNAL:
                    sls.append({'dt':order.datetime,'sls':order.price})
                if order.side==Order.SIDE_SELL and order.flag == Order.FLAG_STOPLOSS:
                    slsl.append({'dt':order.datetime,'slsl':order.price})
                if order.side==Order.SIDE_SELL and order.flag == Order.FLAG_TAKEPROFIT:
                    sltp.append({'dt':order.datetime,'sltp':order.price})
            events += by+sls+slsl+sltp
            

            res['data'] = ohlc
            res['events'] = events
            
            res['brief'] = self.get_brief()
            return res
    
    def _next(self,row):
            
        self.row = row
        self.price = self.row['open']
        self.datetime = self.row['datetime']
        self.executed_order = self.check_orders()
        self.next()

        #Gestion de stoploss y takeprofit price
        for i in self.orders: #Ordenes abiertas
            order = self.orders[i]
            if order.flag == Order.FLAG_STOPLOSS:
                self.sl_price_data.append({'dt': self.datetime,'SL':order.limit_price})
            elif order.flag == Order.FLAG_TAKEPROFIT:
                self.tp_price_data.append({'dt': self.datetime,'TP':order.limit_price})
            elif order.side == Order.SIDE_BUY:
                self.buy_price_data.append({'dt': self.datetime,'BY':order.limit_price})


        if row.name == self.klines.iloc[-1].name: #Se esta ejecutando la ultima vela
            if self.wallet_base > 0:
                self.close(Order.FLAG_SIGNAL)
            self.cancel_orders()

        usd_strat = round( self.price * self.wallet_base + self.wallet_quote, self.qd_quote )
        
        self.signal = self.row['signal']
        return usd_strat

    def buy(self,qty,flag):
        if self.wallet_quote >= qty*self.price and qty*self.price>=10: #Compra solo si hay wallet_quote y si el wallet_quote a comprar es > 10 USD
            self.order_id += 1
            qty = round_down(qty,self.qd_qty)
            order = Order(self.order_id,Order.TYPE_MARKET,self.row['datetime'],Order.SIDE_BUY,qty,self.price,flag)
            self.orders[order.id] = order
            if self.execute_order(order.id):
                return order.id

        return 0

    def sell(self,qty,flag):
        if self.wallet_base >= qty and qty*self.price>=10: #Vende solo si hay wallet_quote y si el wallet_quote a comprar es > 10 USD
            self.order_id += 1
            qty = round(qty,self.qd_qty)
            order = Order(self.order_id,Order.TYPE_MARKET,self.row['datetime'],Order.SIDE_SELL,qty,self.price,flag)
            self.orders[order.id] = order
            if self.execute_order(order.id): 
                return order.id
        return 0
        
    def sell_limit(self,qty,flag,limit_price):
        if self.wallet_base >= qty and qty*limit_price>=10: #Vende solo si hay wallet_quote y si el wallet_quote a comprar es > 10 USD
            self.order_id += 1
            qty = round_down(qty,self.qd_qty)
            limit_price = round(limit_price,self.qd_price)
            order = Order(self.order_id,Order.TYPE_LIMIT,self.row['datetime'],Order.SIDE_SELL,qty,limit_price,flag)
            self.orders[order.id] = order
            return order.id
        return 0  
    
    def buy_limit(self,qty,flag,limit_price):
        if self.wallet_quote >= qty*self.price and qty*limit_price>=10: #Compra solo si hay wallet_quote y si el wallet_quote a comprar es > 10 USD
            self.order_id += 1
            qty = round_down(qty,self.qd_qty)
            limit_price = round(limit_price,self.qd_price)
            order = Order(self.order_id,Order.TYPE_LIMIT,self.row['datetime'],Order.SIDE_BUY,qty,limit_price,flag)
            self.orders[order.id] = order
            return order.id
        return 0    
    
    def sell_trail(self,qty,flag,limit_price,activation_price,trail_perc):
        if self.wallet_base >= qty and qty*limit_price>=10: #Compra solo si hay wallet_quote y si el wallet_quote a comprar es > 10 USD
            self.order_id += 1
            qty = round(qty,self.qd_qty)
            order = Order(self.order_id,Order.TYPE_TRAILING,self.row['datetime'],Order.SIDE_SELL,qty,limit_price,flag)
            order.activation_price = activation_price
            order.trail_perc = trail_perc
            self.orders[order.id] = order
            return order.id
        return 0    
          
    def close(self,flag): #Vende el total existente en self.wallet_base
        self.order_id += 1
        qty = self.wallet_base
        order = Order(self.order_id,Order.TYPE_MARKET,self.row['datetime'],Order.SIDE_SELL,qty,self.price,flag)
        self.orders[order.id] = order
        if self.execute_order(order.id):
            return order.id
        return 0
        
    def cancel_orders(self):
        self.orders = {}
    
    def check_orders(self):
        
        executed = False
        orders = self.orders.copy() #Se hace una copia porque si se ejecuta alguna orden, se modifica el tamaño del diccionario y eso afecta al bucle for
        for i in orders:
            order  = self.orders[i]
            if order.type == Order.TYPE_LIMIT or order.type == Order.TYPE_TRAILING:
                
                if order.side == Order.SIDE_BUY:
                    if self.row['low'] <= order.limit_price:
                        executed =  self.execute_order(order.id)
                        
                if order.side == Order.SIDE_SELL and order.flag == Order.FLAG_TAKEPROFIT:
                    if self.row['high'] >= order.limit_price:
                        executed = self.execute_order(order.id)
                        
                if order.side == Order.SIDE_SELL and order.flag == Order.FLAG_STOPLOSS:
                    if self.row['low'] <= order.limit_price:
                        executed = self.execute_order(order.id)
            
            #Actualizando limit_price en caso que aplique
            if not executed and order.type == Order.TYPE_TRAILING:
                #Verifica si se activa el trailing
                if order.side == Order.SIDE_SELL and self.row['high'] > order.activation_price:
                    order.active = True

                #Venta por Stop-Loss
                if order.active and order.side == Order.SIDE_SELL and order.flag == Order.FLAG_STOPLOSS:
                    if order.limit_price < self.row['high']*(1-(order.trail_perc/100)):
                        order.limit_price = self.row['high']*(1-(order.trail_perc/100))
                
                #Venta por Take-Profit
                if order.active and order.side == Order.SIDE_SELL and order.flag == Order.FLAG_TAKEPROFIT:
                    if order.limit_price < self.row['high']*(1+(order.trail_perc/100)):
                        order.limit_price = self.row['high']*(1+(order.trail_perc/100))

        return executed
    
    def execute_order(self,orderid):
        
        order = self.orders[orderid]
        order.price = order.limit_price
        order.datetime = self.row['datetime']  
        if order.type == Order.TYPE_TRAILING and not order.active:
            order.type = Order.TYPE_LIMIT
        
        if self.print_orders:
            if order.side == Order.SIDE_SELL:
                print(f'\033[31m{order}\033[0m',end=' -> ')
            else:
                print(f'\033[32m{order}\033[0m',end=' -> ')

        execute = False
        if order.side == Order.SIDE_BUY:
            quote_to_sell = round(order.qty*order.price,self.qd_quote)
            comision = round(quote_to_sell*(self.exch_comision_perc/100),4)
            new_wallet_base = round(self.wallet_base + order.qty,self.qd_qty)
            new_wallet_quote = round(self.wallet_quote - quote_to_sell ,self.qd_quote)
            if new_wallet_base >= 0 and new_wallet_quote >= 0:
                self.wallet_base = new_wallet_base 
                self.wallet_quote = new_wallet_quote - comision
                execute = True

        elif order.side == Order.SIDE_SELL:
            quote_to_buy = round(order.qty*order.price,self.qd_quote)
            comision = round(quote_to_buy*(self.exch_comision_perc/100),4)
            new_wallet_base = round(self.wallet_base - order.qty,self.qd_qty)
            new_wallet_quote = round(self.wallet_quote + quote_to_buy,self.qd_quote)
            if new_wallet_base >= 0 and new_wallet_quote >= 0:
                self.wallet_base = new_wallet_base 
                self.wallet_quote = new_wallet_quote - comision
                execute = True

        del self.orders[orderid] 
        if execute:
            self.trades[order.id] = order
            if self.print_orders:
                print(f'\033[32mOK\033[0m')
        else:
            if self.print_orders:
                print(f'\033[31mCANCELED\033[0m')

        return execute
        
    def make_trades(self):
        
        for i in self.trades:
            order = self.trades[i]
            
            order.comision = round((order.price*order.qty)*(self.exch_comision_perc/100),4)
            self.trades[i].comision = order.comision
            if self.trade == {}: # Open Trade
                self.trade['start'] = order.datetime
                self.trade['flag'] = order.flag
                self.trade['type'] = order.type
                self.trade['comision'] = order.comision
                if order.side == Order.SIDE_BUY:
                    self.trade['buy_qty'] = order.qty
                    self.trade['buy_quote'] = round(order.qty*order.price,self.qd_quote)
                    self.trade['sell_qty'] = 0.0
                    self.trade['sell_quote'] = 0.0
                elif order.side == Order.SIDE_SELL:
                    self.trade['buy_qty'] = 0.0
                    self.trade['buy_quote'] = 0.0
                    self.trade['sell_qty'] = order.qty
                    self.trade['sell_quote'] = round(order.qty*order.price,self.qd_quote)
                self.trade['price_start'] = order.price

            else:
                
                self.trade['end'] = order.datetime
                self.trade['flag'] = order.flag
                self.trade['type'] = order.type
                self.trade['comision'] = self.trade['comision']+order.comision
                if order.side == Order.SIDE_BUY:
                    self.trade['buy_qty'] = self.trade['buy_qty']+order.qty
                    self.trade['buy_quote'] = self.trade['buy_quote']+round(order.qty*order.price,self.qd_quote)
                elif order.side == Order.SIDE_SELL:
                    self.trade['sell_qty'] = self.trade['sell_qty']+order.qty
                    self.trade['sell_quote'] = self.trade['sell_quote']+round(order.qty*order.price,self.qd_quote)            
            
            if (round(self.trade['buy_qty'] - self.trade['sell_qty'],self.qd_qty) == 0) or (round(self.trade['buy_quote'] - self.trade['sell_quote'],self.qd_quote) == 0):
                start = self.trade['start']
                buy_price = round(self.trade['buy_quote']/self.trade['buy_qty'],self.qd_price)
                qty = self.trade['buy_qty']
                end = self.trade['end']
                sell_price = round(self.trade['sell_quote']/self.trade['sell_qty'],self.qd_price)
                flag = self.trade['flag']
                type = self.trade['type']
                dif = self.trade['end'].to_pydatetime() - self.trade['start'].to_pydatetime()
                days = dif.total_seconds() / 60 / 60 / 24
                result_usd = self.trade['sell_quote'] - self.trade['buy_quote'] - self.trade['comision']
                result_perc = round((((sell_price/buy_price)-1)*100) - ((self.exch_comision_perc) * 2) , 2)
                trade = pd.DataFrame([[start,buy_price,qty,end,sell_price,flag,type,days,result_usd,result_perc]], columns=self.df_trades_columns) 
                self.df_trades = pd.concat([self.df_trades, trade], ignore_index=True) 
                self.trade = {}

    def get_brief(self):
        kline_ini = self.klines.loc[self.klines.index[0]]
        kline_end = self.klines.loc[self.klines.index[-1]]

        
        brief = []

        #general
        symbol = self.symbol
        intervalo = fn.get_intervals(self.interval_id,'binance') 
        last_close = float(kline_end['close'])
        usd_final =  self.wallet_quote + self.wallet_base*last_close
        resultado_usd = usd_final-self.quote_qty
        resultado_perc = (resultado_usd/self.quote_qty)*100
        dif_days = kline_end['datetime'] - kline_ini['datetime']
        dias_operando = round(dif_days.total_seconds() / 3600 / 24,1)
        resultado_mensual = (resultado_perc/dias_operando)*self.DIAS_X_MES
        dias_trades = self.df_trades['days'].sum()
        dias_sin_operar = dias_operando - dias_trades

        
        brief.append(['general', 'Par',    
                      f'{symbol} {intervalo}' ])  
        """          
        brief.append(['general', 'Capital',    
                      f'USD {self.quote_qty} - Posicion {self.quote_perc}%'   ])  
        if self.interes == 'c':          
            brief.append(['general', 'Tipo de interes','Compuesto'   ])            
        elif self.interes == 's':          
            brief.append(['general', 'Tipo de interes','Simple'   ])       
           
        brief.append(['general', 'Gestion de riesgo',    
                      f'Stop-Loss {self.stop_loss}% - Take-Profit {self.take_profit}%'   ])            
        """
        start = kline_ini['datetime'].strftime('%Y-%m-%d %H:%M')
        end = kline_end['datetime'].strftime('%Y-%m-%d %H:%M')
        brief.append(['general', 'Periodo',    
                      f'{start} - {end}' ])   
        brief.append(['general', 'Dias del periodo',    
                      f'{dias_operando:.1f}'])            
        brief.append(['general', 'Dias sin operar',    
                      f'{dias_sin_operar:.1f}'])            
        brief.append(['general', 'Resultado General',    
                      f'{resultado_perc:.2f}%' , 
                      ('text-success' if resultado_perc > 0 else 'text-danger')  ])            
        brief.append(['general', 'Resultado mensual',    
                      f'{resultado_mensual:.2f}%' ,
                      ('text-success' if resultado_perc > 0 else 'text-danger')   ])            

        
        #operaciones
        trades_desc = self.df_trades.describe()
        trades_tot = self.df_trades['start'].count()
        
        if trades_tot > 0:

            trades_pos = np.where(self.df_trades['result_perc'] > 0, 1, 0).sum()
            ratio_trade_pos = (trades_pos/trades_tot)*100 
            max_ganancia = trades_desc.loc['max', 'result_perc']
            max_perdida = trades_desc.loc['min', 'result_perc']
            ratio_perdida_ganancia = self.ind_ratio_ganancia_perdida(self.df_trades)
            ratio_max_perdida_ganancia = ((-max_ganancia) / max_perdida) if max_ganancia != 0 else float('inf')
            trades_x_mes = trades_tot / ( dias_operando / self.DIAS_X_MES)
            maximo_operaciones_negativas_consecutivas = self.ind_maximo_operaciones_negativas_consecutivas(self.df_trades)

            brief.append(['operaciones', 'Total de operaciones',    
                        f'{trades_tot}'])    
            brief.append(['operaciones', 'Operaciones mensuales',    
                        f'{trades_x_mes:.2f}'])    
            brief.append(['operaciones', 'Operaciones positivas',    
                        f'{trades_pos} ( {ratio_trade_pos:.2f}% )'  ])    
            brief.append(['operaciones', 'Comision Exchange',    
                        f'{self.exch_comision_perc}%'  ])    
            brief.append(['operaciones', 'Maxima ganancia',    
                        f'{max_ganancia}%'])    
            brief.append(['operaciones', 'Maxima perdida',    
                        f'{max_perdida}%'])    
            brief.append(['operaciones', 'Ratio Ganancia/Perdida',    
                        f'{ratio_perdida_ganancia:.2f}' ])    
            brief.append(['operaciones', 'Ratio Mayor Ganancia/Perdida',    
                        f'{ratio_max_perdida_ganancia:.2f}'])    
            brief.append(['operaciones', 'Maximo Perdidas consecutivas',    
                        f'{maximo_operaciones_negativas_consecutivas}'])   
   
            

            #indicadores
            volatilidad_cap = self.ind_volatilidad(self.klines,'usd_strat')
            volatilidad_sym = self.ind_volatilidad(self.klines,'usd_hold')
            max_drawdown_cap = self.ind_maximo_drawdown(self.klines,'usd_strat')
            max_drawdown_sym = self.ind_maximo_drawdown(self.klines,'usd_hold')
            max_drawup_cap = self.ind_maximo_drawup(self.klines,'usd_strat')
            max_drawup_sym = self.ind_maximo_drawup(self.klines,'usd_hold')

            cagr = self.ind_cagr(self.klines)
            ratio_sharpe = self.ind_ratio_sharpe(self.klines)
            risk_free_rate=0.045
            ratio_sortino = self.ind_ratio_sortino(self.klines, risk_free_rate)
            ratio_ulcer = self.ind_ratio_ulcer(self.klines)
            ratio_calmar = self.ind_ratio_calmar(self.klines)
            modificacion_sharpe = self.ind_indice_modificacion_sharpe(self.klines)
            umbral_objetivo_riesgo = 0.02  # Umbral objetivo de riesgo: 2%
            ratio_sortino_modificado = self.ind_ratio_sortino_modificado(self.df_trades,umbral_objetivo_riesgo)


            brief.append(['indicadores', 'Volatilidad del capital',    
                        f'{volatilidad_cap:.2f}%'])          
            brief.append(['indicadores', 'Volatilidad del par',    
                        f'{volatilidad_sym:.2f}%'])          
            brief.append(['indicadores', 'Maximo DrawDown Capital',    
                        f'{max_drawdown_cap:.2f}%'])          
            brief.append(['indicadores', 'Maximo DrawDown Par',    
                        f'{max_drawdown_sym:.2f}%'])   
            brief.append(['indicadores', 'Maximo DrawUp Capital',    
                        f'{max_drawup_cap:.2f}%'])          
            brief.append(['indicadores', 'Maximo DrawUp Par',    
                        f'{max_drawup_sym:.2f}%'])   
            brief.append(['indicadores', 'CAGR',    
                        f'{cagr:.2f}%'])          
            brief.append(['indicadores', 'Ratio Sharpe',    
                        f'{ratio_sharpe:.2f}'])          
            brief.append(['indicadores', f'Ratio Sortino ({risk_free_rate})',    
                        f'{ratio_sortino:.2f}'])          
            brief.append(['indicadores', 'Ratio Ulcer',    
                        f'{ratio_ulcer:.2f}'])          
            brief.append(['indicadores', 'Ratio Calmar',    
                        f'{ratio_calmar:.2f}'])          
            brief.append(['indicadores', 'Indice de Modificacion de Sharpe',    
                        f'{modificacion_sharpe:.2f}'])          
            brief.append(['indicadores', f'Ratio Sortino Modificado ({umbral_objetivo_riesgo})',    
                        f'{ratio_sortino_modificado:.2f}'])          

        return brief

    def get_resultados(self):

        kline_ini = self.klines.loc[self.klines.index[0]]
        kline_end = self.klines.loc[self.klines.index[-1]]

        df_trades = self.df_trades
        df_data = self.klines

        dif_days = kline_end['datetime'] - kline_ini['datetime']
        dias_operando = round(dif_days.total_seconds() / 3600 / 24,1)
        dias_trades = df_trades['days'].sum()
        dias_sin_operar = dias_operando - dias_trades
        ratio_dias_sin_operar = (dias_sin_operar/dias_operando)*100 if dias_operando > 0 else 0.0

        trades_desc = df_trades.describe()
        trades_tot = df_trades['start'].count()

        trades_pos = np.where(df_trades['result_perc'] > 0, 1, 0).sum()
        ratio_trade_pos = (trades_pos/trades_tot)*100 if trades_tot > 0 else 0.0
        max_ganancia = trades_desc.loc['max', 'result_perc'] if trades_pos > 0 else 0.0
        max_perdida = trades_desc.loc['min', 'result_perc'] if trades_pos > 0 else 0.0
        ratio_perdida_ganancia = self.ind_ratio_ganancia_perdida(df_trades) if trades_pos > 0 else 0.0
        ratio_max_perdida_ganancia = ((-max_ganancia) / max_perdida) if max_perdida != 0 else 0.0
        trades_x_mes = trades_tot / ( dias_operando / self.DIAS_X_MES) if dias_operando != 0 else 0.0
        maximo_operaciones_negativas_consecutivas = self.ind_maximo_operaciones_negativas_consecutivas(df_trades)

        volatilidad_cap = self.ind_volatilidad(df_data,'usd_strat')
        volatilidad_sym = self.ind_volatilidad(df_data,'usd_hold')
        ratio_volatilidad = (volatilidad_cap/volatilidad_sym)*100 if volatilidad_sym != 0 else 0.0
        max_drawdown_cap = self.ind_maximo_drawdown(df_data,'usd_strat')
        max_drawdown_sym = self.ind_maximo_drawdown(df_data,'usd_hold')
        ratio_max_drawdown = (max_drawdown_cap/max_drawdown_sym)*100 if max_drawdown_sym != 0 else 0.0
        max_drawup_cap = self.ind_maximo_drawup(df_data,'usd_strat')
        max_drawup_sym = self.ind_maximo_drawup(df_data,'usd_hold')
        ratio_max_drawup = (max_drawup_cap/max_drawup_sym)*100  if max_drawup_sym != 0 else 0.0
        cagr = self.ind_cagr(df_data)
        ratio_calmar = self.ind_ratio_calmar(df_data) if trades_pos > 0 else 0.0
        modificacion_sharpe = self.ind_indice_modificacion_sharpe(df_data) if trades_pos > 0 else 0.0
        
        resultados = []
        resultados.append({'ind':'cagr',self.symbol: cagr })          
        resultados.append({'ind':'max_drawdown_cap',self.symbol: max_drawdown_cap })
        resultados.append({'ind':'maximo_operaciones_negativas_consecutivas',self.symbol: maximo_operaciones_negativas_consecutivas })   
        resultados.append({'ind':'ratio_dias_sin_operar',self.symbol: ratio_dias_sin_operar })  
        resultados.append({'ind':'trades_x_mes',self.symbol: trades_x_mes})  
        resultados.append({'ind':'ratio_trade_pos',self.symbol: ratio_trade_pos  })    
        resultados.append({'ind':'ratio_perdida_ganancia',self.symbol: ratio_perdida_ganancia })    
        resultados.append({'ind':'ratio_max_perdida_ganancia',self.symbol: ratio_max_perdida_ganancia })    
        resultados.append({'ind':'ratio_volatilidad',self.symbol: ratio_volatilidad})          
        resultados.append({'ind':'ratio_max_drawdown',self.symbol: ratio_max_drawdown })
        resultados.append({'ind':'ratio_max_drawup',self.symbol: ratio_max_drawup })
        resultados.append({'ind':'ratio_calmar',self.symbol: ratio_calmar })          
        resultados.append({'ind':'modificacion_sharpe',self.symbol: modificacion_sharpe })

        return resultados
        
    def ind_ratio_ganancia_perdida(self,df_trades):
        # Esta función calcula el ratio de ganancias y pérdidas de las operaciones.
        ganancias = df_trades[df_trades['result_perc'] > 0]['result_perc']
        perdidas = df_trades[df_trades['result_perc'] < 0]['result_perc']
        promedio_ganancias = ganancias.mean() if len(ganancias) > 0 else 0
        promedio_perdidas = perdidas.mean() if len(perdidas) > 0 else 0
        ratio_ganancia_perdida = promedio_ganancias / abs(promedio_perdidas) if promedio_perdidas != 0 else 0
        return round(ratio_ganancia_perdida,2)
    
    def ind_maximo_operaciones_negativas_consecutivas(self, df_trades):
        max_consecutivas = 0
        consecutivas = 0
        for resultado in df_trades['result_perc']:
            if resultado < 0:
                consecutivas += 1
                if consecutivas > max_consecutivas:
                    max_consecutivas = consecutivas
            else:
                consecutivas = 0
        return max_consecutivas
    
    def ind_maximo_drawdown(self, df_data, key):
        # Esta función calcula el máximo drawdown del capital acumulado.
        data = df_data[key]
        roll_max = data.cummax()
        drawdown = ((data / roll_max) - 1.0 ) * (-100)
        return round(drawdown.max(),2)

    def ind_maximo_drawup(self, df_data, key):
        # Esta función calcula el máximo drawup del capital acumulado.
        data = df_data[key]
        roll_min = data.cummin()
        drawup = ((data / roll_min) - 1.0 ) * 100
        return round(drawup.max(),2)

    def ind_volatilidad(self, df_data,key):
        # Volatilidad anualizada 
        return df_data[key].pct_change().std() * np.sqrt(360)*100

    def ind_ratio_sharpe(self, df_data, risk_free_rate=0.045):
        returns = df_data['usd_strat'].pct_change()
        sharpe_ratio = (self.ind_cagr(df_data) - risk_free_rate) / self.ind_volatilidad(df_data,'usd_strat')
        return sharpe_ratio
    
    def ind_cagr(self, df_data):
        # CAGR (Compound Annual Growth Rate).
        kline_ini = self.klines.loc[self.klines.index[0]]
        kline_end = self.klines.loc[self.klines.index[-1]]

        dif_days = kline_end['datetime'] - kline_ini['datetime']
        dias_operando = round(dif_days.total_seconds() / 3600 / 24,1)
        years = dias_operando / 365
       
        data = df_data['usd_strat']
        return ((data.iloc[-1] / data.iloc[0]) ** (1 / years) - 1)*100
    
    def ind_ratio_sortino(self, df_data, risk_free_rate):
        df_data['retorno_diario'] = df_data['usd_strat'].pct_change()
        negative_returns = df_data[df_data['retorno_diario'] < 0]['retorno_diario'].std() * np.sqrt(360)
        sortino_ratio = (self.ind_cagr(df_data) - risk_free_rate) / negative_returns
        return sortino_ratio
    
    def ind_drawdowns(self, df_data):
    # Esta función calcula los drawdowns a partir de los datos del capital acumulado.
        data = df_data['usd_strat']
        roll_max = data.cummax()
        drawdowns = data - roll_max
        return drawdowns

    def ind_ratio_ulcer(self, df_data):
        # Esta función calcula el Ratio de Ulcer.
        drawdowns = self.ind_drawdowns(df_data)
        ulcer_index = np.sqrt(np.mean(drawdowns ** 2))
        return ulcer_index

    def ind_indice_modificacion_sharpe(self, df_data, risk_free_rate=4.5):
        # Esta función calcula el Índice de Modificación de Sharpe.

        """
        me parece que risk_free_rate deberia ser 4.5 en lugar de 0.045
        el CAGR esta expresado en porcentaje y el risk_free_rate en 1/100
        """

        cagr = self.ind_cagr(df_data)
        volatilidad = self.ind_volatilidad(df_data,'usd_strat')
        max_drawdown = self.ind_maximo_drawdown(df_data,'usd_strat')
        sharpe_ratio = self.ind_ratio_sharpe(df_data, risk_free_rate=risk_free_rate)
        indice_modificacion_sharpe = (cagr - risk_free_rate) / (volatilidad * abs(max_drawdown) * sharpe_ratio)

        return indice_modificacion_sharpe
    
    def ind_ratio_calmar(self, df_data):
        # Esta función calcula el Ratio de Calmar.
        cagr = self.ind_cagr(df_data)
        max_drawdown = self.ind_maximo_drawdown(df_data,'usd_strat')
        ratio_calmar = cagr / abs(max_drawdown)
        return ratio_calmar
    
    def ind_ratio_sortino_modificado(self, df_trades, umbral_objetivo_riesgo):
        # Esta función calcula el Ratio de Sortino Modificado.
        retorno_total = df_trades['result_usd'].sum()
        df_trades['retorno_diario'] = df_trades['result_usd'] / self.quote_qty
        df_trades['retorno_negativo'] = df_trades['retorno_diario'].apply(lambda x: x if x < 0 else 0)
        desviacion_negativa = df_trades['retorno_negativo'].std()
        if desviacion_negativa!=0:
            ratio_sortino_modificado = (retorno_total - umbral_objetivo_riesgo) / desviacion_negativa
            return ratio_sortino_modificado
        return 0.0
    
    def is_order(self,orderid):
        if orderid in self.orders:
            return True
        return False

    def get_order(self,orderid):
        if orderid in self.orders:
            return self.orders[orderid]
        return None

    def is_order_completed(self,orderid):
        if orderid in self.trades:
            return True
        return False
