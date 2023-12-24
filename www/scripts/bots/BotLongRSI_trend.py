from bot.model_kline import *
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import warnings
from ..BotBaseLong import BotBaseLong



class BotLongRSI_trend(BotBaseLong):


    descripcion = 'Opera en largo \n'\
                  'Ejecuta la compra al recibir una señal de Compra, '\
                  'y cierra la operación por Stop Loss o Take Profit (Si se definen con un % mayor a cero) '\
                  'o cuando recibe una señal de Venta.'
    
    def signal(self,df):
        """ Analisis de volatilidad """
        #Calculo de precio de referencia
        min_price = df['low'].min()
        df['price_ref'] = (df['close']/min_price)*10

        #Media movil simple
        df['ma'] = df['price_ref'].rolling(20).mean()

        #Bollinger
        boll = BollingerBands(close=df['price_ref'],window=20,window_dev=2)
        df['bb_ma'] = boll.bollinger_mavg()
        df['bb_h'] = boll.bollinger_hband()
        df['bb_l'] = boll.bollinger_lband()
        df['bb_w'] = boll.bollinger_wband()

        #Esta info se deberia calcular cada 1 dia/semana y almacenarla en la DB, analizando la amplitud del ultimo año
        bb_w_info = df['bb_w'].describe()
        #corte para definir si la aplitud es mayor al estandard
        #df['bb_w_avg'] = bb_w_info['mean']+bb_w_info['std']
        df['bb_w_avg'] = df['bb_w'].rolling(30).mean()


        #Media simple de la amplitud
        df['bb_w_ma'] = df['bb_w'].rolling(7).mean()

        #Analisis de la tendencia
        #Si la amplitud supera el corte hay tendencia
        df['trend'] = np.where((df['bb_w']>df['bb_w_ma']),1,0)

        """ Analisis de señal """
        window = 2
        df['RSI'] = RSIIndicator(df['close'], window, True).rsi()
                
        df['Posicion'] = np.where((df['RSI'] < 20) & (df['trend']>0), 'COMPRA', None)
        df['Posicion'] = np.where((df['RSI'] > 90) , 'VENTA', df['Posicion'])

        df['Alternancia'] = (df[['Posicion']] != df[['Posicion']].shift()).any(axis=1)
        df['signal'] = np.where(df['Alternancia'], df['Posicion'], 'NEUTRO')

        return df


