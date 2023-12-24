from scripts.Exchange import Exchange
from bot.models import *
from bot.model_kline import *
from user.models import UserProfile
import scripts.functions as fn

from app_log import app_log as Log

def run():
    log = Log()
    json_rsp = {}
    startDt = datetime.now()
    #log.info(f'START {startDt}')
    print(f'START {startDt}')

    json_rsp['error'] = []

    ### Establecer hora y minutos de start para definir que estrategias ejecutar de acuerdo al intervalo
    apply_intervals = fn.get_apply_intervals(startDt)
    json_rsp['apply_intervals'] = apply_intervals
    
    ### Obtener estrategias activas (Activas y Con bots activos) con intervalos aplicables a la hora de ejecucion del script
    ### Crear una lista con los Symbol de las estrategias activas
    estrategias = Estrategia.get_estrategias_to_run(apply_intervals)
    active_symbols = []
    for estr in estrategias:
        #log.info(f'Estrategia: {estr}')
        gen_bot = GenericBotClass().get_instance(estr.clase)
        gen_bot.set(estr.parse_parametros())
        try:
            gen_bot.valid()
            bot_symbols = gen_bot.get_symbols()
            for sym in bot_symbols:
                active_symbols.append(sym)
        except Exception as err:
            raise ValidationError(err)
        

    ### Actualizar velas de los Symbols
    exchInfo = Exchange(type='info',exchange='bnc',prms=None)
    try:
        update_klines = exchInfo.update_klines()
        json_rsp['klines'] = update_klines
                
    except Exception as err:
        err = str(err)
        msg_text = f'No fue posible encontrar velas\n{err}'
        json_rsp['error'].append(msg_text)
    

    ## Obtener precios de los symbols activos
    prices = exchInfo.get_all_prices()

    ### Valida que los symbols de las estrategias se encuentren actualizados
    actSymOk = True
    for actSym in active_symbols:
        if not json_rsp['klines'][actSym]['updated']:
            actSymOk = False
   

    ### Si el symbol se encuentra actualizado ejecuta la estrategia
    signals = {}
    if actSymOk:
        print(f'actSymOk OK')
        actions = []
        ### Buscar Señales
        for estr in estrategias:
            botClass = estr.get_instance()

            signal_res = botClass.get_signal()
            if not signal_res['ok']:
                json_rsp['error'].append(signal_res['error'])
            else:
                signal = signal_res['signal']
                signals[estr.id] = signal
        
        ### - Obtener lista de bots activos ordenados por usuario_id
        bots = Bot.get_bots_activos()
        usuario_id = 0
        for bot in bots:
            botClass = bot.get_instance()
            botClass.bot_id = bot.id

            if bot.usuario.id != usuario_id:
                #log.info(f'Usuario: {bot.usuario.username}')
                usuario_id = bot.usuario.id
                profile = UserProfile.objects.get(user_id=bot.usuario.id)
                profile_config = profile.parse_config()
                prms = {}
                prms['bnc_apk'] = profile_config['bnc']['bnc_apk']
                prms['bnc_aps'] = profile_config['bnc']['bnc_aps']
                prms['bnc_env'] = profile_config['bnc']['bnc_env']
                       

                exch = Exchange(type='user_apikey',exchange='bnc',prms=prms)
                wallet = exch.get_wallet() 

            #log.info(f'Bot: {bot}')
            price = prices[botClass.symbol]
            pos_orders = bot.get_pos_orders()

            ### - Disparar las señales a los bots activos
            ### - Cuando se dispare una señal a un Bot 
            ###     - Si el bot NO PUEDE EJECUTARLA por cuestiones relacionadas con el capital. Inactivar el Bot
            ###     - Si SE EJECUTA una compra/venta, registrar SL y TP en caso que aplique
            signal = 'NEUTRO'
            if bot.estrategia_id in signals:
                signal = signals[bot.estrategia_id]
            if signal != 'NEUTRO':
                log.info(f'Signal: {signal}')
            
            #Forzar signal
            #signal = 'VENTA'
            #signal = 'COMPRA'
            
            execRes = botClass.execute_live(exchange = exch, 
                                       signal=signal, 
                                       price=price, 
                                       wallet=wallet, 
                                       pos_orders=pos_orders)
            if len(execRes) > 0:
                log.info(f'Execute: {execRes}')
            if 'execute' in execRes and execRes['execute'] == 'CLOSE':
                closeRes = bot.close_pos()
                log.info(f'Close: {closeRes}')

    
    #Buscar ordenes incompletas, agrupadas por usuario
    #Si existen, reconectar con el Exchange para cada usuario 
    # Repetir la busqueda de ordenes incompletas en un bucle para todos los usuarios  
    # El bucle no puede ser infinito
    # Si quedan ordenes incompletas, se revisaran en la proxima corrida del crontab


    #Para cada job activo recalcular max-drawdown y demas indicadores y cachearlo en la db
    # Luego del recalculo verificar si se debe detener el bot por exceder
    # el max-drawdown general o el stop-loss general


    ### Control de errores
    if len(json_rsp['error']) > 0:
        json_rsp['ok'] = False
    else:
        json_rsp['ok'] = True
    if not json_rsp['ok']:
        for k,v in json_rsp.items():
            if k == 'klines':
                for rk,rv in json_rsp['klines'].items():
                    log.error(f'klines -> {rk}: {rv}')   
            elif k == 'error':
                for err in json_rsp['error']:
                    log.error(f"ERROR -> {err}")    
            else:
                log.info(f"{k}: {v}")

    print('Ready')

    #endDt = datetime.now()
    #log.info(f'END {endDt}')