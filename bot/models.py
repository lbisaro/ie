from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import functions as fn
import os, fnmatch

from scripts.BotLong import BotLong


class Estrategia(models.Model):
    nombre = models.CharField(max_length = 100, null=False, unique = True, blank=False)
    clase = models.SlugField(max_length = 50, null=False, blank=False)
    parametros = models.TextField(null=False, blank=False)
    creado = models.DateField(default=timezone.now)
    activo = models.IntegerField(default=0)  

    def __str__(self):
        return self.nombre
    
    def strPrm(self):
        return self.str_parametros()
    
    def can_delete(self):
        bots = Bot.objects.filter(estrategia_id=self.id)
        qtyBots = len(bots)
        return True if (qtyBots == 0 and self.activo == 0) else False
         
    
    def clean(self):
        bot_class = eval(self.clase)()
        bot_class.set(eval(self.parametros))
        
        try:
            bot_class.valid()
        except Exception as e:
            raise ValidationError(e)

    def parse_parametros(self):
        parametros = eval(self.clase).parametros
        pe = eval(self.parametros)
        for prm in pe:
            for v in prm:
                parametros[v]['v'] = prm[v]
        return parametros     
    
    def str_parametros(self):
        prm = self.parse_parametros()
        str = ''
        for p in prm:
            if str != '':
                str += ', '
            str += p['v']
        return f"{str}"
    
    def get_clases():
        folder = os.path.join(settings.BASE_DIR,'scripts')
        files = [file for file in os.listdir(folder) if fnmatch.fnmatch(file, 'Bot*.py')]
        clases = []
        for file in files:
            file = file.replace('.py','')
            if file != 'BotBase':
                clases.append(file)
        return clases


class Bot(models.Model):
    estrategia = models.ForeignKey(Estrategia, on_delete = models.CASCADE)
    usuario = models.ForeignKey(User, on_delete = models.CASCADE)
    parametros = models.TextField(null=False, blank=False)
    creado = models.DateField(default=timezone.now)
    activo = models.IntegerField(default=0)
    interval_id = models.CharField(max_length = 50, null=False, blank=False)
    quote_qty = models.DecimalField(max_digits=18,decimal_places=8,null=False, blank=False)

    def __str__(self):
        str = f"{self.estrategia.nombre}"

        strInterval = ''
        if self.interval_id:
            strInterval = fn.get_intervals(self.interval_id,'binance')
        str += f" {strInterval}"
        
        strPrm = self.str_parametros()
        str += f" [{strPrm}]"
        return str
    
    def can_delete(self):
        orders = Order.objects.filter(bot_id=self.id)
        qtyOrders = len(orders)
        return True if (qtyOrders == 0 and self.activo == 0) else False
         
    def clean(self):
        bot_class = eval(self.estrategia.clase)()
        bot_class.set(eval(self.parametros))
        
        try:
            bot_class.valid()
        except Exception as e:
            raise ValidationError(e)
    
    def parse_parametros(self):
        parametros = self.estrategia.parse_parametros()
        pb = eval(self.parametros)
        for prm in pb:
            for v in prm:
                parametros[v]['v'] = prm[v]
        return parametros
    
    def str_parametros(self):
        pb = eval(self.parametros)

        str = ''
        for prm in pb:
            for v in prm:
                str += prm[v]+' '
        return str.strip()


class Order(models.Model):
    bot = models.ForeignKey(Bot, on_delete = models.CASCADE)
    
    datetime = models.DateField(default=timezone.now)
    base_asset = models.CharField(max_length = 14, null=False, blank=False, db_index=True)
    quote_asset = models.CharField(max_length = 14, null=False, blank=False, db_index=True)
    side = models.IntegerField(default=0, null=False, blank=False, db_index=True)
    completed = models.IntegerField(default=0, null=False, blank=False, db_index=True)
    qty = models.DecimalField(max_digits=15,decimal_places=8,null=False, blank=False)
    price = models.DecimalField(max_digits=15,decimal_places=8, null=False, blank=False)
    orderid = models.CharField(max_length = 20, null=False, unique = True, blank=False, db_index=True)
    pos_order_id = models.IntegerField(default=0, null=False, blank=False, db_index=True)
    
    def __str__(self):
        str = f"{self.base_asset}{self.quote_asset} "
        if self.side == 0:
            str += 'Compra'
        else:
            str += 'Venta'

        return str

    
    class Meta:
        verbose_name_plural='Bots'
