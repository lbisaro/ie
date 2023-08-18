from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import functions as fn


class Symbol(models.Model):
    symbol = models.CharField(max_length = 16, null=False, blank=False)
    base_asset = models.CharField(max_length = 8, null=False, blank=False)
    quote_asset = models.CharField(max_length = 8, null=False, blank=False)
    qty_decs_qty = models.IntegerField(max_length=2, null=False, blank=False)
    qty_decs_price = models.IntegerField(max_length=2, null=False, blank=False)
    qty_decs_quote = models.IntegerField(max_length=2, null=False, blank=False)

class Klines(models.Model):
    symbol = models.ForeignKey(Symbol, on_delete = models.CASCADE)
    creado = models.DateField(null=False, blank=False, db_index=True)
    open = models.DecimalField(max_digits=15,decimal_places=8,null=False, blank=False)
    close = models.DecimalField(max_digits=15,decimal_places=8,null=False, blank=False)
    high = models.DecimalField(max_digits=15,decimal_places=8,null=False, blank=False)
    low = models.DecimalField(max_digits=15,decimal_places=8,null=False, blank=False)
    volume = models.DecimalField(max_digits=12,decimal_places=2,null=False, blank=False)