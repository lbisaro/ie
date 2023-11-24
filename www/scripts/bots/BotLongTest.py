from bot.model_kline import *
from django.db.models import Q
import numpy as np
from ..BotBaseLong import BotBaseLong
from indicators import find_pivots,donchian

class BotLongTest(BotBaseLong):

    descripcion = 'Opera en largo \n'\
                  'Ejecuta la compra al recibir una señal de Compra, '\
                  'y cierra la operación por Stop Loss o Take Profit (Si se definen con un % mayor a cero) '\
                  'o cuando recibe una señal de Venta.'
    
    def signal(self,df):

        """ PIVOTS 
        df['ma'] = df['close'].rolling(window=21).mean()
        
        df = find_pivots(df, dev_threshold = 3.0)
        
        df['compra'] = (df['close'] < df['ma']) & (df['min_pivot'] > 0)
        df['venta']  = (df['close'] > df['ma']) & (df['max_pivot'] > 0)

        df['signal'] = np.where(df['compra'], 'COMPRA', 'NEUTRO')
        df['signal'] = np.where(df['venta'], 'VENTA',df['signal'])
        """
        df = donchian(df)
        df['dch_amp'] = df['dch_max'] - df['dch_min']
        df['compra'] = (df['close'] < df['dch_mean']) & (df['dch_amp'] == df['dch_amp'].shift(2)) & (df['dch_amp'].shift(2) > df['dch_amp'].shift(3))
        df['venta']  = (df['close'] > df['dch_mean']) & (df['dch_amp'] == df['dch_amp'].shift(2)) & (df['dch_amp'].shift(2) > df['dch_amp'].shift(3))

        df['signal'] = np.where(df['compra'], 'COMPRA', 'NEUTRO')
        df['signal'] = np.where(df['venta'], 'VENTA',df['signal'])

        return df


