from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse

import functions as fn

from bot.models import *

from binance.client import Client

def bots(request):
    bots = Bot.objects.filter(activo__gt=0).order_by('usuario_id','estrategia_id') 
    
    jsonRsp = {}
    jsonRsp['ok'] = True
    jsonRsp['qty_bots'] = len(bots)
    jsonRsp['bots'] = []
    
    for b in bots:
        intervals = fn.get_intervals(b.interval_id,'binance')
        bot = {
            'bot_id':  b.id,
            'usuario_id':  b.usuario_id,
            'estrategia_id':  b.estrategia_id,
            'username':  b.usuario.username,
            'clase':  b.estrategia.clase,
            'interval': intervals,
            'interval_id': b.interval_id,
            'quote_qty': b.quote_qty,
            'parametros': eval(b.parametros)
            }
        #parametros = b.parse_parametros()
        #for p in parametros:
        #    bot['parametros'][p['c']] = p['v']

        jsonRsp['bots'].append(bot)

    return JsonResponse(jsonRsp)

def bot_run(request,bot_id):
    jsonRsp = {}
    #bot = Bot.objects.get(pk=bot_id)
    bot = get_object_or_404(Bot, pk=bot_id)
    jsonRsp['ok'] = True
    jsonRsp['parametros'] = {}

    client = Client()
    runBot = BotLong(bot_id,client)

    atributos = runBot.__dict__
    for attr in atributos:
        val = atributos[attr]
        print(attr, type(attr), val, type(val) )
        jsonRsp['parametros'][attr] = str(val)
    

    return JsonResponse(jsonRsp)
