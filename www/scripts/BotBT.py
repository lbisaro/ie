from bot.models import *
import scripts.functions as fn
from django.utils import timezone
from datetime import datetime
import pandas as pd
import numpy as np

class BotBT():
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

    quote_qty = 0
    interval_id = ''
    bot_id = None
    klines = pd.DataFrame()

    ### Informacion para Backtesting
    backtesting = True
    exch_comision_perc = 0.2 #0.4% - Comision por operacion de compra o venta

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
    
    def get_resultados(self):

        kline_ini = self.klines.iloc[0]
        kline_end = self.klines.iloc[-1]

        dif_days = kline_end['datetime'] - kline_ini['datetime']
        dias_operando = round(dif_days.total_seconds() / 3600 / 24,1)
        dias_trades = self.trades['days'].sum()
        dias_sin_operar = dias_operando - dias_trades
        ratio_dias_sin_operar = (dias_sin_operar/dias_operando)*100 if dias_operando > 0 else 0.0

        trades_desc = self.trades.describe()
        trades_tot = self.trades['start'].count()

        
        
        trades_pos = np.where(self.trades['result_perc'] > 0, 1, 0).sum()
        ratio_trade_pos = (trades_pos/trades_tot)*100 if trades_tot > 0 else 0.0
        max_ganancia = trades_desc.loc['max', 'result_perc'] if trades_pos > 0 else 0.0
        max_perdida = trades_desc.loc['min', 'result_perc'] if trades_pos > 0 else 0.0
        ratio_perdida_ganancia = self.ind_ratio_ganancia_perdida(self.trades) if trades_pos > 0 else 0.0
        ratio_max_perdida_ganancia = ((-max_ganancia) / max_perdida) if max_perdida != 0 else 0.0
        trades_x_mes = trades_tot / ( dias_operando / self.DIAS_X_MES) if dias_operando != 0 else 0.0
        maximo_operaciones_negativas_consecutivas = self.ind_maximo_operaciones_negativas_consecutivas(self.trades)

        volatilidad_cap = self.ind_volatilidad(self.klines,'usd_strat')
        volatilidad_sym = self.ind_volatilidad(self.klines,'usd_hold')
        ratio_volatilidad = (volatilidad_cap/volatilidad_sym)*100 if volatilidad_sym != 0 else 0.0
        max_drawdown_cap = self.ind_maximo_drawdown(self.klines,'usd_strat')
        max_drawdown_sym = self.ind_maximo_drawdown(self.klines,'usd_hold')
        ratio_max_drawdown = (max_drawdown_cap/max_drawdown_sym)*100 if max_drawdown_sym != 0 else 0.0
        max_drawup_cap = self.ind_maximo_drawup(self.klines,'usd_strat')
        max_drawup_sym = self.ind_maximo_drawup(self.klines,'usd_hold')
        ratio_max_drawup = (max_drawup_cap/max_drawup_sym)*100  if max_drawup_sym != 0 else 0.0
        cagr = self.ind_cagr(self.klines)
        ratio_calmar = self.ind_ratio_calmar(self.klines) if trades_pos > 0 else 0.0
        modificacion_sharpe = self.ind_indice_modificacion_sharpe(self.klines) if trades_pos > 0 else 0.0
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
        kline_ini = self.klines.iloc[0]
        kline_end = self.klines.iloc[-1]

        
        brief = []

        #general
        symbol = self.symbol
        intervalo = fn.get_intervals(self.interval_id,'binance') 
        last_close = float(kline_end['Close'])
        usd_final =  self.klines.iloc[-1]['usd_strat']
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