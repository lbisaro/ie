import pandas as pd
import numpy as np
from math import floor
from datetime import datetime, timedelta

def get_intervals(i='ALL',c='ALL'):
    columns=['id','interval_id','name','binance','pandas_resample','minutes']
    intervals = pd.DataFrame([['0m01','0m01','1 minuto','1m','1T',1],
                              ['0m05','0m05','5 minutos','5m','5T',5],
                              ['0m15','0m15','15 minutos','15m','15T',15],
                              ['0m30','0m30','30 minutos','30m','30T',30],
                              ['1h01','1h01','1 hora','1h','1H',60],
                              ['1h04','1h04','4 horas','4h','4H',(60*4)],
                              ['2d01','2d01','1 dia','1d','1D',(60*4*24)],
                             ],columns=columns)
    intervals.set_index('id',inplace=True)
    if i=='ALL' and c=='ALL':
        return intervals
    else:
        if i!='ALL' and c=='ALL':
            if i in intervals.index:
                return intervals.loc[i]
            else:
                return None
        elif i!='ALL' and c!='ALL':
            if i in intervals.index:
                if c in intervals.loc[i]:
                    return intervals.loc[i][c]
                else:
                    return None
            else:
                return None
            
def get_binance_intervals():
    intervals = get_intervals()
    return intervals['binance'].values


def get_apply_intervals(dt):

    #Se calcula el time interval con GMT+0 para que Al buscar velas de 4hs o diarias, se obtengan velas cerradas
    dt = dt+timedelta(hours=3)

    hr = dt.strftime('%H')
    mn = dt.strftime('%M')

    whereIn = "'0m01'"
    if mn[1]=='0' or mn[1]=='5':
        whereIn = whereIn + ",'0m05'"
    if mn=='00' or mn=='15' or mn=='30' or mn=='45':
        whereIn = whereIn + ",'0m15'"
    if mn=='00' or mn=='30':
        whereIn = whereIn + ",'0m30'"
    if mn=='00' :
        whereIn = whereIn + ",'1h01'"
    if mn=='00' and (hr=='00' or hr=='04' or hr=='08' or hr=='12' or hr=='16' or hr=='20'):
        whereIn = whereIn + ",'1h04'"
    if mn=='00' and (hr=='21'):
        whereIn = whereIn + ",'2d01'"

    return whereIn

def round_down(num, decs):
    pot = 10**decs
    num = num * pot
    num = floor(num)
    num = num / pot
    return num

def pendiente(y):
    qty = len(y)
    x = np.arange(qty)
    p = np.polyfit(x, y, 1)
    return round(p[0],2)

def ohlc_mirror_v(df):
    """
    Transforma el DF invirtiendo las tendencias, 
    espejando los precios de OHLC de forma vertical
    """
    df.rename(columns={'open':'open_i','close':'close_i','low':'low_i','high':'high_i'},inplace=True)

    open_high = df['high_i'].max()
    open_low  = df['low_i'].min()
    open_mean = (open_high+open_low)/2
    df['open_diff'] = open_mean-df['open_i']
    df['open'] = open_mean + df['open_diff']

    df['close_d'] = df['open_i']-df['close_i']
    df['close'] = df['open']+df['close_d']

    df['high_d'] = df['open_i']-df['high_i']
    df['low'] = df['open']+df['high_d']

    df['low_d'] = df['open_i']-df['low_i']
    df['high'] = df['open']+df['low_d']

    df.drop(columns=['open_i','close_i','low_i','high_i','open_diff','close_d','high_d','low_d'],inplace=True)
    return df

def ohlc_mirror_h(df):
    """
    Transforma el DF colocando al inicio las velas finales y viceversa, 
    espejando los precios de OHLC de forma horizontal
    """
    df_i = df.iloc[::-1].copy()
    df_i.reset_index(inplace = True)
    df_i.drop(columns=['index'],inplace=True)
    
    df['close']  = df_i['open']
    df['open']   = df_i['close']
    df['high']   = df_i['high']
    df['low']    = df_i['low']
    df['volume'] = df_i['volume']

    return df