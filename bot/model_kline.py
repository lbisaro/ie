from django.conf import settings
from django.db import models
from django.db.models import Max
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
import pandas as pd
import pytz
import functions as fn


class Symbol(models.Model):
    symbol = models.CharField(max_length = 16, unique = True, null=False, blank=False,verbose_name='Nombre del par')
    base_asset = models.CharField(max_length = 8, null=False, blank=False)
    quote_asset = models.CharField(max_length = 8, null=False, blank=False)
    qty_decs_qty = models.IntegerField(null=False, blank=False)
    qty_decs_price = models.IntegerField(null=False, blank=False)
    qty_decs_quote = models.IntegerField(null=False, blank=False)
    activo = models.IntegerField(default=0)  
    
    class Meta:
        verbose_name = "Par"
        verbose_name_plural='Pares'
        
    
    def activate(self):
        self.activo = 1
        self.save()

class Kline(models.Model):
    symbol = models.ForeignKey(Symbol, on_delete = models.CASCADE)
    datetime = models.DateTimeField(null=False, blank=False, db_index=True)
    open = models.DecimalField(max_digits=15,decimal_places=8,null=False, blank=False)
    close = models.DecimalField(max_digits=15,decimal_places=8,null=False, blank=False)
    high = models.DecimalField(max_digits=15,decimal_places=8,null=False, blank=False)
    low = models.DecimalField(max_digits=15,decimal_places=8,null=False, blank=False)
    volume = models.DecimalField(max_digits=12,decimal_places=2,null=False, blank=False)

    class Meta:
        verbose_name_plural='Velas'
       # Definir que la combinación de 'symbol' y 'datetime' es única
        unique_together = ('symbol', 'datetime')

    def get_df(strSymbol,interval_id,limit):
        symbol = Symbol.objects.get(symbol = strSymbol)
        pandas_interval = fn.get_intervals(interval_id,'pandas_resample')
        i_unit = interval_id[1:2]
        i_qty = int(interval_id[2:])
        if i_unit == 'm': #Minutos
            delta_time = timedelta(minutes = i_qty*limit)
            from_datetime = (datetime.now() - delta_time ).strftime('%Y-%m-%d %H:%M')+':00'
        elif i_unit == 'h': #Horas
            delta_time = timedelta(hours = i_qty*limit)
            from_datetime = (datetime.now() - delta_time ).strftime('%Y-%m-%d %H')+':00:00'
        elif i_unit == 'd': #Dias
            delta_time = timedelta(days = i_qty*limit)
            from_datetime = (datetime.now() - delta_time ).strftime('%Y-%m-%d')+' 00:00:00'
        
        timezone = pytz.timezone('UTC')
        from_datetime = timezone.localize(datetime.strptime(from_datetime,'%Y-%m-%d %H:%M:%S'))
        
        klines = Kline.objects.filter(symbol_id=symbol.id, datetime__gte=from_datetime).order_by('datetime')
        if not klines:
            return None
        else:
            data = [{'symbol': symbol.symbol,
                    'datetime': kline.datetime, 
                    'open': kline.open,
                    'close': kline.close,
                    'high': kline.high,
                    'low': kline.low,
                    'volume': kline.volume
                    } for kline in klines]
            df = pd.DataFrame(data)
            
            agg_funcs = {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }   
            
            if interval_id != '0m01':
                df = df.resample(pandas_interval, on="datetime").agg(agg_funcs).reset_index()
                df = df[0:limit]
            return df 
        