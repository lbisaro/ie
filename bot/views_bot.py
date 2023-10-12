from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
import functions as fn
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError

from bot.models import *
from bot.model_kline import *

@login_required
def bots(request):
    bots = Bot.objects.filter(usuario=request.user).order_by('-activo','estrategia__nombre') 
    formattedBots = []
    for b in bots:
        intervalo = fn.get_intervals(b.estrategia.interval_id,'name')
        formattedBots.append({'bot_id':b.id, 
                             'estrategia':b.estrategia.nombre,
                             'estrategia_activo':b.estrategia.activo,
                             'quote_qty': round(b.quote_qty,2),
                             'usuario': b.usuario,
                             'intervalo': intervalo,
                             'activo': b.activo,
                             })
    if request.method == 'GET':
        return render(request, 'bots.html',{
            'bots': formattedBots,
        })

@login_required
def bot(request, bot_id):
    bot = get_object_or_404(Bot, pk=bot_id,usuario=request.user)
    intervalo = fn.get_intervals(bot.estrategia.interval_id,'name')
    return render(request, 'bot.html',{
        'title': str(bot),
        'nav_title': str(bot),
        'bot_id': bot.id,
        'estrategia': bot.estrategia.nombre,
        'descripcion': bot.estrategia.descripcion,
        'estrategia_activo': bot.estrategia.activo,
        'intervalo': intervalo,
        'estrategia_id': bot.estrategia.id,
        'activo': bot.activo,
        'creado': bot.creado,
        'quote_qty': round(bot.quote_qty,2),
        'stop_loss': round(bot.stop_loss,2),
        'max_drawdown': round(bot.max_drawdown,2),
        'can_delete': bot.can_delete(),
        'parametros': bot.parse_parametros(),
    })

@login_required
def bot_create(request):
    jsonRsp = {}
    if request.method == 'GET':
        intervals = fn.get_intervals().to_dict('records')
        symbols = Symbol.objects.filter(activo=1).order_by('symbol')
        return render(request, 'bot_edit.html',{
            'title': 'Crear Bot',
            'nav_title': 'Crear Bot',
            'intervals': intervals,
            'symbols': symbols,
            'estrategias': Estrategia.objects.filter(activo__gt=0),
            'bot_id': 0,
            'estrategia_id': 0,
        })
    else:
        bot = Bot()
        
        bot.estrategia_id=request.POST['estrategia_id']
        bot.quote_qty=request.POST['quote_qty']
        bot.max_drawdown=request.POST['max_drawdown']
        bot.stop_loss=request.POST['stop_loss']
        bot.usuario=request.user
        
        try:
            bot.full_clean()

            bot.save()
            jsonRsp['ok'] = '/bot/bot/'+str(bot.id)

        except ValidationError as e:
            strError = ''
            for err in e:
                if err[0] != '__all__':
                    strError += '<br/><b>'+err[0]+'</b> '
                for desc in err[1]:
                    strError += desc+" "
            jsonRsp['error'] = strError

        return JsonResponse(jsonRsp)
        
@login_required
def get_parametros_estrategia(request,estrategia_id):
    jsonRsp = {}
    estrategia = Estrategia.objects.get(pk=estrategia_id)
    parametros = estrategia.parse_parametros(),

    descripcion = estrategia.descripcion
    intervalo = fn.get_intervals(estrategia.interval_id,'name')
    jsonRsp['ok'] = len(parametros)
    jsonRsp['max_drawdown'] = estrategia.max_drawdown
    jsonRsp['descripcion'] = descripcion
    jsonRsp['intervalo'] = intervalo
    jsonRsp['parametros'] = parametros
    return JsonResponse(jsonRsp)



@login_required
def bot_edit(request,bot_id):
    jsonRsp = {}
    bot = get_object_or_404(Bot, pk=bot_id,usuario=request.user)
    if request.method == 'GET':
        symbols = Symbol.objects.filter(activo=1).order_by('symbol')
        
        return render(request, 'bot_edit.html',{
            'title': 'Editar Bot '+str(bot),
            'nav_title': 'Editar Bot',
            'bot_id': bot.id,
            'symbols': symbols,
            'quote_qty': round(bot.quote_qty,2),
            'stop_loss': round(bot.stop_loss,2),
            'max_drawdown': round(bot.max_drawdown,2),
            'estrategia_id': bot.estrategia.id,
            'estrategias': Estrategia.objects.filter(Q(activo__gt=0) | Q(pk=bot.estrategia.id)),
            'activo': bot.activo,
        })
    else:

        bot.estrategia_id=request.POST['estrategia_id']
        bot.stop_loss=request.POST['stop_loss']
        bot.max_drawdown=request.POST['max_drawdown']
        bot.quote_qty=request.POST['quote_qty']

        try:
            bot.full_clean()

            bot.save()
            jsonRsp['ok'] = '/bot/bot/'+str(bot.id)

        except ValidationError as e:
            strError = ''
            for err in e:
                if err[0] != '__all__':
                    strError += '<br/><b>'+err[0]+'</b> '
                for desc in err[1]:
                    strError += desc+" "
            jsonRsp['error'] = strError

        return JsonResponse(jsonRsp)

@login_required
def bot_toogle_activo(request,bot_id):
    bot = get_object_or_404(Bot, pk=bot_id,usuario=request.user)
    if bot.activo > 0:
        bot.activo = 0
    else:
        bot.activo = 1
    bot.save()
    return redirect('/bot/bot/'+str(bot.id))

@login_required
def bot_delete(request,bot_id):
    jsonRsp = {}
    bot = get_object_or_404(Bot, pk=bot_id,usuario=request.user)
    if bot.can_delete():
        bot.delete()
        jsonRsp['ok'] = True
    else:
        jsonRsp['error'] = 'No es psible eliminar el Bot'
    return JsonResponse(jsonRsp)
    
    