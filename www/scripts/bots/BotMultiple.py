from bot.model_kline import *
import numpy as np
from ..Bot_CoreLong import Bot_CoreLong
import ta

class BotMultiple(Bot_CoreLong):

    parametros = {'symbol':  {  
                        'c' :'symbol',
                        'd' :'Par',
                        'v' :'BTCUSDT',
                        't' :'symbol',
                        'pub': True,
                        'sn':'Sym',},
                 'quote_perc': {
                        'c' :'quote_perc',
                        'd' :'Operacion sobre capital',
                        'v' :'100',
                        't' :'perc',
                        'pub': True,
                        'sn':'Quote', },
                'stop_loss': {
                        'c' :'stop_loss',
                        'd' :'Stop Loss',
                        'v' :'3.5',
                        't' :'perc',
                        'pub': True,
                        'sn':'SL', },
                'take_profit': {
                        'c' :'take_profit',
                        'd' :'Take Profit',
                        'v' :'1.2',
                        't' :'perc',
                        'pub': True,
                        'sn':'TP', },
                'interes': {
                        'c' :'interes',
                        'd' :'Tipo de interes',
                        'v' :'c',
                        't' :'t_int',
                        'pub': True,
                        'sn':'Int', },
                'trail': {
                        'c' :'trail',
                        'd' :'Trail',
                        'v' : 0,
                        't' :'bin',
                        'pub': True,
                        'sn':'Trail', },
                
                'desicion': {
                        'c' :'desicion',
                        'd' :'Desicion',
                        'v' : 1,
                        't' :'int',
                        'pub': True,
                        'sn':'Desic', },
                } 

    descripcion = 'Bot Core v2 \n'\
                  'Ejecuta la compra al recibir una señal de Compra, '\
                  'y cierra la operación por Stop Loss o Take Profit (Si se definen con un % mayor a cero) '\
                  'El parametro Desicion define que indicadores utilizar'
    
    def check_signal(self,row):
        
        if self.desicion==1:
            if row['rsi_2'] <= 65.681824 and row['ma10_open_ratio'] <= 1.026084 and row['atr'] <= 809.712433 or \
                row['rsi_2'] <= 64.024189 and row['ma10_open_ratio'] > 1.051603  and row['williams_r'] > -92.832016 : 
                return 'COMPRA'
            
        elif self.desicion==2:
            rsi_2_threshold = 30  # Ejemplo de valor de umbral para RSI de 2 días
            ma10_open_ratio_threshold = 1.05  # Ejemplo de valor de umbral para ma10_open_ratio

            if row['rsi_2'] <= rsi_2_threshold and row['ma10_open_ratio'] > ma10_open_ratio_threshold:
                return 'COMPRA'
            
        elif self.desicion==3:
            """
            Error en label y vol_sma10
            """
            if row['ma21_open_ratio'] < self.klines['ma21_open_ratio'].quantile(1/3) and \
                row['label'] == 0 and \
                row['williams_r'] > self.klines['williams_r'].quantile(2/3) and \
                row['ao'] > self.klines['ao'].quantile(2/3) and \
                row['vol_sma10'] < self.klines['vol_sma10'].quantile(1/3):
                return 'COMPRA'
        
        elif self.desicion==4:
            """
            Error en obv_cat
            """
            if (row['obv_cat'] == 'obv_low') and (row['ma21_open_ratio_cat'] == 'ma21_open_ratio_medium') and \
                (row['rsi_2_sma_cat'] == 'rsi_2_sma_medium') and (row['williams_r_cat'] == 'williams_r_low') and \
                (row['stoch_d_cat'] == 'stoch_d_low'):
                return 'COMPRA'
            
        elif self.desicion==5:
            if row['rsi_2'] <= 20.976684 and row['rsi_14_sma'] <= 36.490307 and row['stoch_k'] <= 38.221718:
                return 'COMPRA'

        elif self.desicion==6:
            if row['rsi_2'] <= 20.976684 and row['rsi_2'] <= 77.089401 and row['adx_neg'] <= 37.914232 and row['rsi_2_sma'] <= 84.663757:
                return 'COMPRA'

        elif self.desicion==7:
            if row['rsi_2'] <= 78.369846 and row['rsi_2_sma'] > 83.796917 and row['rsi_2'] > 21.195584 and  row['vol_sma21_ratio'] > 0.880919:
                return 'COMPRA'

        elif self.desicion==8:
            if row['rsi_2'] <= 78.369846 and row['rsi_2_sma'] <= 83.796917 and row['rsi_2'] > 21.195584 and row['rsi_14'] > 26.311381:
                return 'COMPRA'

        elif self.desicion==9:
            if row['rsi_2'] <= 78.369846 and row['rsi_2_sma'] <= 83.796917 and row['rsi_2'] > 21.195584 and row['rsi_14'] > 26.311381 and row['vol_sma21_ratio'] > 0.880919:
                return 'COMPRA'

        elif self.desicion==10:
            if row['rsi_2'] <= 79.941154 and row['ma21_open_ratio']  <= 0.863092 and row['ma10_open_ratio'] <= 0.868698:
                """
                Esto no se puede hacer porque en el vivo se desconocen los proximos 3 dias
                Crear una función que verifique si los mínimos de los próximos 3 días son ascendentes.
                """
                return 'COMPRA'

        elif self.desicion==11:
            if row['rsi_2'] <= 79.941154 and row['ma21_open_ratio']  <= 0.863092:
                return 'COMPRA'

        elif self.desicion==12:
            if row['rsi_2'] > 79.941154  and row['atr']  <= 312.867615:
                return 'COMPRA'

        elif self.desicion==13:
            if row['rsi_2'] <= 80.201191   and row['rsi_2']  > 36.969124 and row['ma10_open_ratio']  <= 1.018904 and row['atr']  <= 314.899307:
                return 'COMPRA'

        elif self.desicion==14:
            if row['rsi_2'] > 80.201191   and row['obv']  <= 2154016.500000 and row['atr']  <= 312.867615 and row['obv']  > -3471446.250000:
                return 'COMPRA'

        elif self.desicion==15:
            if row['rsi_2'] > 80.201191   and row['obv']  > 2154016.500000 and row['macd']  <= 4349.813232 and row['stoch_d']  > 90.036484 :
                return 'COMPRA'

        
        
        return 'NEUTRO'
    
    
    def start(self):
        warnings.filterwarnings("ignore") #Se evita el warning generado por el indicador

        # Añadiendo indicadores


        # Añadir medias móviles de volumen y su cociente

        self.klines['vol_sma21_ratio'] = self.klines['volume'].rolling(window=21).mean() / self.klines['volume']
        self.klines['vol_sma10_ratio'] = self.klines['volume'].rolling(window=10).mean() / self.klines['volume']
        self.klines['vol_sma50_ratio'] = self.klines['volume'].rolling(window=50).mean() / self.klines['volume']
        # Añadir MACD
        self.klines['macd'] = ta.trend.MACD(self.klines['close']).macd()

        # Añadir CCI
        self.klines['cci'] = ta.trend.CCIIndicator(high=self.klines['high'], low=self.klines['low'], close=self.klines['close']).cci()

        # Añadir Stochastic Oscillator
        stoch = ta.momentum.StochasticOscillator(high=self.klines['high'], low=self.klines['low'], close=self.klines['close'])
        self.klines['stoch_k'] = stoch.stoch()
        self.klines['stoch_d'] = stoch.stoch_signal()

        # Añadir Awesome Oscillator
        self.klines['ao'] = ta.momentum.AwesomeOscillatorIndicator(high=self.klines['high'], low=self.klines['low']).awesome_oscillator()

        # Añadir On-Balance Volume
        self.klines['obv'] = ta.volume.OnBalanceVolumeIndicator(close=self.klines['close'], volume=self.klines['volume']).on_balance_volume()

        # Añadir Average True Range
        self.klines['atr'] = ta.volatility.AverageTrueRange(high=self.klines['high'], low=self.klines['low'], close=self.klines['close']).average_true_range()

        self.klines['rsi_2'] = ta.momentum.RSIIndicator(self.klines['close'], window=2).rsi()
        self.klines['rsi_14'] = ta.momentum.RSIIndicator(self.klines['close'], window=14).rsi()
        self.klines['rsi_2_sma'] = self.klines['rsi_2'].rolling(window=10).mean()
        self.klines['rsi_14_sma'] = self.klines['rsi_14'].rolling(window=14).mean()
        self.klines['adx'] = ta.trend.ADXIndicator(self.klines['high'], self.klines['low'], self.klines['close'], window=14).adx()
        self.klines['adx_pos'] = ta.trend.ADXIndicator(self.klines['high'], self.klines['low'], self.klines['close'], window=14).adx_pos()
        self.klines['adx_neg'] = ta.trend.ADXIndicator(self.klines['high'], self.klines['low'], self.klines['close'], window=14).adx_neg()
        self.klines['ma21_open_ratio'] = self.klines['close'].rolling(window=21).mean() / self.klines['open']
        self.klines['ma10_open_ratio'] = self.klines['close'].rolling(window=10).mean() / self.klines['open']
        self.klines['williams_r'] = ta.momentum.WilliamsRIndicator(self.klines['high'], self.klines['low'], self.klines['close'], lbp=14).williams_r()


        self.klines['signal'] = self.klines.apply(self.check_signal, axis=1)



