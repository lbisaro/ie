from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Case, When, IntegerField
from django.contrib.auth.decorators import login_required
import json

from bot.models import *
from bot.model_kline import *



@login_required
def backtesting(request):
    gen_bot = GenericBotClass()
    classList = gen_bot.get_clases()
    clases = []
    for c in classList:
        obj = gen_bot.get_instance(c)
        cls = {'class':c,'descripcion':obj.descripcion, }
        clases.append(cls)
    if request.method == 'GET':
        return render(request, 'backtesting.html',{
            'clases': clases,
        })

@login_required
def config(request,bot_class_name):
    gen_bot = GenericBotClass()
    obj = gen_bot.get_instance(bot_class_name)
    intervals = fn.get_intervals().to_dict('records')
    symbols = Symbol.objects.filter(activo=1).order_by('symbol')
        
    if request.method == 'GET':
        return render(request, 'backtesting_run.html',{
            'bot_class_name': bot_class_name,
            'intervals': intervals,
            'symbols': symbols,
            'parametros': obj.parametros,
        })


@login_required
def run(request):
    if request.method == 'POST':
        json_rsp = {}
        bot_class_name = request.POST['bot_class_name']
        gen_bot = GenericBotClass()
        run_bot = gen_bot.get_instance(bot_class_name)
        
        run_bot.quote_qty = float(request.POST['quote_qty'])
        run_bot.interval_id = request.POST['interval_id']

        prmPost = eval(request.POST['parametros'])
        for dict in prmPost:
            for k,v in dict.items():
                run_bot.__setattr__(k, v)

        from_date = request.POST['from_date']
        to_date = request.POST['to_date']

        atributos = run_bot.__dict__
        json_rsp['parametros'] = {}
        for attr in atributos:
            val = atributos[attr]
            json_rsp['parametros'][attr] = val

        #try:
        run_bot.valid()

        bt = run_bot.backtesting(from_date,to_date)
        json_rsp['bt'] = bt

        if bt['error']:
            json_rsp['error'] = bt['error']
            json_rsp['ok'] = False
        else:
            json_rsp['ok'] = True
        #except Exception as e:
        #    json_rsp['ok'] = False
        #    json_rsp['error'] = str(e)

        return JsonResponse(json_rsp)
    


