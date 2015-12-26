import time
import random

import arrow

import stockfighter
from stockfighter.helpers import get_avg_price

def roll():
    return random.random()

def flush_old_orders(mm, seconds=120):
    # Cancel all open orders older than seconds
    df = mm.show_pending_orders()
    if not df.empty:
        df = df.loc[df.ts < arrow.utcnow().replace(seconds=-seconds).datetime]
        ids_to_cancel = df['id'].tolist()
        for oid in ids_to_cancel:
            mm.cancel(oid)
            print('Order {} cancelled'.format(oid))

def directional_purchase(quote):
    if GM.target_price_l2:
        if not quote.empty:
            if (quote.ask / 100) < GM.target_price_l2*0.99:
                MM.buy(qty=quote.askSize, order_type='iMMediate-or-cancel', price=quote.ask)
                print('1] Buying extra {} because good price [{}]!'.format(quote.askSize, quote.ask))
            else:
                print('1] Ask is {} - Target price is {}'.format(quote.ask/100, GM.target_price_l2))

def dead_market_check(quote):
    secs_no_trading = MM.seconds_without_trading()
    if secs_no_trading > 30:
        print('3] {:.1f} min without trading'.format(secs_no_trading/60))
        qty = int(roll() * 100)
        MM.sell(qty=qty, price=quote.bid, order_type='fill-or-kill')
        print('3] Selling {} shares at {} in FOK to try to restart the market'.format(qty, quote.bid))


def market_making(quote):
    if not quote.empty and quote.spread > 80:
        # let's quote better prices
        qty = roll()*5000
        delta = roll()*1000
        MM.buy(qty=qty+delta, price=quote.bid+10)
        if not GM.target_price_l2 or quote.ask > GM.target_price_l2:
            print('2] Making market (spread is {:.2f}), buy & sell [sell at {} (target price is {}])'.format(quote.spread,quote.ask-10, GM.target_price_l2))
            MM.sell(qty=max(100, qty-delta),price=quote.ask-10)
        else:
            print('2] Making market, buying only, spread is {}'.format(quote.spread))
    elif quote.empty:
        pass
    else:
        print('2] Spread is {}, not trading'.format(quote.spread))


GM = stockfighter.GameMaster()
#gm.restart()
#gm.stop()
#gm.start('chock_a_block')
MM = stockfighter.MarketMaker(gm=GM)
iteration = 0

while True:
    quote = MM.current_quote()
    ## Extra buying if good price (99% or less than target price)
    directional_purchase(quote)

    ## Market Making
    market_making(quote)

    ## How long without trading ?
    dead_market_check(quote)

    ## Information
    time.sleep(1)
    iteration +=1
    if iteration % 10 == 0:
        GM.completion()
        ## Killing old orders
        flush_old_orders(MM)
        (pps, position, value) = MM.calculate_position()
        if pps:
            target = 0 if not GM.target_price_l2 else  GM.target_price_l2
            print('****] Average cost : {:.2f} [target {:.2f}], shares acquired : {} - pnl: {:.2f}'.format(pps, target, position, value))
