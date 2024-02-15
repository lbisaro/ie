import pandas as pd
import datetime as dt

from django.utils import timezone

from scripts.Bot_Core_utils import Order as BotCoreUtilsOrder
from scripts.functions import round_down


class Bot_Core_live:

    def live_get_signal(self,klines):
        self.klines = klines
        self.start()
        return self.klines.iloc[-2]
    
    def live_execute(self, exchange, signal_row, price, wallet, orders):
        self._orders = {}
        self._trades = {}
        self.backtesting = False
        self.live = True
        self.exchange = exchange
        self.wallet = wallet

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

        #Calculo del estado de la posicion actual
        self.load_orders(orders)
        
        if self.live_check_orders():
            jsonRsp['execute'] = True

        self.next()
        
        print('ORDERS')
        for k in self._orders:
            print(self._orders[k])
        print('TRADES')
        for k in self._trades:
            print(self._trades[k])
        return jsonRsp

    def live_check_orders(self):
        
        executed = False
        price = self.price
       
        if len(self._orders) > 0:
            
            _orders = self._orders.copy().items()
            
            for i,order in _orders:
                
                if i in self._orders: #Se consulta si esta o no porque puede que se ejecute mas de una orden en la misma vela
                    order  = self._orders[i]

                    if order.type == BotCoreUtilsOrder.TYPE_LIMIT:
                        
                        if order.side == BotCoreUtilsOrder.SIDE_BUY and order.flag != BotCoreUtilsOrder.FLAG_STOPLOSS:
                            if price <= order.limit_price:
                                executed =  self.execute_order(order.id)
                                
                        if order.side == BotCoreUtilsOrder.SIDE_BUY and order.flag == BotCoreUtilsOrder.FLAG_STOPLOSS:
                            if price >= order.limit_price:
                                executed =  self.live_execute_order(order.id)

                        if order.side == BotCoreUtilsOrder.SIDE_SELL and order.flag != BotCoreUtilsOrder.FLAG_STOPLOSS:
                            print('Check Order ',order)
                            if price >= order.limit_price:
                                print('Ejecutando')
                                executed = self.live_execute_order(order.id)
                                
                        if order.side == BotCoreUtilsOrder.SIDE_SELL and order.flag == BotCoreUtilsOrder.FLAG_STOPLOSS:
                            print('Check Order ',order)
                            if price <= order.limit_price:
                                print('Ejecutando')
                                executed = self.live_execute_order(order.id)

                    if order.type == BotCoreUtilsOrder.TYPE_TRAILING:
                        raise Exception('/------------------- EXECUTE ORDER TRAIL - PENDIENTE DE DESARROLLO ---------------------/')
                        """
                        if order.side == BotCoreUtilsOrder.SIDE_SELL:
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

                        if order.side == BotCoreUtilsOrder.SIDE_BUY:
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
                        """
        
        return executed
    
    def live_execute_order(self,orderid):
        wallet = self.wallet
        exchange = self.exchange
        broker_wallet_base  = round_down(wallet[self.base_asset]['free'],self.qd_qty)
        broker_wallet_quote = round_down(wallet[self.quote_asset]['free'],self.qd_quote)
        symbol = self.symbol

        order = self._orders[orderid]
        qty = order.qty

        try:
            if order.side == BotCoreUtilsOrder.SIDE_BUY:
                str_side = 'BUY'
                exch_order = exchange.order_market_buy(symbol=symbol, qty= qty)
            else:
                str_side = 'SELL'
                exch_order = exchange.order_market_sell(symbol=symbol, qty= qty)
        except Exception as e:
            print(e)
            return False

        """
        Binance order status:

        ORDER_STATUS_NEW = 'NEW'
        ORDER_STATUS_PARTIALLY_FILLED = 'PARTIALLY_FILLED'
        ORDER_STATUS_FILLED = 'FILLED'
        ORDER_STATUS_CANCELED = 'CANCELED'
        ORDER_STATUS_PENDING_CANCEL = 'PENDING_CANCEL'
        ORDER_STATUS_REJECTED = 'REJECTED'
        ORDER_STATUS_EXPIRED = 'EXPIRED'
        """
        
        if exch_order['status'] != 'CANCELED' and \
           exch_order['status'] != 'PENDING_CANCEL' and \
           exch_order['status'] != 'REJECTED' and \
           exch_order['status'] != 'EXPIRED':
            
            order.completed = 1 if exch_order['status'] == 'FILLED' else 0
            order.price = 0
            if order.completed == 1:
                order.price = round(float(exch_order['cummulativeQuoteQty'])/float(exch_order['executedQty']),self.qd_price)
                order.qty = round(float(exch_order['executedQty']),self.qd_qty)
            order.orderid = exch_order['orderId']
            order = self.update_order(order)

            #Pasa la orden a trade
            del self._orders[order.id]
            self._trades[order.id] = order

            order_quote = round(order.qty*order.price,self.qd_quote)
            if order.side == BotCoreUtilsOrder.SIDE_BUY:
                self.wallet_base += order.qty
                self.wallet_quote -= order_quote
            else:
                self.wallet_base -= order.qty
                self.wallet_quote += order_quote
            
            self.on_order_execute()
            return True
        
        print('Exec. Order ERROR ',exch_order['status'],str(order))
        return False 

    
    def load_orders(self, orders):
        self.wallet_base = 0
        self.wallet_quote = self.quote_qty
        for order in orders:
            if order.completed > 0:
                if order.pos_order_id == 0:
                    self._trades[order.id] = order
                order_quote = round(order.qty*order.price,self.qd_quote)
                if order.side == BotCoreUtilsOrder.SIDE_BUY:
                    self.wallet_base += order.qty
                    self.wallet_quote -= order_quote
                else:
                    self.wallet_base -= order.qty
                    self.wallet_quote += order_quote
            else:
                self._orders[order.id] = order
            if order.id > self.order_id:
                self.order_id = order.id
