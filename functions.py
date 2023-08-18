import my_logging as mylog
import pandas as pd

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
                mylog.criticalError('functions.py.get_intervals - El idinterval especificado es invalido')
        elif i!='ALL' and c!='ALL':
            if i in intervals.index:
                if c in intervals.loc[i]:
                    return intervals.loc[i][c]
                else:
                    mylog.criticalError('functions.py.get_intervals - El dato especificado es invalido')
            else:
                mylog.criticalError('functions.py.get_intervals - El idinterval especificado es invalido')