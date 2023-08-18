from django.contrib import admin
from django.urls import path

from bot import views_estrategia as ve
from bot import views_bot as vb
from bot import views_backtesting as vbt
from bot import views_api as api

urlpatterns = [
    path('estrategias/',ve.estrategias,name='estrategias'),
    path('estrategia/<int:estrategia_id>/',ve.estrategia,name='estrategia'),
    path('estrategia/create/',ve.estrategia_create,name='estrategia_create'),
    path('estrategia/load_parametros/<str:clase>/',ve.load_parametros,name='est_load_parametros'),
    path('estrategia/edit/<int:estrategia_id>/',ve.estrategia_edit,name='estrategia_edit'),
    path('estrategia/toogle_activo/<int:estrategia_id>/',ve.estrategia_toogle_activo,name='estrategia_toogle_activo'),
    path('estrategia/delete/<int:estrategia_id>/',ve.estrategia_delete,name='estrategia_delete'),

    path('bots/',vb.bots,name='bots'),
    path('bot/<int:bot_id>/',vb.bot,name='bot'),
    path('bot/create/',vb.bot_create,name='bot_create'),
    path('bot/get_parametros_estrategia/<int:estrategia_id>/',vb.get_parametros_estrategia,name='get_parametros_estrategia'),
    path('bot/edit/<int:bot_id>/',vb.bot_edit,name='bot_edit'),
    path('bot/toogle_activo/<int:bot_id>/',vb.bot_toogle_activo,name='bot_toogle_activo'),
    path('bot/delete/<int:bot_id>/',vb.bot_delete,name='bot_delete'),

    path('api/bots/',api.bots,name='api_bots'),
    path('api/bot/run/<int:bot_id>/',api.bot_run,name='api_bot_run'),

    path('backtesting/',vbt.backtesting,name='backtesting'),
]