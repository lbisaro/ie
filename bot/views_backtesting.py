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
        return render(request, 'backtesting.html')

