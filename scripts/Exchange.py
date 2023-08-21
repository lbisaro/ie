from binance.client import Client
from local__config import *
import math
from datetime import datetime, timedelta
import pytz
import pandas as pd

from bot.model_kline import * 

class Exchange():

    start_klines_str = '2022-08-01 00:00:00 UTC-3'

    def __init__(self,type):
        if type == 'info':
            self.client = Client()
        elif type == 'apikey':
            self.client = Client(LOC_BNC_AK,LOC_BNC_SK,LOC_BNC_TESNET)
        
    def get_symbol_info(self,symbol):
        symbol = symbol.upper()

        db = Symbol.objects.filter(symbol = symbol)
        if not db:
            symbol_info = self.client.get_symbol_info(symbol)
            qty_decs_qty   = self.calcular_decimales(float(symbol_info['filters'][1]['minQty']))
            qty_decs_price = self.calcular_decimales(float(symbol_info['filters'][0]['minPrice']))
            symbol_info['qty_decs_price'] = qty_decs_price
            symbol_info['qty_decs_qty'] = qty_decs_qty
            symbol_info['quote_asset'] = symbol_info['quoteAsset']
            symbol_info['base_asset'] = symbol_info['baseAsset']
            if symbol_info['quote_asset'] == 'USDT' or symbol_info['quote_asset'] == 'BUSD' or symbol_info['quote_asset'] == 'USDC':
                symbol_info['qty_decs_quote'] = 2

        else:
            symbol_info = {}
            for i in db:
                symbol_info['qty_decs_price'] = i.qty_decs_price
                symbol_info['qty_decs_qty'] = i.qty_decs_qty
                symbol_info['qty_decs_quote'] = i.qty_decs_quote
                symbol_info['quote_asset'] = i.quote_asset
                symbol_info['base_asset'] = i.base_asset
        
        return symbol_info

        
    def calcular_decimales(self,step_size):
        potencia = int(math.log10(step_size))
        decimales = ( 0 if potencia>0 else -potencia )
        return decimales
    
    def precio_actual(self,symbol):
        result = self.client.get_avg_price(symbol=symbol)
        avg_price = float(result['price'])
        return avg_price

    def update_klines(self,symbol='ALL'):
        MINUTES_TO_GET = 1440 # 60 minutos * 24 horas = 1 dia
        res = {}
        if symbol == 'ALL':
            symbols = Symbol.objects.filter(activo__gt=0)
        else:
            symbols = Symbol.objects.filter(symbol=symbol)
        
        for s in symbols:
            valid_last_minute = (datetime.now() - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M')
            last_kline = Kline.objects.filter(symbol_id=s.id).order_by('-datetime').first()
            if last_kline:
                
                last_minute = last_kline.datetime.strftime('%Y-%m-%d %H:%M')

                next_datetime = ( last_kline.datetime + timedelta(minutes=1) ).strftime('%Y-%m-%d %H:%M:%S') 
            else:
                if s.symbol == 'BTCUSDT':
                    next_datetime = '2021-01-01 00:00:00'
                    last_minute = '2021-01-01 00:00'
                else:
                    next_datetime = '2022-08-01 00:00:00'
                    last_minute = '2022-08-01 00:00'
            
            end_datetime = ( datetime.strptime(next_datetime, '%Y-%m-%d %H:%M:%S') + timedelta(minutes=MINUTES_TO_GET) ).strftime('%Y-%m-%d %H:%M:%S')
            
            if last_minute < valid_last_minute:
                try:
                    klines = self.client.get_historical_klines(symbol=s.symbol, 
                                                                interval='1m', 
                                                                start_str=next_datetime+ ' UTC-3',
                                                                end_str=end_datetime+ ' UTC-3')

                    df = pd.DataFrame(klines)
                    df = df.iloc[:, :6]
                    df.columns = ["datetime", "open", "high", "low", "close", "volume"]
                    df['open'] = df['open'].astype('float')
                    df['high'] = df['high'].astype('float')
                    df['low'] = df['low'].astype('float')
                    df['close'] = df['close'].astype('float')
                    df['volume'] = df['volume'].astype('float')
                    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms') - pd.Timedelta('3 hr')
                    df['symbol_id'] = s.id
                    qty_records =  int(df['datetime'].count()) 

                    timezone = pytz.timezone('UTC')
                    
                    #Si no obtuvo el total de las velas esperadas es porque llego al final del lote
                    #Por lo tanto, se elimina el ultimo registro para no almacenar velas que estan en formacion
                    if qty_records < MINUTES_TO_GET: 
                        df = df[:-1]    
                    
                    qty_records =  int(df['datetime'].count())
                    if qty_records > 0:

                        df_records = df.to_dict('records')
                        data = [Kline(
                            datetime = timezone.localize(row['datetime']),
                            open  = row['open'],
                            high  = row['high'],
                            low  = row['low'],
                            close  = row['close'],
                            volume  = row['volume'],
                            symbol_id  = row['symbol_id'],
                        ) for row in df_records]
                        Kline.objects.bulk_create(data)
                        res[s.symbol] = {'qty':qty_records, 'datetime': df['datetime'].iloc[-1].strftime('%Y-%m-%d %H:%M')} 
                    else:
                        res[s.symbol] = {'qty':0, 'datetime': df['datetime'].iloc[-1].strftime('%Y-%m-%d %H:%M')} 
                        s.activate()
                except Exception as e:
                    print(str(e))
                    pass 
            else:
                res[s.symbol] = {'qty':0, 'datetime': 'updated'}
                s.activate()
                

        return res