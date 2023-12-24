from bot.model_kline import *
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
import warnings
from ..BotBaseLong import BotBaseLong



class BotLongRSI(BotBaseLong):


    descripcion = 'Opera en largo \n'\
                  'Ejecuta la compra al recibir una señal de Compra, '\
                  'y cierra la operación por Stop Loss o Take Profit (Si se definen con un % mayor a cero) '\
                  'o cuando recibe una señal de Venta.'
    
    def signal(self,df):
        window = 2
        df['RSI'] = RSIIndicator(df['close'], window, True).rsi()
        df['RSI14'] = RSIIndicator(df['close'], 14, True).rsi()
        
        # Agregando la condición para 'RSI14' en las decisiones de compra y venta
        df['Posicion'] = np.where((df['RSI'] < 20) & ~df['RSI14'].between(30, 70), 'COMPRA', None)
        df['Posicion'] = np.where((df['RSI'] > 90) & ~df['RSI14'].between(30, 70), 'VENTA', df['Posicion'])

        df['Alternancia'] = (df[['Posicion']] != df[['Posicion']].shift()).any(axis=1)
        df['signal'] = np.where(df['Alternancia'], df['Posicion'], 'NEUTRO')

        return df


