from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Case, When, IntegerField
from django.contrib.auth.decorators import login_required
import json

from bot.models import *
from bot.model_kline import *



@login_required
def backtesting(request):
    botClass = BotClass()
    classList = botClass.get_clases()
    clases = []
    for c in classList:
        obj = botClass.get_instance(c)
        cls = {'class':c,'descripcion':obj.descripcion, }
        clases.append(cls)
    if request.method == 'GET':
        return render(request, 'backtesting.html',{
            'clases': clases,
        })

@login_required
def config(request,botClassId):
    botClass = BotClass()
    obj = botClass.get_instance(botClassId)
    intervals = fn.get_intervals().to_dict('records')
    symbols = Symbol.objects.filter(activo=1).order_by('symbol')
        
    if request.method == 'GET':
        return render(request, 'backtesting_run.html',{
            'botClass': botClassId,
            'intervals': intervals,
            'symbols': symbols,
            'parametros': obj.parametros,
        })


@login_required
def run(request):
    if request.method == 'POST':
        jsonRsp = {}
        botClassId = request.POST['botClassId']
        botClass = BotClass()
        runBot = botClass.get_instance(botClassId)
        
        runBot.quote_qty = float(request.POST['quote_qty'])
        runBot.interval_id = request.POST['interval_id']

        prmPost = eval(request.POST['parametros'])
        for dict in prmPost:
            for k,v in dict.items():
                runBot.__setattr__(k, v)

        from_date = request.POST['from_date']
        to_date = request.POST['to_date']

        atributos = runBot.__dict__
        jsonRsp['parametros'] = {}
        for attr in atributos:
            val = atributos[attr]
            jsonRsp['parametros'][attr] = val

        #try:
        runBot.valid()

        bt = runBot.backtesting(from_date,to_date)
        jsonRsp['bt'] = bt

        if bt['error']:
            jsonRsp['error'] = bt['error']
            jsonRsp['ok'] = False
        else:
            jsonRsp['ok'] = True
        #except Exception as e:
        #    jsonRsp['ok'] = False
        #    jsonRsp['error'] = str(e)

        return JsonResponse(jsonRsp)
    


