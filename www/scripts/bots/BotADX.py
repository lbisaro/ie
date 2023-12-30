from bot.model_kline import *
import numpy as np
from ..Bot_CoreLong import Bot_CoreLong

class BotADX(Bot_CoreLong):

    descripcion = 'Bot Core v2 \n'\
                  'Ejecuta la compra al recibir una señal de Compra, '\
                  'y cierra la operación por Stop Loss o Take Profit (Si se definen con un % mayor a cero) '\
                  'o cuando recibe una señal de Venta.'
    
    
    def start(self):
        fast = 7
        slow = 14
        self.klines['fast'] = self.klines['close'].ewm(span=fast, adjust=False).mean()
        self.klines['slow'] = self.klines['close'].ewm(span=slow, adjust=False).mean()
        self.klines['cross'] = ((self.klines['fast']/self.klines['slow'])-1)*100

        self.klines['Posicion'] = np.where(self.klines['cross'] > 0, 'COMPRA',None) 
        self.klines['Posicion'] = np.where(self.klines['cross'] < 0, 'VENTA',self.klines['Posicion'])

        self.klines['Alternancia'] = np.logical_and( (self.klines[['Posicion']] != self.klines[['Posicion']].shift() ).any(axis=1), (self.klines['cross'].shift() != 0) )
        self.klines['signal'] = np.where(self.klines['Alternancia'], self.klines['Posicion'], 'NEUTRO')
        self.klines['signal'] = np.where(self.klines['cross']==0, 'NEUTRO',self.klines['signal'] )
        self.klines.drop(columns = ['fast','slow','cross','Posicion','Alternancia'],inplace=True) 

        self.print_orders = False 
