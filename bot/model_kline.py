from django.conf import settings
from django.db import models
from django.db.models import Max
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import F, Min, Max, Avg, Sum
from django.db.models.functions import TruncDay, TruncHour, TruncMinute
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
    
    def __str__(self):
        return f'{self.datetime} {self.close} {self.volume}'
    
    class Meta:
        verbose_name_plural='Velas'
       # Definir que la combinación de 'symbol' y 'datetime' es única
        unique_together = ('symbol', 'datetime')

    """
    # kwargs -> opcionales
        symbol(str) -> obligatorio
        interval_id(str) -> obligatorio
        limit(int) -> Cantidad de velas, desde now() hacia atras
        from_date ('%Y-%m-%d')
        to_date ('%Y-%m-%d')

        Si no llegan parametros toma todas las velas registradas
    """
    def get_df(strSymbol,interval_id,**kwargs):

        #Procesando parametros
        #strSymbol = kwargs.get('symbol', None )
        #interval_id = kwargs.get('interval_id', None )
        limit = kwargs.get('limit', None )
        from_date = kwargs.get('from_date', None )
        to_date = kwargs.get('to_date', None )

        symbol = Symbol.objects.get(symbol = strSymbol)
        pandas_interval = fn.get_intervals(interval_id,'pandas_resample')
        i_unit = interval_id[1:2]
        i_qty = int(interval_id[2:])
        
        if limit is not None:
            if i_unit == 'm': #Minutos
                delta_time = timedelta(minutes = i_qty*limit)
                from_datetime = (datetime.now() - delta_time ).strftime('%Y-%m-%d %H:%M')+':00'
            elif i_unit == 'h': #Horas
                delta_time = timedelta(hours = i_qty*limit)
                from_datetime = (datetime.now() - delta_time ).strftime('%Y-%m-%d %H')+':00:00'
            elif i_unit == 'd': #Dias
                delta_time = timedelta(days = i_qty*limit)
                from_datetime = (datetime.now() - delta_time ).strftime('%Y-%m-%d')+' 00:00:00'
            
            to_datetime = (datetime.now() + timedelta(days = 1) ).strftime('%Y-%m-%d')+' 23:59:59'

        else:
            from_datetime = from_date+' 00:00:00' if from_date is not None else '2010-01-01 00:00:00'
            to_datetime = to_date+' 23:59:59' if to_date is not None else (datetime.now() - timedelta(days = 1) ).strftime('%Y-%m-%d')+' 23:59:59'
            
        #Formateando la fecha por compatibilidad de TimeZone
        #timezone.activate('UTC')
        #timezone = pytz.timezone('UTC')
        #from_datetime = timezone.localize(datetime.strptime(from_datetime,'%Y-%m-%d %H:%M:%S'))
        #to_datetime = timezone.localize(datetime.strptime(to_datetime,'%Y-%m-%d %H:%M:%S'))
        
        
        if i_unit == 'm': #Minutos
            klines = Kline.objects.filter(symbol_id=symbol.id, datetime__gte=from_datetime, datetime__lte=to_datetime).order_by('datetime')
        
        elif i_unit == 'h': #Horas
            query =  "SELECT id, symbol_id, "
            query += " min(datetime) AS datetime, "
            query += " CAST(SUBSTRING_INDEX(GROUP_CONCAT(open ORDER BY datetime ASC SEPARATOR '|'),'|',1) AS DECIMAL(15,8)) AS open, "
            query += " MAX(high) AS high, "
            query += " MIN(low) AS low, "
            query += " SUM(volume) AS volume, "
            query += " CAST(SUBSTRING_INDEX(GROUP_CONCAT(close ORDER BY datetime DESC SEPARATOR '|'),'|',1) AS DECIMAL(15,8)) AS close "
            query += " FROM bot_kline "
            query += " WHERE symbol_id = "+str(symbol.id)+" AND datetime >= '"+str(from_datetime)+"' AND datetime <= '"+str(to_datetime)+"' "
            query += " GROUP BY symbol_id, date(datetime), hour(datetime) "
            query += " order by datetime" 
            klines = Kline.objects.raw(query)
            
        elif i_unit == 'd': #Dias
            query =  "SELECT id, symbol_id, "
            query += " min(datetime) AS datetime, "
            query += " CAST(SUBSTRING_INDEX(GROUP_CONCAT(open ORDER BY datetime ASC SEPARATOR '|'),'|',1) AS DECIMAL(15,8)) AS open, "
            query += " MAX(high) AS high, "
            query += " MIN(low) AS low, "
            query += " SUM(volume) AS volume, "
            query += " CAST(SUBSTRING_INDEX(GROUP_CONCAT(close ORDER BY datetime DESC SEPARATOR '|'),'|',1) AS DECIMAL(15,8)) AS close "
            query += " FROM bot_kline "
            query += " WHERE symbol_id = "+str(symbol.id)+" AND datetime >= '"+str(from_datetime)+"' AND datetime <= '"+str(to_datetime)+"' "
            query += " GROUP BY symbol_id, date(datetime) "
            query += " order by datetime" 
            klines = Kline.objects.raw(query)
                    
        if not klines:
            return None
        else:
            data = [{'symbol': symbol.symbol,
                    'datetime': kline.datetime, 
                    'open': float(kline.open),
                    'close': float(kline.close),
                    'high': float(kline.high),
                    'low': float(kline.low),
                    'volume': float(kline.volume)
                    } for kline in klines]
            df = pd.DataFrame(data)
            
            agg_funcs = {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }   
            
            if i_qty != 1:
                df = df.resample(pandas_interval, on="datetime").agg(agg_funcs).reset_index()
            if limit is not None:
                df = df[0:limit]

            return df 
        