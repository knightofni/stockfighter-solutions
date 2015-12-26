import time

import arrow
import pandas as pd
from numpy import random

import stockfighter
from stockfighter.helpers import get_avg_price, get_vwap


def roll():
    return random.random()

def roll_normal(mean=1, std=1):
    return random.normal(mean, std)


def flush_old_orders(mm, seconds=120):
    # Cancel all open orders older than seconds
    df = mm.show_pending_orders()
    if not df.empty:
        df = df.loc[df.ts < arrow.utcnow().replace(seconds=-seconds).datetime]
        ids_to_cancel = df['id'].tolist()
        for oid in ids_to_cancel:
            mm.cancel(oid)
            print('Order {} cancelled'.format(oid))

def get_open_positions(mm):
    df = mm.show_pending_orders()
    if not df.empty:
        df['shares_on_market'] = df['qty'] - df['totalFilled']
        return df.groupby('direction')['shares_on_market'].sum().to_dict()
    else:
        return dict()

def market_making(quote, max_buy, max_sell):
    ## This market making algo is stupid
    if not quote.empty and quote.spread > 80:
        # let's quote better prices
        qty = int(roll_normal(150, 50))
        qty_buy = min(max_buy, qty)
        qty_sell = min(max_sell, qty)

        TB.buy(qty=qty_buy, price=quote.bid+10)
        TB.sell(qty=qty_sell,price=quote.ask-10)
        print('2] Making market (spread is {:.2f}), buying {} and selling {}'.format(quote.spread, qty_buy, qty_sell))
    elif quote.empty:
        pass
    else:
        print('2] Spread is {}, not trading'.format(quote.spread))

def info(iteration):
    if iteration % 20 == 0:
        GM.completion()
        ## Killing old orders
        flush_old_orders(MM, 30)
        (pps, position, value) = TB.calculate_position()
        if pps:
            print('****] Average cost : {:.2f}, shares acquired : {} - pnl: {:.2f}'.format(pps, position, value))


def risk_management():
    MAX_POS = 700

    # Checking how many buy / sell orders are opened, in qty
    position, open_buy, open_sell = TB.get_own_book()
    max_buy = max(0, (MAX_POS - position) - open_buy)
    max_sell = max(0, (position + MAX_POS) - open_sell)
    #print('Position : {} | Opens B {}- S {} | Maxs B {} - S {}'.format(position, open_buy, open_sell, max_buy, max_sell))
    return max_buy, max_sell


def print_result(res, vwap, forward_vwap):
    if res.get('ok'):
        direction = res.get('direction')
        fills = res.get('fills')
        qty = sum([f.get('qty') for f in fills])
        value = sum([(f.get('price') /100) * f.get('qty') for f in fills])
        pps = 0 if qty == 0 else value / qty
        print('{}] {} shares at price {:.2f} [vwap={:.2f}, fvwap={:.2f}]'.format(direction, qty, pps, vwap, forward_vwap))

GM = stockfighter.GameMaster()
GM.restart()
#GM.stop()
#GM.start('sell_side')
MM = stockfighter.MarketBroker(gm=GM)
TB = stockfighter.TraderBook(marketbroker=MM)
iteration = 0

while True:
    (pps, position, value) = TB.calculate_position()
    max_buy, max_sell = risk_management()
    vwap = get_vwap(MM)
    quote = MM.current_quote()

    ## Fleecing the sheeps
    #vwap = get_avg_price(MM)
    if not quote.empty and not vwap.empty:
        mispricing_thold = 0.98
        if len(vwap) > 20:
            cur_vwap = vwap.iloc[-1]
            forward_vwap = cur_vwap * (cur_vwap / vwap.iloc[-21])
        else:
            forward_vwap = cur_vwap = vwap.iloc[-1]

        quote = MM.current_quote()

        res_b, res_s = None, None
        if quote.ask > 0 and forward_vwap * mispricing_thold > quote.ask:
            res_b = TB.buy(qty=min(max_buy, quote.askSize), price=quote.ask, order_type='immediate-or-cancel')
        if quote.bid > 0 and forward_vwap / mispricing_thold < quote.bid:
            res_s = TB.sell(qty=min(max_sell, quote.bidSize), price=quote.bid, order_type='immediate-or-cancel')

        if res_b:
            print_result(res_b, cur_vwap, forward_vwap)

        if res_s:
            print_result(res_s, cur_vwap, forward_vwap)




    ## Market Making
    #market_making(quote, max_buy, max_sell)

    ## Information
    iteration +=1
    time.sleep(0.25)
    info(iteration)
