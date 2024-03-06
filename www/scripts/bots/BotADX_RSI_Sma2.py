from bot.model_kline import *
import numpy as np
from ..Bot_CoreLong import Bot_CoreLong
import ta
from ta.trend import ADXIndicator

class BotADX_RSI_Sma2(Bot_CoreLong):

    descripcion = 'Bot Core v2 \n'\
                  'Ejecuta la compra al recibir una señal de Compra, '\
                  'y cierra la operación por Stop Loss o Take Profit (Si se definen con un % mayor a cero) '\
                  'o cuando recibe una señal de Venta.'
    
    
    def start(self):
        ADX_PERIODO = 14
        warnings.filterwarnings("ignore") #Se evita el warning generado por el indicador
        iADX = ADXIndicator(self.klines['high'], self.klines['low'],self.klines['close'],ADX_PERIODO, False)    

        self.klines['rsi_2'] = ta.momentum.RSIIndicator(self.klines['close'], window=2).rsi()
        
        self.klines['sma'] = self.klines['close'].rolling(40).mean()
        #self.klines['ADX'] = iADX.adx()
        self.klines['ADX+'] = iADX.adx_pos()
        self.klines['ADX-'] = iADX.adx_neg()
       

        # Asumiendo que self.klines ya tiene las columnas 'close' y 'sma' definidas.
        condiciones = [
                            # Condición para COMPRA: close > sma Y rsi_14 > 86.899055
                            ((self.klines['ADX+'] - self.klines['ADX-']) > 1 ) & (self.klines['rsi_2'] > 85),
                            
                            # Condición para VENTA: (ADX- > 20) O (close < sma)
                            ((self.klines['ADX-'] > 20) | (self.klines['close'] < self.klines['sma']))
                        ]
                        

        # Las opciones correspondientes a cada condición
        opciones = ['COMPRA', 'VENTA']

        # Aplicamos np.select para asignar los valores en base a las condiciones
        self.klines['Posicion'] = np.select(condiciones, opciones, default='NEUTRO')




        #self.klines['Posicion'] = np.where((self.klines['close'] > self.klines['sma']), 'COMPRA', 'NEUTRO')
        self.klines['Alternancia'] = (self.klines[['Posicion']] != self.klines[['Posicion']].shift()).any(axis=1)

        self.klines['signal'] = self.klines['Posicion']
        #self.klines.drop(['sma','ADX','ADX+','ADX-','Posicion','Alternancia','Alternancia'], axis = 1)
        
        warnings.filterwarnings("default") 

        self.print_orders = False

        """ Valores tomados con el script backtest/test_volatilidad
        self.factor = {}
        self.factor['BNBUSDT'] =  round(1.430209,2)
        self.factor['ADAUSDT'] =  round(1.547063,2)
        self.factor['DOTUSDT'] =  round(1.653493,2)
        self.factor['BTCUSDT'] =  round(1.000000,2)
        self.factor['XRPUSDT'] =  round(1.725560,2)
        self.factor['ETHUSDT'] =  round(1.318775,2)
        self.factor['TRXUSDT'] =  round(1.318829,2) 


        self.stop_loss   = round(self.stop_loss   * self.factor[self.symbol],1)
        self.take_profit = round(self.take_profit * self.factor[self.symbol],1)
        print(self.symbol,' Factor: ',self.factor[self.symbol],' SL: ',self.stop_loss,' TP: ',self.take_profit)
        """
      