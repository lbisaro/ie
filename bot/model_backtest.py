from django.db import models
from django.utils import timezone
from bot.models import GenericBotClass
from user.models import User
import pandas as pd
import json
import functions as fn
import glob
import os
import pickle

class Backtest(models.Model):

    ESTADO_CREADO = 0
    ESTADO_INICIADO = 10
    ESTADO_ENCURSO = 50
    ESTADO_COMPLETO = 100

    klines_folder = './backtest/klines/'
    results_folder = './backtest/results/'

    clase = models.SlugField(max_length = 50, null=False, blank=False)
    parametros = models.TextField(null=False, blank=False)
    interval_id = models.CharField(max_length = 8, null=False, blank=False)
    estado = models.IntegerField(null=False, blank=False, default=0)
    completo = models.FloatField(null=False, blank=False, default=0)
    creado = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(User, on_delete = models.CASCADE) 
    
    def __str__(self):
        interval = fn.get_intervals(self.interval_id,'binance')
        str = f'{self.clase} {interval} {self.creado}'
        return str
    
    def name(self):
        return f'{self.clase} #{self.id}'

    def str_estado(self):
        estados = {}
        estados[self.ESTADO_CREADO] = 'Creado'
        estados[self.ESTADO_INICIADO] = 'Iniciado'
        estados[self.ESTADO_ENCURSO] = 'En curso'
        estados[self.ESTADO_COMPLETO] = 'Completo'
        return estados[self.estado]
    
    def str_interval(self):
        interval = fn.get_intervals(self.interval_id,'binance')
        return interval

    def iniciar(self):
        resultados = {}
        resultados['id'] = self.id
        resultados['periodos'] = self.get_periodos(self.interval_id)
        self.set_resultados(resultados)
        self.estado = self.ESTADO_INICIADO
        self.save()

    def log_resultados(self,resultados,msg):
        resultados['log'].append({'dt':timezone.now,'msg':msg,})

    def set_resultados(self,resultados):
        with open(self.get_results_file(), 'wb') as f:
            pickle.dump(resultados, f)
        return resultados
    
    def get_resultados(self):
        with open(self.get_results_file(), 'rb') as f:
            resultados = pickle.load(f)
        return resultados

    def get_resumen_resultados(self):
        resultados = self.get_resultados()

        json_rsp = {}
        df_media = None
        for periodo in resultados['periodos']:

            start_date = periodo['start']
            end_date = periodo['end']
            symbol = periodo['symbol']
            tendencia = periodo['tendencia']
            if periodo['bt']:
                if not tendencia in json_rsp:
                    json_rsp[tendencia] = pd.DataFrame(periodo['bt'],columns=['ind',symbol])
                else:
                    tmp_df = pd.DataFrame(periodo['bt'],columns=['ind',symbol])
                    json_rsp[tendencia][symbol] = tmp_df[symbol]
            
        for periodo in resultados['periodos']:
            tendencia = periodo['tendencia']
            
            json_rsp[tendencia]['Media'] = json_rsp[tendencia].drop(columns=['ind']).mean(axis=1)
            json_rsp[tendencia]['Dev.Est.'] = json_rsp[tendencia].drop(columns=['ind']).std(axis=1)
            
            col_media_tendencia = f'Media {tendencia}'
            if not 'Media' in json_rsp:
                json_rsp['Media'] = json_rsp[tendencia][['ind','Media']]
                json_rsp['Media'] = json_rsp['Media'].rename(columns={'Media': col_media_tendencia})
            else:
                json_rsp['Media'][col_media_tendencia] = json_rsp[tendencia]['Media']
            
        
        #Formateando los dataframes generados
        ind_names = []
        ind_names.append({'ind':'ratio_dias_sin_operar','name':'Ratio de Dias sin operar'})  
        ind_names.append({'ind':'trades_x_mes','name':'Operaciones mensuales'})
        ind_names.append({'ind':'ratio_trade_pos','name':'Ratio operaciones positivas vs negtivas'})
        ind_names.append({'ind':'ratio_perdida_ganancia','name':'Ratio de Perdida vs Ganancia'}) 
        ind_names.append({'ind':'ratio_max_perdida_ganancia','name':'Ratio de Max.Perdida vs Max.Ganancia'}) 
        ind_names.append({'ind':'maximo_operaciones_negativas_consecutivas','name':'Max. operaciones negativas consecutivas'}) 
        ind_names.append({'ind':'mea_promedio','name':'MEA Promedio'}) 
        ind_names.append({'ind':'mef_promedio','name':'MEF Promedio'}) 
        ind_names.append({'ind':'ratio_volatilidad','name':'Ratio de Volatilidad'})
        ind_names.append({'ind':'max_drawdown_cap','name':'Max. DrawDown Capital'})
        ind_names.append({'ind':'ratio_max_drawdown','name':'Ratio Max. DrawDown Capital vs Par'})
        ind_names.append({'ind':'ratio_max_drawup','name':'Ratio Max. DrawUp Capital vs Par'})
        ind_names.append({'ind':'cagr','name':'CAGR'}) 
        ind_names.append({'ind':'ratio_cagr_drawdown','name':'Ratio CAGR vs DrawDown'})
        ind_names.append({'ind':'ratio_calmar','name':'Ratio CALMAR'})
        ind_names.append({'ind':'modificacion_sharpe','name':'Ratio SHARPE Modificado'})
        df_ind_names = pd.DataFrame(ind_names, columns=['ind','name'])
        df_ind_names = df_ind_names.set_index('ind')

        for key in json_rsp:
            print(key)
            json_rsp[key] = json_rsp[key].set_index('ind')
            json_rsp[key] = json_rsp[key].round(2)
            json_rsp[key].insert(0, 'Indicador', df_ind_names['name'])

        return json_rsp
        
    def get_results_file(self):
        file = f'{self.results_folder}id_{self.id}.json'
        return file

    def get_periodos(self,interval_id):

        interval = fn.get_intervals(interval_id,'binance')

        if interval:
            files = glob.glob(self.klines_folder+interval_id+'/*.DataFrame')
            periodos = []
            for f in files:
                file = f
                f = f.replace(os.sep, '')
                f = f.replace('.DataFrame', '')
                f = f.replace(self.klines_folder+interval_id, '')
                parts = f.split('_')
                tendencia = parts[0]
                symbol = parts[1]
                interval = parts[2]
                start = parts[3]
                end = parts[4]
                key = len(periodos)
                periodos.append({
                            'key': key,
                            'tendencia':tendencia,
                            'interval':interval,
                            'interval_id': interval_id,
                            'start': start,
                            'end': end,
                            'symbol': symbol,
                            'str': f'{symbol} {tendencia} desde el {start} al {end}',
                            'file': file,
                            'procesado': 'NO',
                            }
                        )
                            
        return periodos
    
    def parse_parametros(self):
        gen_bot = GenericBotClass().get_instance(self.clase)
        parametros = gen_bot.parametros
        pe = eval(self.parametros)
        for prm in pe:
            for v in prm:
                parametros[v]['v'] = prm[v]
                parametros[v]['str'] = prm[v]

                if parametros[v]['t'] == 'perc':
                    val = float(parametros[v]['v'])
                    parametros[v]['str'] = f'{val:.2f} %'

                if parametros[v]['t'] == 't_int':
                    if parametros[v]['v'] == 's':
                        parametros[v]['str'] = 'Simple'
                    elif parametros[v]['v'] == 'c':
                        parametros[v]['str'] = 'Compuesto'
                
                    
        return parametros

    def str_parametros(self):
        prm = self.parse_parametros()
        str = ''
        for p in prm:
            if str != '':
                str += ', '
            str += p['v']
        return f"{str}"

    def get_instance(self):
        gen_bot = GenericBotClass().get_instance(self.clase)
        gen_bot.set(self.parse_parametros())
        gen_bot.interval_id = self.interval_id

        return gen_bot

    def get_df_from_file(self,file):
        with open(file, 'rb') as f:
            df = pickle.load(f)
        return df
