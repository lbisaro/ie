from django.conf import settings
from django.db import models, connection
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import functions as fn
import os, fnmatch
import importlib
from scripts.BotBase import BotBase
from bot.model_kline import Symbol
import pandas as pd
import datetime as dt


class BotClass:
    
    def get_clases(self):
        clases = []
        folder = os.path.join(settings.BASE_DIR,'scripts/bots')
        files = [file for file in os.listdir(folder) if fnmatch.fnmatch(file, 'Bot*.py')]
        for file in files:
            file = file.replace('.py','')
            clases.append(file)
        return clases
    
    def get_instance(self,clase):
        modulo = importlib.import_module(f'scripts.bots.{clase}')
        obj = eval(f'modulo.{clase}()')
        return obj

class Estrategia(models.Model):
    nombre = models.CharField(max_length = 100, null=False, unique = True, blank=False)
    clase = models.SlugField(max_length = 50, null=False, blank=False)
    parametros = models.TextField(null=False, blank=False)
    descripcion = models.TextField(null=False, blank=False)
    interval_id = models.CharField(max_length = 8, null=False, blank=False)
    creado = models.DateField(default=timezone.now)
    activo = models.IntegerField(default=0)  
    max_drawdown = models.FloatField(null=False, blank=False)

    def __str__(self):
        str = self.nombre
        return str
    
    def get_descripcion(self):
        botClass = BotClass()
        runBot = botClass.get_instance(self.clase)
        runBot.set(self.parametros)
        intervalo = fn.get_intervals(self.interval_id,'pandas_resample')
        add_nombre = f'[{intervalo}] '+runBot.get_add_nombre()  
        return add_nombre
    
    def can_delete(self):
        bots = Bot.objects.filter(estrategia_id=self.id)
        qtyBots = len(bots)
        return True if (qtyBots == 0 and self.activo == 0) else False
         
    
    def clean(self):
        botClass = BotClass().get_instance(self.clase)
        botClass.set(self.parse_parametros())
        
        try:
            botClass.valid()
        except Exception as e:
            raise ValidationError(e)

    def parse_parametros(self):
        botClass = BotClass().get_instance(self.clase)
        parametros = botClass.parametros
        pe = eval(self.parametros)
        for prm in pe:
            for v in prm:
                parametros[v]['v'] = prm[v]
                parametros[v]['str'] = prm[v]

                if parametros[v]['t'] == 'perc':
                    val = float(parametros[v]['v'])
                    parametros[v]['str'] = f'{val:.2f} %'

                if parametros[v]['t'] == 't_int':
                    if parametros[v]['v'] == 's':
                        parametros[v]['str'] = 'Simple'
                    elif parametros[v]['v'] == 'c':
                        parametros[v]['str'] = 'Compuesto'
                
                    
        return parametros

    def str_parametros(self):
        prm = self.parse_parametros()
        str = ''
        for p in prm:
            if str != '':
                str += ', '
            str += p['v']
        return f"{str}"

    def get_estrategias_to_run(intervals):
        query = "SELECT * "
        query += "FROM bot_estrategia "
        query += "WHERE activo = 1 AND interval_id in ("+intervals+") "
        query += "AND (SELECT count(id) FROM bot_bot WHERE activo = 1 AND bot_bot.estrategia_id = bot_estrategia.id)"
        query += "ORDER BY bot_estrategia.id"
        estrategias = Estrategia.objects.raw(query)
        return estrategias

    def get_instance(self):
        botClass = BotClass().get_instance(self.clase)
        botClass.set(self.parse_parametros())
        botClass.interval_id = self.interval_id

        return botClass


class Bot(models.Model):
    estrategia = models.ForeignKey(Estrategia, on_delete = models.CASCADE)
    usuario = models.ForeignKey(User, on_delete = models.CASCADE)
    creado = models.DateField(default=timezone.now)
    finalizado = models.DateField(null=True, blank=True)
    activo = models.IntegerField(default=0)
    quote_qty = models.FloatField(null=False, blank=False)
    max_drawdown = models.FloatField(null=False, blank=False)
    stop_loss = models.FloatField(null=False, blank=False)

    def __str__(self):
        str = f"Bot {self.estrategia.nombre}"

        strInterval = ''
        if self.estrategia.interval_id:
            strInterval = fn.get_intervals(self.estrategia.interval_id,'binance')
        str += f" {strInterval}"

        str += f' [{self.usuario.username}]'
        
        return str
    
    def can_delete(self):
        orders = Order.objects.filter(bot_id=self.id)
        qtyOrders = len(orders)
        return True if (qtyOrders == 0 and self.activo == 0) else False
         
    def parse_parametros(self):
        return self.estrategia.parse_parametros()
    
    def get_instance(self):
        botClass = self.estrategia.get_instance()
        botClass.set(self.parse_parametros())
        botClass.quote_qty = self.quote_qty
        botClass.valid()
        return botClass

    def get_bots_activos():
        query = "SELECT * FROM bot_bot "\
                "WHERE bot_bot.activo = 1 "\
                "ORDER BY usuario_id"
        bots = Bot.objects.raw(query)
        return bots

    def get_pos_orders(self):
        query = "SELECT * FROM bot_order "\
                "WHERE bot_id = "+str(self.id)+" AND pos_order_id = 0 "\
                "ORDER BY datetime"
        pos_orders = Order.objects.raw(query)
        return pos_orders
    
    def close_pos(self):
        orders = self.get_pos_orders()
        completed = True
        qty_base = 0
        buy = 0
        sell = 0
        start_order_id = 0

        for order in orders:
            if order.side == BotBase.SIDE_BUY:
                qty_base += 1
                qty_base += order.qty
            if order.side == BotBase.SIDE_SELL:
                sell += 1
                qty_base -= order.qty
            if order.completed == 0:
                completed = False
            if start_order_id == 0 or order.id < start_order_id:
                start_order_id = order.id

        if buy > 0 and sell > 0 and completed and qty_base == 0:
            for order in orders:
                order.pos_order_id = start_order_id
                order.save()
            return True
        
        self.bloquear()
        return False
    
    def bloquear(self):
        self.activo = 0
        self.save()
        self.add_log(BotLog.LOG_DESACTIVAR)
    
    def add_log(self,log_id):
        bot_log = BotLog()
        bot_log.bot = self
        bot_log.log_id = log_id
        bot_log.save()

    def get_orders(self):
        query = "SELECT * FROM bot_order "\
                "WHERE bot_id = "+str(self.id)+" "\
                "ORDER BY datetime"
        orders = Order.objects.raw(query)
        return orders
    
    def get_trades(self):
        orders = self.get_orders()
        

        last_posorder_id = -1
        trades = {}
        trade = {}
        key = 0
        
        for o in orders:
            if o.completed > 0 and o.pos_order_id > 0:
                
                #Reinicio de la posicion
                if o.pos_order_id != last_posorder_id:
                    last_posorder_id = o.pos_order_id
                    key = o.pos_order_id
                    trades[key] = {}
                    trade = {}
                    trade['start'] = o.datetime
                    trade['buy_price'] = 0.0
                    trade['qty'] = 0.0
                    trade['end'] = None
                    trade['flag'] = ''
                    trade['sell_price'] = 0.0
                    trade['str_flag'] = ''
                    trade['days'] = 0.0
                    trade['comision'] = 0.0
                    trade['orders'] = 0
                    trade['buy_ops'] = 0
                    trade['buy_acum_quote'] = 0.0
                    trade['buy_acum_base'] = 0.0
                    trade['buy_avg_price'] = 0.0
                    trade['sell_ops'] = 0
                    trade['sell_acum_quote'] = 0.0
                    trade['sell_acum_base'] = 0.0
                    trade['sell_avg_price'] = 0.0
                    trade['result_qty'] = 0.0
                    trade['result_quote'] = 0.0
                    trade['result_perc'] = 0.0
                        
                    
                if o.side == BotBase.SIDE_BUY:
                    trade['buy_ops'] += 1
                    trade['buy_acum_quote'] += o.price * o.qty
                    trade['buy_acum_base'] += o.qty
                    trade['result_qty'] += o.qty

                else:
                    trade['sell_ops'] += 1
                    trade['sell_acum_quote'] += o.price * o.qty
                    trade['sell_acum_base'] += o.qty
                    trade['result_qty'] -= o.qty
                    

                #Calculos
                trade['comision'] = round(trade['comision'] + o.price * o.qty * (BotBase.exch_comision_perc/100) ,4)
                if trade['buy_acum_base'] != 0:
                    trade['buy_avg_price'] = trade['buy_acum_quote'] / trade['buy_acum_base']
                if trade['sell_acum_base'] != 0:
                    trade['sell_avg_price'] = trade['sell_acum_quote'] / trade['sell_acum_base']
                if trade['buy_avg_price'] != 0:
                    trade['result_perc'] = round(((trade['sell_avg_price']/trade['buy_avg_price'])-1)*100 - BotBase.exch_comision_perc , 2)
                
                trade['result_quote'] = trade['sell_acum_quote']-trade['buy_acum_quote']-trade['comision']
                

                trade['end'] = o.datetime
                if o.flag == BotBase.FLAG_STOPLOSS:
                   trade['flag'] += 'SL '
                elif o.flag == BotBase.FLAG_TAKEPROFIT:
                   trade['flag'] += 'TP '
                
                trades[key] = trade

        #transforma el diccinoario de diccionarios en una lista de diccionarios
        list_trades = []
        for t in trades:
            dif = trades[t]['end'] - trades[t]['start']
            days = round(dif.total_seconds() / 60 / 60 / 24 , 2)
            trades[t]['duracion'] = days
            list_trades.append(trades[t])
        return list_trades 
                

    
    def can_activar(self):
        if self.estrategia.activo > 0:
            return True
        return False
    
    def get_resultados(self):
        jsonRsp = {}
        orders = self.get_orders()
        trades = self.get_trades()

        """
        botClass = self.get_instance()
        botClass.reset_res()
        botClass.reset_pos()
        symbol = botClass.symbol
        intervalo = fn.get_intervals(self.estrategia.interval_id,'binance') 
        kline_ini = self.creado
        if self.finalizado:
            kline_end = self.finalizado
        else:
            kline_end = timezone.now()

      
        klines = Kline.get_df(strSymbol=symbol, 
                              interval_id=self.estrategia.interval_id,
                              from_date = kline_ini.strftime('%Y-%m-%d'),
                              to_date = kline_end.strftime('%Y-%m-%d'),
                              )
        botClass.klines = klines
        orders = self.get_orders()
        order_columns = ['datetime','symbol','side','qty','price','flag','comision']
        last_posorder_id = 0
        for o in orders:
            comision = round(o.price * o.qty * (BotBase.exch_comision_perc/100) ,4)
            order_datetime = o.datetime.replace(second=0, microsecond=0)
            if o.completed > 0 and o.pos_order_id > 0:
                order = [
                    order_datetime,
                    o.base_asset+o.quote_asset,
                    o.side,
                    o.qty,
                    o.price,
                    o.flag,
                    comision,
                ] 
                if o.pos_order_id != last_posorder_id:
                    last_posorder_id = o.pos_order_id
                    botClass.open_pos(o.datetime.strftime("%Y-%m-%d %H:%M"),o.price,o.qty)
                else:
                    botClass.close_pos(o.datetime.strftime("%Y-%m-%d %H:%M"),o.price,o.flag)

                botClass.res['orders'].append(order)
            

        df_orders = pd.DataFrame(botClass.res['orders'], columns=order_columns)
        df_orders.set_index('datetime', inplace=True)

        klines['side'] = None
        klines['qty'] = None
        klines['price'] = None
        klines['flag'] = None
        klines['comision'] = None

        botClass.wallet_base = 0.0
        botClass.wallet_quote = self.quote_qty * (botClass.quote_perc/100)
        hold_qty = 0
        for i in klines.index:
            k = klines.loc[i]
            timestamp = pd.Timestamp(k['datetime']).timestamp()
            unix_dt = int( (timestamp*1000) +  10800000 ) #Convierte a milisegundos y agrega 3 horas
            
            buy = None
            sell_s = None
            sell_sl = None
            sell_tp = None
            flag = None
            if k['datetime'] in df_orders.index:
                o = df_orders.loc[k['datetime']]
                if o.side == BotBase.SIDE_BUY:
                    botClass.wallet_quote = botClass.wallet_quote - (o.qty * o.price)
                    botClass.wallet_base = botClass.wallet_base + o.qty
                    buy = float(o.price)
                if o.side == BotBase.SIDE_SELL:
                    botClass.wallet_quote = botClass.wallet_quote + (o.qty * o.price)
                    botClass.wallet_base = botClass.wallet_base - o.qty
                    if o.flag == BotBase.FLAG_SIGNAL:
                        sell_s = float(o.price)
                    if o.flag == BotBase.FLAG_STOPLOSS:
                        sell_sl = float(o.price)
                    if o.flag == BotBase.FLAG_TAKEPROFIT:
                        sell_tp = float(o.price)
                flag = int(o.flag)

            if hold_qty == 0:
                hold_qty = botClass.wallet_quote / k['close']
            usdH = float(hold_qty*k['close'])

            usdW = botClass.wallet_quote + (botClass.wallet_base * k['close'])

            data = {'dt': unix_dt,
                    'o': k['open'],
                    'h': k['high'],
                    'l': k['low'],
                    'c': k['close'],
                    'v': k['volume'],
                    'sigB': None,
                    'sigS': None,
                    'buy': buy,
                    'sell_s': sell_s,
                    'sell_sl': sell_sl,
                    'sell_tp': sell_tp,
                    'flag': flag,
                    'usdH': usdH,
                    'usdW': usdW,
                    'dd': 0.0,
                    'SL': None,
                    'TP': None,
                } 
            botClass.res['data'].append(data)
        
        
        jsonRsp['parametros'] = {
            'interes': botClass.interes,
            'interval_id': self.estrategia.interval_id,
            'quote_perc': botClass.quote_perc,
            'quote_qty': botClass.quote_qty,
            'stop_loss': botClass.stop_loss,
            'take_profit': botClass.take_profit,
            'symbol': symbol,

        }
        exch = Exchange(type='info',exchange='bnc',prms=None)
        symbol_info = exch.get_symbol_info(symbol)
        botClass.base_asset = symbol_info['base_asset']
        botClass.quote_asset = symbol_info['quote_asset']
        botClass.qd_price = symbol_info['qty_decs_price']
        botClass.qd_qty = symbol_info['qty_decs_qty']
        botClass.qd_quote = symbol_info['qty_decs_quote']

        botClass.res['symbol'] = symbol
        botClass.res['periods'] = int(klines['close'].count())
        botClass.res['from'] = kline_ini.strftime('%Y-%m-%d')
        botClass.res['to'] = kline_end.strftime('%Y-%m-%d')
        botClass.res['base_asset'] = botClass.wallet_base
        botClass.res['quote_asset'] = botClass.wallet_quote
        botClass.res['qd_price'] = botClass.qd_price
        botClass.res['qd_qty'] = botClass.qd_qty
        botClass.res['qd_quote'] = botClass.qd_quote
        botClass.res['interval_id'] = self.estrategia.interval_id

        botClass.res['brief'] = botClass.bt_get_brief()

        jsonRsp['bt'] = botClass.res
        jsonRsp['ok'] = True
        """
        return jsonRsp

class Order(models.Model):
    bot = models.ForeignKey(Bot, on_delete = models.CASCADE)
    datetime = models.DateTimeField(default=timezone.now)
    completed = models.IntegerField(default=0, null=False, blank=False, db_index=True)
    qty = models.FloatField(null=False, blank=False)
    price = models.FloatField(null=False, blank=False)
    orderid = models.CharField(max_length = 20, null=False, unique = True, blank=False, db_index=True)
    pos_order_id = models.IntegerField(default=0, null=False, blank=False, db_index=True)
    symbol = models.ForeignKey(Symbol, on_delete = models.CASCADE)
    #Definido en BotBase: SIDE_BUY, SIDE_SELL
    side = models.IntegerField(default=0, null=False, blank=False, db_index=True)
    #Definido en BotBase: FLAG_SIGNAL, FLAG_STOPLOSS, FLAG_TAKEPROFIT
    flag = models.IntegerField(default=0, null=False, blank=False)
    
    def __str__(self):
        str = f"{self.base_asset}{self.quote_asset} "
        if self.side == 0:
            str += 'Compra'
        else:
            str += 'Venta'

        return str

    
    class Meta:
        verbose_name_plural='Bots'

class BotLog(models.Model):

    LOG_ACTIVAR = 1
    LOG_DESACTIVAR = 2

    bot = models.ForeignKey(Bot, on_delete = models.CASCADE)
    datetime = models.DateTimeField(default=timezone.now)
    log_id = models.IntegerField(default=0, null=False, blank=False, db_index=True)
        
        
    