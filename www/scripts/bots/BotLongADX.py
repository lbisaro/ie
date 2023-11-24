from bot.model_kline import *
from django.db.models import Q
import pandas as pd
import numpy as np
import time
from ta.trend import ADXIndicator
import warnings
from scripts.Exchange import Exchange
import functions as fn
from ..BotBaseLong import BotBaseLong



class BotLongADX(BotBaseLong):

    descripcion = 'Opera en largo \n'\
                  'Ejecuta la compra al recibir una señal de Compra, '\
                  'y cierra la operación por Stop Loss o Take Profit (Si se definen con un % mayor a cero) '\
                  'o cuando recibe una señal de Venta.'
    
    def signal(self,df):
        ADX_PERIODO = 14
        warnings.filterwarnings("ignore") #Se evita el warning generado por el indicador

        iADX = ADXIndicator(df['high'], df['low'],df['close'],ADX_PERIODO, False)
        
        df['ADX'] = iADX.adx()
        df['ADX+'] = iADX.adx_pos()
        df['ADX-'] = iADX.adx_neg()
        df['Posicion'] = np.where(np.logical_and(df['ADX-'] < df['ADX+'], (df['ADX+'] - df['ADX-']) > 1), 'COMPRA', 'VENTA')
        df['Alternancia'] = (df[['Posicion']] != df[['Posicion']].shift()).any(axis=1)
        df['Orden'] = np.where(df['Alternancia'], df['Posicion'], '')
        
        df['Orden_Precio'] = df['open']
        df['signal'] = np.where(df['Alternancia'], df['Posicion'], 'NEUTRO')
        
        warnings.filterwarnings("default")
        
        return df


