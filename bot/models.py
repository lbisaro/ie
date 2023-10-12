from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import functions as fn
import os, fnmatch
import importlib
from scripts.BotBase import BotBase


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
        buy = 0
        sell = 0
        start_order_id = 0

        for order in orders:
            if order.side == BotBase.SIDE_BUY:
                buy += 1
            if order.side == BotBase.SIDE_SELL:
                sell += 1
            if order.completed == 0:
                completed = False
            if start_order_id == 0 or order.id < start_order_id:
                start_order_id = order.id
        
        if buy > 0 and sell > 0 and completed:
            for order in orders:
                order.pos_order_id = start_order_id
                order.save()
            return True
        return False

class Order(models.Model):
    bot = models.ForeignKey(Bot, on_delete = models.CASCADE)
    datetime = models.DateField(default=timezone.now)
    base_asset = models.CharField(max_length = 14, null=False, blank=False, db_index=True)
    quote_asset = models.CharField(max_length = 14, null=False, blank=False, db_index=True)
    completed = models.IntegerField(default=0, null=False, blank=False, db_index=True)
    qty = models.FloatField(null=False, blank=False)
    price = models.FloatField(null=False, blank=False)
    orderid = models.CharField(max_length = 20, null=False, unique = True, blank=False, db_index=True)
    pos_order_id = models.IntegerField(default=0, null=False, blank=False, db_index=True)
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
