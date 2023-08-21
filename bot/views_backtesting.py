from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Case, When, IntegerField
from django.contrib.auth.decorators import login_required


from bot.models import *
from bot.model_kline import *


@login_required
def backtesting(request):
    estrategias = Estrategia.objects.annotate(qtyBots=Count('bot'),
                qtyBotsActivos=Count(Case(When(bot__activo__gt=0, then=1),output_field=IntegerField()))
                )

    if request.method == 'GET':
        return render(request, 'backtesting.html',{
            'estrategias': estrategias,
        })

@login_required
def config(request,estrategia_id):
    estrategia = get_object_or_404(Estrategia, pk=estrategia_id)
    intervals = fn.get_intervals().to_dict('records')
    symbols = Symbol.objects.filter(activo=1).order_by('symbol')
        
    if request.method == 'GET':
        return render(request, 'backtesting_run.html',{
            'estrategia': estrategia,
            'intervals': intervals,
            'symbols': symbols,
            'parametros': estrategia.parse_parametros(),
        })


@login_required
def run(request):
    if request.method == 'POST':
        jsonRsp = {}
        estrategia = get_object_or_404(Estrategia, pk=request.POST['estrategia_id'])
        estrategia.parametros=request.POST['parametros']
        parametros = estrategia.parse_parametros()

        runBot = eval(estrategia.clase)()
        runBot.quote_qty = float(request.POST['quote_qty'])
        runBot.interval_id = request.POST['interval_id']
        runBot.set(parametros)

        jsonRsp['ok'] = True

        atributos = runBot.__dict__
        jsonRsp['parametros'] = {}
        for attr in atributos:
            val = atributos[attr]
            jsonRsp['parametros'][attr] = val

        #try:
        runBot.valid()

        bt = runBot.backtesting()
        jsonRsp['bt'] = {}

        jsonRsp['ok'] = True
        # except Exception as e:
        #     jsonRsp['ok'] = False
        #     jsonRsp['error'] = str(e)

        return JsonResponse(jsonRsp)
    


