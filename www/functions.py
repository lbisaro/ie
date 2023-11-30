import pandas as pd
from math import floor

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