import pandas as pd
import numpy as np


def trend(df):
    window = 3
    ema_fast = 7
    ema_slow = 21

    df['hl2'] = (df['high'] + df['low']) / 2
    df['ema_f'] = df['hl2'].ewm(span=ema_fast, adjust=False).mean()
    df['ema_s'] = df['hl2'].ewm(span=ema_slow, adjust=False).mean()

    df['cross'] = np.where(df['ema_f']>df['ema_s'],1,-1)

    # Contar las veces consecutivas que 'cross' es igual a 1 en las últimas 5 filas
    df['ema_signal'] = np.where(df['cross'].rolling(window=window).sum() == window, 1, 0 )

    # Contar las veces consecutivas que 'cross' es igual a -1 en las últimas 5 filas
    df['ema_signal'] = np.where(df['cross'].rolling(window=window).sum() == -window , -1, df['ema_signal'] )

    df['trend_up'] = np.where(df['ema_signal']>0,(df['ema_f']+df['ema_s'])/2,None)
    df['trend_down'] = np.where(df['ema_signal']<0,(df['ema_f']+df['ema_s'])/2,None)
    df[['high','low','trend_up','trend_down']].plot(figsize=(20,4),style=['#dddddd','#dddddd','g','r'])
    df = df.drop(['hl2','ema_f','ema_s','cross','ema_signal'], axis=1)
    return df

# Función para calcular los pivotes de máximos y mínimos
def find_pivots(df,dev_threshold=0,dev_trend=0.33):
    df['max_pivots'] = None
    df['min_pivots'] = None
    df['max_trend'] = None
    df['min_trend'] = None

    if 1 < dev_trend < 0:
        assert "dev_trend debe ser un valor entre 0 y 1"
    
    dict = df.to_dict(orient='index')
    if dev_threshold == 0:
        df['mean'] = (df['high'] - df['low']) / ((df['high'] + df['low']) / 2) * 100
        dev_threshold = round(df['mean'].mean() * 1.5,3)
        if dev_threshold < 3:
            dev_threshold = 3
    
    max_val = None
    min_val = None
    last = None

    for i in dict:
        high = dict[i]['high']
        low = dict[i]['low']

        if max_val is None or high > max_val:
            max_val = high
        if min_val is None or low < min_val:
            min_val = low

        #Tendencias
        if (max_val- high) / max_val * 100 >= dev_threshold*dev_trend:
            if last is None or last != 'max':
                dict[i]['max_trend'] = max_val
        if (low - min_val) / min_val * 100 >= dev_threshold*dev_trend:
            if last is None or last != 'min':
                dict[i]['min_trend'] = min_val
        
        #Pivots
        if (max_val- high) / max_val * 100 >= dev_threshold:
            if last is None or last != 'max':
                dict[i]['max_pivots'] = max_val
            last = 'max'
            max_val = None
        elif (low - min_val) / min_val * 100 >= dev_threshold:
            if last is None or last != 'min':
                dict[i]['min_pivots'] = min_val
            last = 'min'
            min_val = None

    df = pd.DataFrame.from_dict(dict, orient='index')
    return df


class Fibonacci:
    """
    Uso: ff = Fibonacci().long(df, dev_threshold=0, dev_trend = 0.33)
    """
    
    last_pivots = [['',0],['',0],['',0]]
    last_fibo = None

    def evaluate_long(self, min):
        if self.last_pivots[0][0] == 'min' and self.last_pivots[1][0] == 'max' and self.last_pivots[2][0] == 'min':
            #Si los ultimos 3 pivotes son min, max, min
            if self.last_pivots[0][1] > self.last_pivots[2][1] and self.last_pivots[1][1] > self.last_pivots[0][1]:
                #Si El ultimo min es mayor al primer min, y el max es mayor al ultimo min
                #Hay un pull-back, entonces devuelve el [max,ultimo min]
                return [self.last_pivots[1][1],self.last_pivots[0][1]]
        elif min > 0 and self.last_pivots[0][0] == 'max' and self.last_pivots[1][0] == 'min' :
            #Si no hay un pull-back pero
            #Hay tendencia a un min y los ultimos pivots son max, min  
            if min > self.last_pivots[1][1] and self.last_pivots[0][1] > min:
                #Si el ultimo min es mayor a la tendencia min y el max es mayor al ultimo min
                return [self.last_pivots[0][1],min]
            
        return None

    def add_pivots(self,type,price):
        self.last_pivots[2] = self.last_pivots[1]
        self.last_pivots[1] = self.last_pivots[0]
        self.last_pivots[0] = [type,price]

    def long(self,df,dev_threshold=0,dev_trend = 0.33):
        self.dev_threshold=dev_threshold
        self.dev_trend = dev_trend

        df = df
        df = find_pivots(df,self.dev_threshold,self.dev_trend) 

        df['fibo_0.000'] = None
        df['fibo_1.000'] = None
        df['fibo'] = None

        df_dict = df.to_dict(orient='index')

        self.last_pivots = [['',0],['',0],['',0]]
        self.last_fibo = None

        for i in df.index:
            row = df.loc[i]
            
            if row['max_pivots'] > 0:
                self.add_pivots('max',row['max_pivots'])
            if row['min_pivots'] > 0: 
                self.add_pivots('min',row['min_pivots'])
            
            fibo = self.evaluate_long(row['min_trend'])

            df_dict[i]['fibo'] = 0
            if fibo is not None: 
                if fibo != self.last_fibo:
                    df_dict[i]['fibo'] = 1
                df_dict[i]['fibo_0.000'] = fibo[0]
                df_dict[i]['fibo_1.000'] = fibo[1]
            self.last_fibo = fibo

        df = pd.DataFrame.from_dict(df_dict, orient='index')
        df.reset_index(inplace=True)
        return df

def donchian(df, period = 20):
    df['dch_max'] = df['high'].rolling(window=period).max()
    df['dch_min'] = df['low'].rolling(window=period).min()
    df['dch_mean'] = (df['dch_max']+df['dch_min'])/2
    return df