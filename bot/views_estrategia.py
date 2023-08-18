from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Case, When, IntegerField
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError

from bot.models import *
from scripts.BotLong import *

@login_required
def estrategias(request):
    estrategias = Estrategia.objects.annotate(qtyBots=Count('bot'),
                qtyBotsActivos=Count(Case(When(bot__activo__gt=0, then=1),output_field=IntegerField()))
                )

    if request.method == 'GET':
        return render(request, 'estrategias.html',{
            'estrategias': estrategias,
        })

@login_required
def estrategia(request, estrategia_id):
    estrategia = get_object_or_404(Estrategia, pk=estrategia_id)
    bots = Bot.objects.filter(estrategia_id=estrategia_id)
    qtyBots = len(bots)
    if qtyBots == 0:
        qtyBots = 'Ninguno'

    return render(request, 'estrategia.html',{
        'estrategia_id': estrategia.id,
        'nombre': estrategia.nombre,
        'clase': estrategia.clase,
        'activo': estrategia.activo,
        'creado': estrategia.creado,
        'qtyBots': qtyBots,
        'can_delete': estrategia.can_delete(),
        'parametros': estrategia.parse_parametros(),
    })

@login_required
def estrategia_create(request):
    jsonRsp = {}
    if request.method == 'GET':
        clases = Estrategia.get_clases()
        return render(request, 'estrategia_edit.html',{
            'title': 'Crear estrategia',
            'clases': clases,
            'qtyBots': 0,
            'estrategia_id': 0,
        })
    else:
        estrategia = Estrategia()
        estrategia.nombre=request.POST['nombre'] 
        estrategia.clase=request.POST['clase']
        estrategia.parametros=request.POST['parametros']
        
        try:
            estrategia.full_clean()

            estrategia.save()
            jsonRsp['ok'] = '/bot/estrategia/'+str(estrategia.id)

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
def load_parametros(request,clase):
    jsonRsp = {}
    
    parametros = eval(clase).parametros
    jsonRsp['ok'] = len(parametros)
    jsonRsp['parametros'] = parametros
    return JsonResponse(jsonRsp)


@login_required
def estrategia_edit(request,estrategia_id):
    jsonRsp = {}
    estrategia = get_object_or_404(Estrategia, pk=estrategia_id)
    bots = Bot.objects.filter(estrategia_id=estrategia_id)
    clases = Estrategia.get_clases()
    qtyBots = len(bots)
    if request.method == 'GET':
        return render(request, 'estrategia_edit.html',{
            'title': 'Editar estrategia '+estrategia.nombre,
            'estrategia_id': estrategia.id,
            'nombre': estrategia.nombre,
            'clase': estrategia.clase,
            'clases': clases,
            'activo': estrategia.activo,
            'qtyBots': qtyBots,
            'parametros': estrategia.parse_parametros(),
        })
    else:

        estrategia.nombre=request.POST['nombre'] 
        estrategia.clase=request.POST['clase']
        estrategia.parametros=request.POST['parametros']
        
        try:
            estrategia.full_clean()

            estrategia.save()
            jsonRsp['ok'] = '/bot/estrategia/'+str(estrategia.id)

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
def estrategia_toogle_activo(request,estrategia_id):
    estrategia = get_object_or_404(Estrategia, pk=estrategia_id)
    if estrategia.activo > 0:
        estrategia.activo = 0
    else:
        estrategia.activo = 1
    estrategia.save()
    return redirect('/bot/estrategia/'+str(estrategia.id))

@login_required
def estrategia_delete(request,estrategia_id):
    jsonRsp = {}
    estrategia = get_object_or_404(Estrategia, pk=estrategia_id)
    
    if estrategia.can_delete():
        estrategia.delete()
        jsonRsp['ok'] = True
    else:
        jsonRsp['error'] = 'No es psible eliminar la estrategia'
    return JsonResponse(jsonRsp)
    
    
