from bot.models import *
import scripts.functions as fn
import pandas as pd
import numpy as np
from scripts.Exchange import Exchange
import datetime as dt


class Bot_Core():
        
    ORD_SIDE_BUY = 0
    ORD_SIDE_SELL = 1

    ORD_TYPE_MARKET = 0
    ORD_TYPE_LIMIT = 1
    ORD_TYPE_TRAILING = 2

    ORD_FLAG_SIGNAL = 0
    ORD_FLAG_STOPLOSS = 1
    ORD_FLAG_TAKEPROFIT = 2
    ORD_FLAG_TRAILING = 3
    
    DIAS_X_MES = 30.4375 #Resulta de tomar 3 años de 365 dias + 1 de 366 / 4 años / 12 meses

    exch_comision_perc = 0.2 #0.4% - Comision por operacion de compra o venta

    signal = 'NEUTRO'

    orderid = 0

    quote_qty = 0
    interval_id = ''
    bot_id = None

    base_asset = ''
    quote_asset = ''
    qd_price = 0
    qd_qty = 0
    qd_quote = 0

        
    #Registro de ordenes
    order_columns = ['datetime','unix_dt','orderid','qty', 'price', 'side', 'flag', 'type','completed','limit_price','delta_perc','activation_price','comision']
    orders = pd.DataFrame(columns=order_columns)
    #Trade en curso
    trade = {}
    #Registro de trades
    trades_columns = ['start','buy_price','qty','end','sell_price','flag','days','result_usd','result_perc']
    trades = pd.DataFrame(columns=trades_columns)
    
    backtesting = True
    exchange = None
    bt_index = None #Almacena el datetime de la siguiente vela en el loop de backtesting 
    wallet_base = 0.0
    wallet_quote = 0.0

    unix_dt = None

    klines = None
    price = None
    k_high = None
    k_low = None

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
            else:
                self.__dict__[prm] = str(val)
        
        else:
            self.__dict__[prm] = val

    def valid(self):
        raise Exception(f'\n{self.__class__.__name__} Se debe establecer un metodo valid()')
    
    def get_symbols(self):
        raise Exception(f'\n{self.__class__.__name__} Se debe establecer un metodo get_symbols()')
    
    def signal(self,df):
        raise Exception(f'\n{self.__class__.__name__} Se debe establecer un metodo signal(df)')

    def add_order(self,qty, side, flag, type, limit_price, delta_perc, activation_price):
        price = 0.0
        completed = False
        self.orderid += 1
        orderid = self.orderid
        comision = 0.0
        new_order = pd.DataFrame([[self.datetime, self.unix_dt, orderid, qty, price, side, flag, type, completed, limit_price, delta_perc, activation_price,comision]], columns=self.order_columns)
        self.orders = pd.concat([self.orders, new_order], ignore_index=True) 
                
        if type == self.ORD_TYPE_MARKET:
            if self.execute_order(orderid):
                return orderid
            else:
                return 0
            
        return orderid
    
    def check_open_orders(self):
        open_orders = self.get_open_orders()

        executed = False

        for i,order in open_orders.iterrows():

            if order['type'] == self.ORD_TYPE_LIMIT:
                
                if order['side'] == self.ORD_SIDE_BUY:
                    if self.k_low <= order['limit_price']:
                        if self.execute_order(order['orderid']):
                            executed = True
                        
                if order['side'] == self.ORD_SIDE_SELL and order['flag'] == self.ORD_FLAG_TAKEPROFIT:
                    if self.k_high >= order['limit_price']:
                        if self.execute_order(order['orderid']):
                            executed = True
                        
                if order['side'] == self.ORD_SIDE_SELL and order['flag'] == self.ORD_FLAG_STOPLOSS:
                    if self.k_low <= order['limit_price']:
                        if self.execute_order(order['orderid']):
                            executed = True
                        
            #if order['type'] == self.ORD_TYPE_TRAILING:
            #    #verificar que el minimo no haya agarrado el stop por trailing
            #    #Actualizar limit_price si es que el maximo/minimo es mayor/menor al anterior con referencia al delta y el high/low
            #    if order['side'] == self.ORD_SIDE_BUY:
            #        pass
            #    if order['side'] == self.ORD_SIDE_SELL:
            #        pass

        return executed

    def get_open_orders(self):
        return self.orders[self.orders['completed'] == False]
    
    def is_order(self,orderid):
        order = self.orders[self.orders['orderid'] == orderid]
        if not order.empty:
            return True
        return False

    def get_order(self,orderid):
        order = self.orders[self.orders['orderid'] == orderid]
        return order.iloc[0]

    def is_order_completed(self,orderid):
        order = self.orders[self.orders['orderid'] == orderid]
        return order['completed'].iloc[0]
    
    def open_orders_qty(self):
        return self.get_open_orders['datetime'].count()
    
    def delete_order(self,orderid):
        self.orders = self.orders.drop(self.orders[self.orders['orderid'] == orderid].index)
    
    def cancel_open_orders(self):
        self.orders = self.orders.drop(self.orders[self.orders['completed'] == False].index)
    
    #Si se intenta ejecutar una orden de venta con qty = 0, lo que hace es liquidar todas las unidades definidas en self.wallet_base
    def execute_order(self,orderid):
        order = self.orders.loc[self.orders['orderid'] == orderid]
        i = order.iloc[0].name
        side = order.iloc[0]['side']
        qty = order.iloc[0]['qty'] 
        type = order.iloc[0]['type']
        flag = order.iloc[0]['flag']
        if type == self.ORD_TYPE_MARKET:
            price = self.price
        else:
            price = order.iloc[0]['limit_price']
        comision = (price*qty) * (self.exch_comision_perc/100)
        
        if side == self.ORD_SIDE_BUY:
            quote_to_sell = qty*price
            new_wallet_base = round(self.wallet_base + qty,self.qd_qty)
            new_wallet_quote = round(self.wallet_quote - quote_to_sell,self.qd_quote)
            if new_wallet_base >= 0 and new_wallet_quote >= 0:
                self.wallet_base = new_wallet_base 
                self.wallet_quote = new_wallet_quote - comision
                self.orders.loc[self.orders['orderid'] == orderid, ['datetime', 'price', 'completed','comision']] = [self.datetime, price, True, comision]
                return True
            else:
                self.delete_order(orderid)
        
        elif side == self.ORD_SIDE_SELL:
            
            if qty == 0:
                qty = self.wallet_base
            quote_to_buy = qty*price
            new_wallet_base = round(self.wallet_base - qty,self.qd_qty)
            new_wallet_quote = round(self.wallet_quote + quote_to_buy,self.qd_quote)
            if new_wallet_base >= 0 and new_wallet_quote >= 0:
                self.wallet_base = new_wallet_base 
                self.wallet_quote = new_wallet_quote - comision
                self.orders.loc[self.orders['orderid'] == orderid, ['datetime', 'price', 'completed','comision','qty']] = [self.datetime, price, True, comision, qty]

                return True
            else:
                self.delete_order(orderid)
        
        return False

    def order_market(self,side,qty,flag):
        limit_price = None
        delta_perc = None
        activation_price = None
        return self.add_order(qty, side, flag, self.ORD_TYPE_MARKET, limit_price, delta_perc, activation_price)

    def order_market_buy(self,qty,flag):
        return self.order_market(self.ORD_SIDE_BUY,qty,flag)
	
    def order_market_sell(self,qty,flag):
        return self.order_market(self.ORD_SIDE_SELL,qty,flag)
    

    def order_limit(self,side,qty,limit_price,flag):
        delta_perc = None
        activation_price = None
        return self.add_order(qty, side, flag, self.ORD_TYPE_LIMIT, limit_price, delta_perc, activation_price)

    def order_limit_buy(self,qty,limit_price,flag):
        return self.order_limit(self.ORD_SIDE_BUY,qty,limit_price,flag)
	
    def order_limit_sell(self,qty,limit_price,flag):
        if flag != self.ORD_FLAG_STOPLOSS and flag != self.ORD_FLAG_TAKEPROFIT:
            return False
        return self.order_limit(self.ORD_SIDE_SELL,qty,limit_price,flag)
    
    def make_trades(self):
        for i, order in self.orders.iterrows():
            if self.trade == {}: # Open Trade
                self.trade['start'] = order['datetime']
                self.trade['flag'] = order['flag']
                self.trade['comision'] = order['comision']
                if order['side'] == self.ORD_SIDE_BUY:
                    self.trade['buy_qty'] = order['qty']
                    self.trade['buy_quote'] = round(order['qty']*order['price'],self.qd_quote)
                    self.trade['sell_qty'] = 0.0
                    self.trade['sell_quote'] = 0.0
                elif order['side'] == self.ORD_SIDE_SELL:
                    self.trade['buy_qty'] = 0.0
                    self.trade['buy_quote'] = 0.0
                    self.trade['sell_qty'] = order['qty']
                    self.trade['sell_quote'] = round(order['qty']*order['price'],self.qd_quote)
                self.trade['price_start'] = order['price']

            else:
                self.trade['end'] = order['datetime']
                self.trade['flag'] = order['flag']
                self.trade['comision'] = self.trade['comision']+order['comision']
                if order['side'] == self.ORD_SIDE_BUY:
                    self.trade['buy_qty'] = self.trade['buy_qty']+order['qty']
                    self.trade['buy_quote'] = self.trade['buy_quote']+round(order['qty']*order['price'],self.qd_quote)
                elif order['side'] == self.ORD_SIDE_SELL:
                    self.trade['sell_qty'] = self.trade['sell_qty']+order['qty']
                    self.trade['sell_quote'] = self.trade['sell_quote']+round(order['qty']*order['price'],self.qd_quote)            
            
            if (self.trade['buy_qty'] == self.trade['sell_qty']) or (self.trade['buy_quote'] == self.trade['sell_quote']):
                start = self.trade['start']
                buy_price = round(self.trade['buy_quote']/self.trade['buy_qty'],self.qd_price)
                qty = self.trade['buy_qty']
                end = self.trade['end']
                sell_price = round(self.trade['sell_quote']/self.trade['sell_qty'],self.qd_price)
                flag = self.trade['flag']
                dif = self.trade['end'].to_pydatetime() - self.trade['start'].to_pydatetime()
                days = dif.total_seconds() / 60 / 60 / 24
                result_usd = self.trade['sell_quote'] - self.trade['buy_quote'] - self.trade['comision']
                result_perc = round((((sell_price/buy_price)-1)*100) - ((self.exch_comision_perc) * 2) , 2)
                trade = pd.DataFrame([[start,buy_price,qty,end,sell_price,flag,days,result_usd,result_perc]], columns=self.trades_columns)
                self.trades = pd.concat([self.trades, trade], ignore_index=True)
                
                self.trade = {}


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
        klines = self.signal(klines)
        
        #quitando las velas previas a la fecha de start
        self.klines = klines[klines['datetime'] >= pd.to_datetime(from_date)]
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
        quote_to_hold = round( self.quote_qty*(self.quote_perc/100) , self.qd_quote )
        qty_to_hold = round( ( quote_to_hold / price_to_hold ) , self.qd_qty ) 
        usd_in_hold = round( self.quote_qty - quote_to_hold , self.qd_quote )
        self.klines['base_qty'] = 0.0
        self.klines['quote_qty'] = 0.0
        self.klines['usd_hold'] = round( self.klines['open'] * qty_to_hold + usd_in_hold, self.qd_quote )

        self.klines['unix_dt'] = (self.klines['datetime'] - dt.datetime(1970, 1, 1)).dt.total_seconds() * 1000 +  10800000

        #Se ejecuta la funcion next para cada registro del dataframe
        proc_start = dt.datetime.now()
        self.klines['usd_strat'] = self.klines.apply(self._next, axis=1)
             
        
        print('')
        proc_end = dt.datetime.now()
        proc_diff = proc_end-proc_start
        print('Duracion: ',f"Proceso demoro {proc_diff.total_seconds() / 60:.4f} minutos.")

        ms_x_kline = (proc_diff.total_seconds()*1000)/(velas*1000)
        print('Milisegundos x Vela: ',ms_x_kline*1000)
        self.cancel_open_orders()

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

        rename_columns = {'unix_dt': 'dt', 
                          'open': 'o', 
                          'high': 'h', 
                          'low': 'l', 
                          'close': 'c', 
                          'volume': 'v', 
                          'usd_hold': 'uH', 
                          'usd_strat': 'uW'}
        ohlc = new_df[['unix_dt','open','high','low','close','volume','usd_hold','usd_strat']].rename(columns=rename_columns).to_dict(orient='records')
    
        new_df = self.klines[['unix_dt','signal','low','high']]
        sB = self.klines[self.klines['signal']=='COMPRA'][['unix_dt','low']].rename(columns={'unix_dt':'dt','low':'sB'}).to_dict(orient='records')
        sS = self.klines[self.klines['signal']=='VENTA'][['unix_dt','high']].rename(columns={'unix_dt':'dt','high':'sS'}).to_dict(orient='records')
        events = sB+sS

        if to_get=='ind':
            return self.get_resultados()
        
        elif to_get=='completed':

            self.make_trades()
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
                'data': [], 
                'events': [],
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
                    '',
                    '',
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

            #Ordenes ejecutadas a Events
            by = self.orders[self.orders['side']==self.ORD_SIDE_BUY][['unix_dt','price']].rename(columns={'unix_dt':'dt','price':'by'}).to_dict(orient='records')
            ventas = self.orders['side']==self.ORD_SIDE_SELL
            signal = self.orders['flag']==self.ORD_FLAG_SIGNAL
            sls = self.orders[ventas & signal][['unix_dt','price']].rename(columns={'unix_dt':'dt','price':'sls'}).to_dict(orient='records')
            signal = self.orders['flag']==self.ORD_FLAG_STOPLOSS
            slsl = self.orders[ventas & signal][['unix_dt','price']].rename(columns={'unix_dt':'dt','price':'slsl'}).to_dict(orient='records')
            signal = self.orders['flag']==self.ORD_FLAG_TAKEPROFIT
            sltp = self.orders[ventas & signal][['unix_dt','price']].rename(columns={'unix_dt':'dt','price':'sltp'}).to_dict(orient='records')

            events += by+sls+slsl+sltp

            res['data'] = ohlc
            res['events'] = events
            
            res['brief'] = self.get_brief()
                            
            return res
    
    def _next(self,row):
            
        self.k_high = row['high']
        self.k_low = row['low']
        self.price = row['open']
        self.unix_dt = row['unix_dt']
        self.datetime = row['datetime']

        #self.update_pos_limits()

        if self.check_open_orders(): #Devuelve True si se ejecuto alguna orden abierta (Limit o Trail)
            self.cancel_open_orders()
        else:
            self.next()

        usd_strat = round( self.price * self.wallet_base + self.wallet_quote, self.qd_quote )
        
        self.signal = row['signal']
        return usd_strat

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
        dias_trades = self.trades['days'].sum()
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
        trades_desc = self.trades.describe()
        trades_tot = self.trades['start'].count()
        
        if trades_tot > 0:

            trades_pos = np.where(self.trades['result_perc'] > 0, 1, 0).sum()
            ratio_trade_pos = (trades_pos/trades_tot)*100 
            max_ganancia = trades_desc.loc['max', 'result_perc']
            max_perdida = trades_desc.loc['min', 'result_perc']
            ratio_perdida_ganancia = self.ind_ratio_ganancia_perdida(self.trades)
            ratio_max_perdida_ganancia = ((-max_ganancia) / max_perdida) if max_ganancia != 0 else float('inf')
            trades_x_mes = trades_tot / ( dias_operando / self.DIAS_X_MES)
            maximo_operaciones_negativas_consecutivas = self.ind_maximo_operaciones_negativas_consecutivas(self.trades)

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
            ratio_sortino_modificado = self.ind_ratio_sortino_modificado(self.trades,umbral_objetivo_riesgo)


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

        df_trades = self.trades
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