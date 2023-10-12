from bot.model_kline import *
from django.db.models import Q
import numpy as np
from ..BotBaseLong import BotBaseLong

class BotLongEMACross(BotBaseLong):

    descripcion = 'Opera en largo \n'\
                  'Ejecuta la compra al recibir una señal de Compra, '\
                  'y cierra la operación por Stop Loss o Take Profit (Si se definen con un % mayor a cero) '\
                  'o cuando recibe una señal de Venta.'
    
    
    def signal(self,df):
        fast = 7
        slow = 14
        df['fast'] = df['close'].ewm(span=fast, adjust=False).mean()
        df['slow'] = df['close'].ewm(span=slow, adjust=False).mean()
        df['cross'] = ((df['fast']/df['slow'])-1)*100

        df['Posicion'] = np.where(df['cross'] > 0, 'COMPRA',None)
        df['Posicion'] = np.where(df['cross'] < 0, 'VENTA',df['Posicion'])

        df['Alternancia'] = np.logical_and( (df[['Posicion']] != df[['Posicion']].shift() ).any(axis=1), (df['cross'].shift() != 0) )
        df['signal'] = np.where(df['Alternancia'], df['Posicion'], 'NEUTRO')
        df['signal'] = np.where(df['cross']==0, 'NEUTRO',df['signal'] )


        return df


