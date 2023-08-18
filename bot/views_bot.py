from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
import functions as fn
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError

from bot.models import *

@login_required
def bots(request):
    bots = Bot.objects.filter(usuario=request.user).order_by('-activo','estrategia__nombre') 
    formattedBots = []
    for b in bots:
        interval = fn.get_intervals(b.interval_id,'binance')
        formattedBots.append({'bot_id':b.id, 
                             'estrategia':b.estrategia.nombre,
                             'strPrm': interval+" "+b.str_parametros(),
                             'quote_qty': round(b.quote_qty,2),
                             'interval': b.usuario,
                             'usuario': b.usuario,
                             'activo': b.activo,
                             })
    if request.method == 'GET':
        return render(request, 'bots.html',{
            'bots': formattedBots,
        })

@login_required
def bot(request, bot_id):
    bot = get_object_or_404(Bot, pk=bot_id,usuario=request.user)
    
    return render(request, 'bot.html',{
        'title': str(bot),
        'nav_title': str(bot),
        'bot_id': bot.id,
        'estrategia': bot.estrategia.nombre,
        'estrategia_id': bot.estrategia.id,
        'activo': bot.activo,
        'creado': bot.creado,
        'quote_qty': round(bot.quote_qty,2),
        'interval': fn.get_intervals(bot.interval_id,'binance'),
        'can_delete': bot.can_delete(),
        'strParametros': bot.str_parametros(),
        'parametros': bot.parse_parametros(),
    })

@login_required
def bot_create(request):
    jsonRsp = {}
    if request.method == 'GET':
        intervals = fn.get_intervals().to_dict('records')
        return render(request, 'bot_edit.html',{
            'title': 'Crear Bot',
            'nav_title': 'Crear Bot',
            'intervals': intervals,
            'estrategias': Estrategia.objects.filter(activo__gt=0),
            'bot_id': 0,
            'estrategia_id': 0,
        })
    else:
        bot = Bot()
        
        bot.estrategia_id=request.POST['estrategia_id']
        bot.parametros=request.POST['parametros']
        bot.interval_id=request.POST['interval_id']
        bot.quote_qty=request.POST['quote_qty']
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
    jsonRsp['ok'] = len(parametros)
    jsonRsp['parametros'] = parametros
    return JsonResponse(jsonRsp)



@login_required
def bot_edit(request,bot_id):
    jsonRsp = {}
    bot = get_object_or_404(Bot, pk=bot_id,usuario=request.user)
    if request.method == 'GET':
        intervals = fn.get_intervals().to_dict('records')
        
        return render(request, 'bot_edit.html',{
            'title': 'Editar Bot '+str(bot),
            'nav_title': 'Editar Bot',
            'bot_id': bot.id,
            'intervals': intervals,
            'interval_id': bot.interval_id,
            'quote_qty': round(bot.quote_qty,2),
            'estrategia_id': bot.estrategia.id,
            'estrategias': Estrategia.objects.filter(Q(activo__gt=0) | Q(pk=bot.estrategia.id)),
            'activo': bot.activo,
            'parametros': bot.parse_parametros(),
        })
    else:

        bot.estrategia_id=request.POST['estrategia_id']
        bot.parametros=request.POST['parametros']
        bot.interval_id=request.POST['interval_id']
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
        jsonRsp['error'] = 'No es psible eliminar la bot'
    return JsonResponse(jsonRsp)
    
    
