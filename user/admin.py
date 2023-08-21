from django.contrib import admin

from bot.models import *
from bot.model_kline import *
admin.site.register(Estrategia)
admin.site.register(Bot)
admin.site.register(Order)
admin.site.register(Symbol)
admin.site.register(Kline)
