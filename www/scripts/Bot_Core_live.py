import pandas as pd
import datetime as dt

from scripts.Bot_Core_utils import *
from scripts.functions import round_down

class Bot_Core_live:

    def live_get_signal(self,klines):
        self.klines = klines
        self.start()
        return self.klines.iloc[-2]
    
    def live_execute(self, exchange, signal_row, price, wallet, orders):
        self.backtesting = False
        self.live = True

        jsonRsp = {}
        
        symbol_info = exchange.get_symbol_info(self.symbol)
        self.base_asset = symbol_info['base_asset']
        self.quote_asset = symbol_info['quote_asset']
        self.qd_price = symbol_info['qty_decs_price']
        self.qd_qty = symbol_info['qty_decs_qty']
        self.qd_quote = symbol_info['qty_decs_quote']

        self.price = price
        self.signal = signal_row['signal']
        self.datetime = dt.datetime.now()
        self.row = signal_row

        broker_wallet_base  = round_down(wallet[self.base_asset]['free'],self.qd_qty)
        broker_wallet_quote = round_down(wallet[self.quote_asset]['free'],self.qd_quote)

        #Calculo del estado de la posicion actual
        self.load_orders(orders)
        
        self.live_check_orders()
        self.next()

        
        """
        for order in pos_orders:
            if order.completed == 0:
                jsonRsp['error'] = 'Existen ordenes incompletas'
                return jsonRsp

            order_quote = round( round(order.qty,self.qd_qty) * round(order.price,self.qd_price) , self.qd_quote )
            if order.side == Order.SIDE_BUY:

                self.wallet_quote -= order_quote
                self.wallet_base += order.qty
                base_in_usd += order_quote
            else:
                self.wallet_quote += order_quote
                self.wallet_base -= order.qty
                base_in_usd -= order_quote

        self.wallet_base    = round(self.wallet_base,self.qd_qty)
        base_in_usd = round(base_in_usd,self.qd_quote)
        self.wallet_quote   = round(self.wallet_quote,self.qd_quote)

        if self.wallet_base > 0:
            price_calculated = base_in_usd / self.wallet_base
            stop_loss_price = round( price_calculated - (price_calculated * ( self.stop_loss/100) ) , self.qd_price )
            take_profit_price = round( price_calculated + (price_calculated * ( self.take_profit/100) ) , self.qd_price )


        if signal == 'COMPRA' and self.wallet_quote == 0:
            if self.interes == 's': #Interes Simple
                quote_to_sell = round( self.wallet_quote*(self.quote_perc/100) , self.qd_quote )
            else: #Interes Compuesto
                quote_to_sell = round( self.wallet_quote*(self.quote_perc/100) , self.qd_quote )
            if wallet[self.quote_asset]['free'] >= quote_to_sell:
                qty = round( ( quote_to_sell / price ) , self.qd_qty )
                if self.market_buy(exchange,self.symbol,qty,Order.FLAG_SIGNAL):
                    jsonRsp['execute'] = 'OPEN'
                else:
                    jsonRsp['error'] = 'ORDER_NOT_PLACED'

        elif signal == 'VENTA' and self.wallet_base > 0:
            if wallet[self.base_asset]['free'] >= self.wallet_base:
                qty = self.wallet_base
                if self.market_sell(exchange,self.symbol,qty,Order.FLAG_SIGNAL):
                    jsonRsp['execute'] = 'CLOSE'
                else:
                    jsonRsp['error'] = 'ORDER_NOT_PLACED'

        else: #Si no hay una señal de compra venta, revisa Stop-Loss y Take-Profit
            if self.wallet_base > 0:
                if self.stop_loss > 0 and stop_loss_price > price:
                    if wallet[self.base_asset]['free'] >= self.wallet_base:
                        qty = self.wallet_base
                        if self.market_sell(exchange,self.symbol,qty,Order.FLAG_STOPLOSS):
                            jsonRsp['execute'] = 'CLOSE'
                        else:
                            jsonRsp['error'] = 'ORDER_NOT_PLACED'

                if self.take_profit > 0 and take_profit_price < price:
                    if wallet[self.base_asset]['free'] >= self.wallet_base:
                        qty = self.wallet_base
                        if self.market_sell(exchange,self.symbol,qty,Order.FLAG_TAKEPROFIT):
                            jsonRsp['execute'] = 'CLOSE'
                        else:
                            jsonRsp['error'] = 'ORDER_NOT_PLACED'
        """
        return jsonRsp

    def live_check_orders(self):
        
        executed = False
        price = self.price
       
        if len(self._orders) > 0:
            
            _orders = self._orders.copy().items()

            
            for i,order in _orders:
                
                if i in self._orders: #Se consulta si esta o no porque puede que se ejecute mas de una orden en la misma vela
                    order  = self._orders[i]

                    if order.type == Order.TYPE_LIMIT:
                        
                        if order.side == Order.SIDE_BUY:
                            if price <= order.limit_price:
                                executed =  self.live_execute_order(order.id)
                                
                        if order.side == Order.SIDE_SELL and order.flag != Order.FLAG_STOPLOSS:
                            if price >= order.limit_price:
                                executed = self.live_execute_order(order.id)
                        
                        if order.side == Order.SIDE_SELL and order.flag == Order.FLAG_STOPLOSS:
                            if price <= order.limit_price:
                                executed = self.live_execute_order(order.id)

                    if order.type == Order.TYPE_TRAILING:

                        if order.side == Order.SIDE_SELL:
                            if order.active:
                                if price < order.limit_price:
                                    executed = self.live_execute_order(order.id)

                            if order.id in self._orders: #Verifica si la orden no se ejecuto
                                if not order.active and (price >= order.activation_price or order.activation_price == 0):
                                    order.active = True

                                if order.active:
                                    new_limit_price = price * (1-(order.trail_perc/100))
                                    if new_limit_price >= order.limit_price: 
                                        order.limit_price = round(new_limit_price,self.qd_price)
                                    if price < order.limit_price < price:
                                        executed = self.live_execute_order(order.id)

                        if order.side == Order.SIDE_BUY:
                            if order.active:
                                if price < order.limit_price < price:
                                    executed = self.live_execute_order(order.id)
                                    
                            if order.id in self._orders: #Verifica si la orden no se ejecuto
                                if not order.active and (price < order.activation_price or order.activation_price == 0):
                                    order.active = True
                                    
                                if order.active:
                                    new_limit_price = price * (1+(order.trail_perc/100))
                                    if new_limit_price <= order.limit_price: 
                                        order.limit_price = round(new_limit_price,self.qd_price)
                                    if price < order.limit_price < price:
                                        executed = self.live_execute_order(order.id)

        return executed
    
    def live_execute_order(self,orderid):
        print('Live Execute Order - En desarrollo',orderid)
        