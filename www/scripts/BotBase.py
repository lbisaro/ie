from bot.models import *
import scripts.functions as fn
from django.utils import timezone
from datetime import datetime
import pandas as pd
import numpy as np

class BotBase():
    SIDE_BUY = 0
    SIDE_SELL = 1

    FLAG_SIGNAL = 0
    FLAG_STOPLOSS = 1
    FLAG_TAKEPROFIT = 2

    method = 'LONG' # 'SHORT

    DIAS_X_MES = 30.4375 #Resulta de tomar 3 años de 365 dias + 1 de 366 / 4 años / 12 meses

    quote_qty = 0
    interval_id = ''
    bot_id = None

    ### Informacion para Backtesting
    backtesting = False
    bt_index = None #Almacena el datetime de la siguiente vela en el loop de backtesting 
    wallet_base = 0.0
    wallet_quote = 0.0
    exch_comision_perc = 0.2 #0.4% - Comision por operacion de compra o venta

    row_signal = 'NEUTRO'

    res = {
        'error': None,
        'symbol': '',
        'periods': 0,
        'from': '',
        'to': '',
        'brief': [],
        'duration_klines': 0.0,
        'duration_proc': 0.0,
        'wallet': {
            'base_asset': 0.0,
            'quote_asset': 0.0,
        },
        'orders': [],
        'trades': [],
        'data': [],
        'order_side': { 
            SIDE_BUY:'BUY',
            SIDE_SELL:'SELL',
            },
        'order_flag': { 
            FLAG_SIGNAL:'SIGNAL',
            FLAG_STOPLOSS:'STOP-LOSS',
            FLAG_TAKEPROFIT:'TAKE-PROFIT',
            },
    }

    pos = {}

    ### Fin - Informacion para Backtesting

    def __init__(self):
        pass

    def get_signal(self):
        pass

    def reset_res(self):
        self.res['error'] = None
        self.res['data'] = []
        self.res['orders'] = []
        self.res['trades']= []
        self.res['events']= []
        self.res['brief']= []
    
    def reset_pos(self):
        self.pos = {
           'start': None,
           'buy_price': 0.0,
           'qty': 0.0,
           'end': None,
           'sell_price': 0.0,
           'flag': 0,
           'days': 0,
           'result_usd': 0,
           'result_perc': 0,
           'max': 0,
           'min': 0,
           'mef':0,
           'mea': 0,
           }
    def update_pos(self,price_low,price_high):
        if price_high > self.pos['max']:
            self.pos['max'] = price_high
        if price_low < self.pos['min']:
            self.pos['min'] = price_low
        
    def open_pos(self,dt,price,qty):
        self.reset_pos()
        self.pos['start'] = dt
        self.pos['buy_price'] = price
        self.pos['qty'] = qty
        self.pos['max'] = price
        self.pos['min'] = price
    
    def close_pos(self,dt,price,flag):
        self.pos['end'] = dt
        self.pos['sell_price'] = price
        self.pos['flag'] = flag
        
        #Calculos
        dif = datetime.strptime(self.pos['end'], "%Y-%m-%d %H:%M") - datetime.strptime(self.pos['start'], "%Y-%m-%d %H:%M")
        days = dif.total_seconds() / 60 / 60 / 24

        sell = self.pos['sell_price']*self.pos['qty']
        buy = self.pos['buy_price']*self.pos['qty']
        comision = sell * (self.exch_comision_perc/100) + buy * (self.exch_comision_perc/100)
        self.pos['days'] =  days
        self.pos['result_usd'] = round( sell - buy - comision, 2)
        self.pos['result_perc'] = round((((self.pos['sell_price']/self.pos['buy_price'])-1)*100) - ((self.exch_comision_perc) * 2) , 2)
        
        
        trade = [
                self.pos['start'],
                self.pos['buy_price'],
                self.pos['qty'],
                self.pos['end'],
                self.pos['sell_price'],
                self.pos['flag'],
                self.pos['days'],
                self.pos['result_usd'],
                self.pos['result_perc'],
                0,
                2,
                ]
        self.res['trades'].append(trade)
        self.reset_pos()

   
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
    
    def bt_order_market_buy(self,qty,price,flag):
        return self.bt_order_market(self.SIDE_BUY,qty,price,flag)

    def bt_order_market_sell(self,qty,price,flag):
        return self.bt_order_market(self.SIDE_SELL,qty,price,flag)

    def bt_order_market(self,side,qty,price,flag):
        symbol = self.base_asset+self.quote_asset

        strFlag = 'Signal'
        if flag == self.FLAG_STOPLOSS:
            strFlag = 'Stop-Loss'
        elif flag == self.FLAG_TAKEPROFIT:
            strFlag = 'Take-Profit'

    
        quote_qty = round( ( qty * price ) , self.qd_quote )
        comision = quote_qty*self.exch_comision_perc/100
        order = [
            self.bt_index,
            symbol,
            side,
            qty,
            price,
            flag,
            round(comision,4),
        ] 
        if side == self.SIDE_SELL:
            if self.wallet_base - qty >= 0:
                    
                self.wallet_base = round( self.wallet_base - qty , self.qd_qty)
                self.wallet_quote = round( self.wallet_quote + quote_qty - comision , self.qd_quote+2) 
                
                self.res['orders'].append(order)
                if self.method == 'LONG':
                    self.close_pos(self.bt_index,price,flag)
                elif self.method == 'SHORT':
                    self.open_pos(self.bt_index,price,qty)
            else:
                return None

        elif side == self.SIDE_BUY:
            if self.wallet_quote - quote_qty >= 0:
                self.wallet_base = round( self.wallet_base + qty , self.qd_qty)
                self.wallet_quote = round( self.wallet_quote - quote_qty - comision , self.qd_quote+2)

                self.res['orders'].append(order)
                if self.method == 'LONG':
                    self.open_pos(self.bt_index,price,qty)
                elif self.method == 'SHORT':
                    self.close_pos(self.bt_index,price,flag)
            else:
                return None

        self.res['wallet']['base_asset'] = self.wallet_base
        self.res['wallet']['quote_asset'] = self.wallet_quote
        return order
    
    def market_buy(self,exchange,symbol,qty,flag):
        return self.market(exchange,self.SIDE_BUY,symbol,qty,flag)

    def market_sell(self,exchange,symbol,qty,flag):
        return self.market(exchange,self.SIDE_SELL,symbol,qty,flag)

    def market(self,exchange,side,symbol,qty,flag):
        
        if side == self.SIDE_BUY:
            str_side = 'BUY'
            order = exchange.order_market_buy(symbol=symbol, qty= qty)
        else:
            str_side = 'SELL'
            order = exchange.order_market_sell(symbol=symbol, qty= qty)

        """
        Binance order status:

        ORDER_STATUS_NEW = 'NEW'
        ORDER_STATUS_PARTIALLY_FILLED = 'PARTIALLY_FILLED'
        ORDER_STATUS_FILLED = 'FILLED'
        ORDER_STATUS_CANCELED = 'CANCELED'
        ORDER_STATUS_PENDING_CANCEL = 'PENDING_CANCEL'
        ORDER_STATUS_REJECTED = 'REJECTED'
        ORDER_STATUS_EXPIRED = 'EXPIRED'
        """
        
        if order['status'] != 'CANCELED' and order['status'] != 'REJECTED' and order['status'] != 'EXPIRED':
            completed = 1 if order['status'] == 'FILLED' else 0
            if completed == 1:
                price = round(float(order['cummulativeQuoteQty'])/float(order['executedQty']),self.qd_price)
                qty = round(float(order['executedQty']),self.qd_qty)
            
            from bot.models import Order
            from bot.model_kline import Symbol
            symbol_obj = Symbol.objects.get(symbol=self.symbol)
            bot_order = Order()
            bot_order.bot_id = self.bot_id
            bot_order.datetime = timezone.now() - pd.Timedelta('3 hr')
            bot_order.symbol = symbol_obj
            bot_order.side = side
            bot_order.flag = flag
            bot_order.completed = completed
            if completed:
                bot_order.price = price
            else:
                bot_order.price = 0
            bot_order.qty = qty
            bot_order.orderid = order['orderId']
            bot_order.pos_order_id = 0
            bot_order.save()
            return True
                
        return False 
    
    def get_resultados(self):

        kline_ini = self.klines.loc[self.klines.index[0]]
        kline_end = self.klines.loc[self.klines.index[-1]]

        df_trades = pd.DataFrame(self.res['trades'], 
                                 columns = ['start','buy_price','qty','end','sell_price','flag','days','result_usd','result_perc','mef','mea'])
        df_data = pd.DataFrame(self.res['data'], 
                                 columns = ['dt','o','h','l','c','v','sB','sS','by','sls','slsl','sltp','flag','uH','uW'])

        dif_days = kline_end['datetime'] - kline_ini['datetime']
        dias_operando = round(dif_days.total_seconds() / 3600 / 24,1)
        dias_trades = df_trades['days'].sum()
        dias_sin_operar = dias_operando - dias_trades
        ratio_dias_sin_operar = (dias_sin_operar/dias_operando)*100 if dias_operando > 0 else 0.0

        trades_desc = df_trades.describe()
        trades_tot = df_trades['start'].count()

        #if dias_operando > 0 and trades_tot > 0:
            

        mea = df_trades['mea'].dropna().describe()
        mea_promedio = (mea['mean'] + mea['75%'])/2 if trades_tot > 0 else 0.0
        mef = df_trades['mef'].dropna().describe()
        mef_promedio = (mef['mean'] + mef['75%'])/2 if trades_tot > 0 else 0.0
        
        trades_pos = np.where(df_trades['result_perc'] > 0, 1, 0).sum()
        ratio_trade_pos = (trades_pos/trades_tot)*100 if trades_tot > 0 else 0.0
        max_ganancia = trades_desc.loc['max', 'result_perc'] if trades_pos > 0 else 0.0
        max_perdida = trades_desc.loc['min', 'result_perc'] if trades_pos > 0 else 0.0
        ratio_perdida_ganancia = self.ind_ratio_ganancia_perdida(df_trades) if trades_pos > 0 else 0.0
        ratio_max_perdida_ganancia = ((-max_ganancia) / max_perdida) if max_perdida != 0 else 0.0
        trades_x_mes = trades_tot / ( dias_operando / self.DIAS_X_MES) if dias_operando != 0 else 0.0
        maximo_operaciones_negativas_consecutivas = self.ind_maximo_operaciones_negativas_consecutivas(df_trades)

        volatilidad_cap = self.ind_volatilidad(df_data,'uW')
        volatilidad_sym = self.ind_volatilidad(df_data,'uH')
        ratio_volatilidad = (volatilidad_cap/volatilidad_sym)*100 if volatilidad_sym != 0 else 0.0
        max_drawdown_cap = self.ind_maximo_drawdown(df_data,'uW')
        max_drawdown_sym = self.ind_maximo_drawdown(df_data,'uH')
        ratio_max_drawdown = (max_drawdown_cap/max_drawdown_sym)*100 if max_drawdown_sym != 0 else 0.0
        max_drawup_cap = self.ind_maximo_drawup(df_data,'uW')
        max_drawup_sym = self.ind_maximo_drawup(df_data,'uH')
        ratio_max_drawup = (max_drawup_cap/max_drawup_sym)*100  if max_drawup_sym != 0 else 0.0
        cagr = self.ind_cagr(df_data)
        ratio_calmar = self.ind_ratio_calmar(df_data) if trades_pos > 0 else 0.0
        modificacion_sharpe = self.ind_indice_modificacion_sharpe(df_data) if trades_pos > 0 else 0.0
        ratio_cagr_drawdown = (cagr/max_drawdown_cap)*100 if max_drawdown_cap != 0 else 0.0

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

    def get_brief(self):
        kline_ini = self.klines.loc[self.klines.index[0]]
        kline_end = self.klines.loc[self.klines.index[-1]]

        df_trades = pd.DataFrame(self.res['trades'], 
                                 columns = ['start','buy_price','qty','end','sell_price','flag','days','result_usd','result_perc','mef','mea'])
        df_data = pd.DataFrame(self.res['data'], 
                                 columns = ['dt','o','h','l','c','v','sB','sS','by','sls','slsl','sltp','flag','uH','uW'])
        brief = []


        #general
        symbol = self.res['symbol']
        intervalo = fn.get_intervals(self.interval_id,'binance') 
        last_close = float(kline_end['close'])
        usd_final =  self.wallet_quote + self.wallet_base*last_close
        resultado_usd = usd_final-self.quote_qty
        resultado_perc = (resultado_usd/self.quote_qty)*100
        dif_days = kline_end['datetime'] - kline_ini['datetime']
        dias_operando = round(dif_days.total_seconds() / 3600 / 24,1)
        resultado_mensual = (resultado_perc/dias_operando)*self.DIAS_X_MES
        dias_trades = df_trades['days'].sum()
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
        brief.append(['general', 'Periodo',    
                      self.res['from']+' - '+self.res['to'] ])   
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
        trades_desc = df_trades.describe()
        trades_tot = df_trades['start'].count()
        
        #calculo de MEA y MEF
        mea = df_trades['mea'].dropna().describe()
        mef = df_trades['mef'].dropna().describe()

        if mea['count'] > 0:
            mea_str = str(round( (mea['mean']+mea['75%'])/2 ,2) )+'%'
        else:
            mea_str = 'No aplica'

        if mef['count'] > 0:
            mef_str = str(round( (mef['mean']+mef['75%'])/2 ,2) )+'%'
        else:
            mef_str = 'No aplica'
        
        if trades_tot > 0:

            trades_pos = np.where(df_trades['result_perc'] > 0, 1, 0).sum()
            ratio_trade_pos = (trades_pos/trades_tot)*100 
            max_ganancia = trades_desc.loc['max', 'result_perc']
            max_perdida = trades_desc.loc['min', 'result_perc']
            ratio_perdida_ganancia = self.ind_ratio_ganancia_perdida(df_trades)
            ratio_max_perdida_ganancia = ((-max_ganancia) / max_perdida) if max_ganancia != 0 else float('inf')
            trades_x_mes = trades_tot / ( dias_operando / self.DIAS_X_MES)
            maximo_operaciones_negativas_consecutivas = self.ind_maximo_operaciones_negativas_consecutivas(df_trades)

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
            
            brief.append(['operaciones', 'Max.Excursion Adversa',    
                        mea_str])    
            brief.append(['operaciones', 'Max.Excursion Favorable',    
                        mef_str])    
            

            #indicadores
            volatilidad_cap = self.ind_volatilidad(df_data,'uW')
            volatilidad_sym = self.ind_volatilidad(df_data,'uH')
            max_drawdown_cap = self.ind_maximo_drawdown(df_data,'uW')
            max_drawdown_sym = self.ind_maximo_drawdown(df_data,'uH')
            max_drawup_cap = self.ind_maximo_drawup(df_data,'uW')
            max_drawup_sym = self.ind_maximo_drawup(df_data,'uH')

            cagr = self.ind_cagr(df_data)
            ratio_sharpe = self.ind_ratio_sharpe(df_data)
            risk_free_rate=0.045
            ratio_sortino = self.ind_ratio_sortino(df_data, risk_free_rate)
            ratio_ulcer = self.ind_ratio_ulcer(df_data)
            ratio_calmar = self.ind_ratio_calmar(df_data)
            modificacion_sharpe = self.ind_indice_modificacion_sharpe(df_data)
            umbral_objetivo_riesgo = 0.02  # Umbral objetivo de riesgo: 2%
            ratio_sortino_modificado = self.ind_ratio_sortino_modificado(df_trades,umbral_objetivo_riesgo)


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
        returns = df_data['uW'].pct_change()
        sharpe_ratio = (self.ind_cagr(df_data) - risk_free_rate) / self.ind_volatilidad(df_data,'uW')
        return sharpe_ratio
    
    def ind_cagr(self, df_data):
        # CAGR (Compound Annual Growth Rate).
        df_data_ini = df_data.loc[df_data.index[0]]
        df_data_end = df_data.loc[df_data.index[-1]]
        dif_days = df_data_end['dt'] - df_data_ini['dt'] #Diferencia de DateTeim en millisegundos

        # Calcular la diferencia en días
        start_date = datetime.utcfromtimestamp(df_data_ini['dt'] / 1000.0)
        end_date = datetime.utcfromtimestamp(df_data_end['dt'] / 1000.0)
        dif_days = (end_date - start_date).days
        years = dif_days / 365
       
        data = df_data['uW']
        return ((data.iloc[-1] / data.iloc[0]) ** (1 / years) - 1)*100
    
    def ind_ratio_sortino(self, df_data, risk_free_rate):
        df_data['retorno_diario'] = df_data['uW'].pct_change()
        negative_returns = df_data[df_data['retorno_diario'] < 0]['retorno_diario'].std() * np.sqrt(360)
        sortino_ratio = (self.ind_cagr(df_data) - risk_free_rate) / negative_returns
        return sortino_ratio
    
    def ind_drawdowns(self, df_data):
    # Esta función calcula los drawdowns a partir de los datos del capital acumulado.
        data = df_data['uW']
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
        volatilidad = self.ind_volatilidad(df_data,'uW')
        max_drawdown = self.ind_maximo_drawdown(df_data,'uW')
        sharpe_ratio = self.ind_ratio_sharpe(df_data, risk_free_rate=risk_free_rate)
        indice_modificacion_sharpe = (cagr - risk_free_rate) / (volatilidad * abs(max_drawdown) * sharpe_ratio)

        return indice_modificacion_sharpe
    
    def ind_ratio_calmar(self, df_data):
        # Esta función calcula el Ratio de Calmar.
        cagr = self.ind_cagr(df_data)
        max_drawdown = self.ind_maximo_drawdown(df_data,'uW')
        ratio_calmar = cagr / abs(max_drawdown)
        return ratio_calmar
    
    def ind_ratio_sortino_modificado(self, df_trades, umbral_objetivo_riesgo):
        # Esta función calcula el Ratio de Sortino Modificado.
        retorno_total = df_trades['result_usd'].sum()
        df_trades['retorno_diario'] = df_trades['result_usd'] / self.quote_qty
        df_trades['retorno_negativo'] = df_trades['retorno_diario'].apply(lambda x: x if x < 0 else 0)
        desviacion_negativa = df_trades['retorno_negativo'].std()
        ratio_sortino_modificado = (retorno_total - umbral_objetivo_riesgo) / desviacion_negativa
        return ratio_sortino_modificado