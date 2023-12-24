from bot.model_kline import *
import pandas as pd
import time
import datetime as dt
from scripts.Exchange import Exchange
from scripts.BotBT import BotBT
from django.utils import timezone
from scripts.functions import round_down
from scripts.backtesting.backtesting import Backtest, Strategy
from scripts.backtesting.lib import resample_apply


class BotBTLong(BotBT):

    symbol = ''
    quote_perc = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    interes = ''

    descripcion = 'Bot basado en Backtesting.py \n'\
                  'Ejecuta la compra al recibir una señal de Compra, '\
                  'y cierra la operación por Stop Loss o Take Profit (Si se definen con un % mayor a cero) '\
                  'o cuando recibe una señal de Venta.'
    
    parametros = {'symbol':  {  
                        'c' :'symbol',
                        'd' :'Par',
                        'v' :'BTCUSDT',
                        't' :'symbol',
                        'pub': True,
                        'sn':'Sym',},
                'quote_perc': {
                        'c' :'quote_perc',
                        'd' :'Operacion sobre capital',
                        'v' :'100',
                        't' :'perc',
                        'pub': True,
                        'sn':'Quote', },
                'stop_loss': {
                        'c' :'stop_loss',
                        'd' :'Stop Loss',
                        'v' :'2',
                        't' :'perc',
                        'pub': True,
                        'sn':'SL', },
                'take_profit': {
                        'c' :'take_profit',
                        'd' :'Take Profit',
                        'v' :'0',
                        't' :'perc',
                        'pub': True,
                        'sn':'TP', },
                'interes': {
                        'c' :'interes',
                        'd' :'Tipo de interes',
                        'v' :'c',
                        't' :'t_int',
                        'pub': True,
                        'sn':'Int', },
                }

    def valid(self):
        err = []
        if len(self.symbol) < 1:
            err.append("Se debe especificar el Par")
        if self.quote_perc <= 0:
            err.append("El Porcentaje de capital por operacion debe ser mayor a 0")
        if self.stop_loss < 0 or self.stop_loss > 100:
            err.append("El Stop Loss debe ser un valor entre 0 y 100")
        if self.take_profit < 0 or self.take_profit > 100:
            err.append("El Take Profit debe ser un valor entre 0 y 100")
        if self.interes != 'c' and self.interes != 's':
            err.append("Se debe establecer el tipo de interes. (Simple o Compuesto)")
        
        if len(err):
            raise Exception("\n".join(err))
    
    def get_symbols(self):
        return [self.symbol]
    
    def addStrategy(self,strategy):
        self._strategy = strategy

        
    def backtest(self,klines,from_date,to_date,to_get='complete'):
        self.res = {}

        self.backtesting = True
        
        exch = Exchange(type='info',exchange='bnc',prms=None)
        symbol_info = exch.get_symbol_info(self.symbol)
        self.base_asset = symbol_info['base_asset']
        self.quote_asset = symbol_info['quote_asset']
        self.qd_price = symbol_info['qty_decs_price']
        self.qd_qty = symbol_info['qty_decs_qty']
        self.qd_quote = symbol_info['qty_decs_quote']

        
        self.klines = klines
        #Aplicar la señal de compra/venta
        self.klines = self.signal(self.klines)
        #quitando las velas previas a la fecha de start
        self.klines = self.klines[self.klines['datetime'] >= pd.to_datetime(from_date)]
        self.klines = self.klines.reset_index(drop=True)
        self.klines['unix_dt'] = (self.klines['datetime'] - dt.datetime(1970, 1, 1)).dt.total_seconds() * 1000 +  10800000

        self.klines = self.signal(self.klines)

        self.klines.set_index('datetime',inplace=True)
        self.klines.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        cash = self.quote_qty

        
        self._bt = Backtest(self.klines, self._strategy, cash=cash, commission=(self.exch_comision_perc/100), trade_on_close=False)
        
        self._bt._strategy.cash = self.quote_qty

        
        velas = int(self.klines['Close'].count())

        if velas<50:
            self.res['ok'] = False
            self.res['error'] = 'El intervalo y rango de fechas solicitado genera un total de '+str(velas)+' velas'+\
                    '<br>Se requiere un minimo de '+str(self.VELAS_PREVIAS)+' velas para poder realizar el Backtesting'
            return self.res
        

        #Procesando resultados
        stats = self.run()
        
        print(f'Periodo: {stats.Start} al {stats.End}')
        print(f'Duracion: {stats.Duration}')
        print('Return (Ann.) [%]',stats['Return (Ann.) [%]'])
        print('Max. Drawdown [%]',stats['Max. Drawdown [%]'])
        print('# Trades',stats['# Trades'])
        
        equity = stats._equity_curve
        self.klines['usd_strat'] = equity['Equity']
        price_to_hold = self.klines.iloc[0]['Close'] 
        quote_to_hold = round( self.quote_qty*(self.quote_perc/100) , self.qd_quote )
        qty_to_hold = round( ( quote_to_hold / price_to_hold ) , self.qd_qty ) 
        usd_in_hold = round( self.quote_qty - quote_to_hold , self.qd_quote )
        self.klines['usd_hold'] = round( self.klines['Close'] * qty_to_hold + usd_in_hold, self.qd_quote )

        #Preparando data para el grafico
        self.klines['datetime'] = self.klines.index
        if self.interval_id < '2d01':
            agg_funcs = {
                    "unix_dt": "first",
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum",
                    "usd_hold": "last",
                    "usd_strat": "last",
                }   
            new_df = self.klines[['datetime','unix_dt','Open','High','Low','Close','Volume','usd_hold','usd_strat']].resample('1D', on="datetime").agg(agg_funcs).reset_index()
        else:
            new_df = self.klines[['datetime','unix_dt','Open','High','Low','Close','Volume','usd_hold','usd_strat']]

        rename_columns = {'unix_dt': 'dt', 
                          'Open': 'o', 
                          'High': 'h', 
                          'Low': 'l', 
                          'Close': 'c', 
                          'Volume': 'v', 
                          'usd_hold': 'uH', 
                          'usd_strat': 'uW'}
        ohlc = new_df[['unix_dt','Open','High','Low','Close','Volume','usd_hold','usd_strat']].rename(columns=rename_columns).to_dict(orient='records')
    
        #Procesando trades
        self.trades = stats._trades.copy()
        
        self.trades['EntryDate'] = self.trades['EntryTime'].dt.date
        self.trades['ExitDate'] = self.trades['ExitTime'].dt.date
        self.trades['unix_dt_entry'] = pd.to_datetime(self.trades['EntryDate']).apply(lambda x: int(x.timestamp())) * 1000 +  10800000
        self.trades['unix_dt_exit'] = pd.to_datetime(self.trades['ExitDate']).apply(lambda x: int(x.timestamp())) * 1000 +  10800000

        self.trades = self.trades.rename(columns={'EntryTime':'start',
                                    'ExitTime':'end',
                                    'EntryPrice':'buy_price',
                                    'ExitPrice':'sell_price',
                                    'Size':'qty',
                                    'PnL':'result_usd',
                                    'ReturnPct':'result_perc',
                                    'Tag':'flag',
                                    })
        self.trades['days'] = (self.trades['end'] - self.trades['start']).dt.total_seconds() / 60 / 60 / 24

        #Eventos de compra y venta para el grafico
        by = self.trades[['unix_dt_entry','buy_price']].rename(columns={'unix_dt_entry':'dt','buy_price':'by'}).to_dict(orient='records')
        sls = self.trades[(self.trades['flag']!=self.ORD_FLAG_STOPLOSS) & (self.trades['flag']!=self.ORD_FLAG_TAKEPROFIT)][['unix_dt_exit','sell_price']].rename(columns={'unix_dt_exit':'dt','sell_price':'sls'}).to_dict(orient='records')
        slsl = self.trades[self.trades['flag']==self.ORD_FLAG_STOPLOSS][['unix_dt_exit','sell_price']].rename(columns={'unix_dt_exit':'dt','sell_price':'slsl'}).to_dict(orient='records')
        sltp = self.trades[self.trades['flag']==self.ORD_FLAG_TAKEPROFIT][['unix_dt_exit','sell_price']].rename(columns={'unix_dt_exit':'dt','sell_price':'sltp'}).to_dict(orient='records')
        
        events = by+sls+slsl+sltp

        
        dict_trades = []
        for i,trade in self.trades.iterrows():
                trd = [
                    trade['start'],
                    trade['buy_price'],
                    trade['qty'],
                    trade['end'],
                    trade['sell_price'],
                    trade['flag'],
                    trade['days'],
                    trade['result_usd'],
                    trade['result_perc'],
                    '',
                    '',
                    ]
                dict_trades.append(trd)

        
        #new_df = self.klines[['unix_dt','signal','low','high']]
        #sB = self.klines[self.klines['signal']=='COMPRA'][['unix_dt','low']].rename(columns={'unix_dt':'dt','low':'sB'}).to_dict(orient='records')
        #sS = self.klines[self.klines['signal']=='VENTA'][['unix_dt','high']].rename(columns={'unix_dt':'dt','high':'sS'}).to_dict(orient='records')

        res = { 'ok': True,
                'error': False,
                'order_side': { 
                        self.ORD_SIDE_BUY:'BUY',
                        self.ORD_SIDE_SELL:'SELL',
                        },
                'order_flag': { 
                        self.ORD_FLAG_SIGNAL:'SIGNAL',
                        self.ORD_FLAG_STOPLOSS:'STOP-LOSS',
                        self.ORD_FLAG_TAKEPROFIT:'TAKE-PROFIT',
                        },
                'qd_price': self.qd_price, 
                'qd_qty': self.qd_qty, 
                'qd_quote': self.qd_quote, 
                'data': ohlc, 
                'events': events,
                'orders': [], 
                'trades': dict_trades, 
                'brief': [],
                }
        
        if to_get=='ind':
            res = self.get_resultados()
            print(res)
            return res
        
        res['brief'] = self.get_brief()
             
        return res
    