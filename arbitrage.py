from catalyst.utils.run_algo import run_algorithm

from catalyst.api import symbol, record, order, get_datetime, commission, slippage
from catalyst.exchange.utils.stats_utils import extract_transactions
#  from catalyst #import run_algorithm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from catalyst.exchange.utils.stats_utils import get_pretty_stats

def initialize(context):
    context.asset = symbol('btc_usdt')
    context.binance     = context.exchanges['binance']
    context.poloniex    = context.exchanges['poloniex']

    context.binance_trading_pair    = symbol('eth_btc', context.binance.name)
    context.poloniex_trading_pair   = symbol('eth_btc', context.poloniex.name)
    #  context.set_commission(maker=0.2, taker=0.2)

def handle_data(context, data):
    poloniex_price   = data.current(context.poloniex_trading_pair, 'price')
    binance_price    = data.current(context.binance_trading_pair, 'price')
    slippage = 0.03

    sell_p, buy_p = get_adjusted_prices(poloniex_price, slippage)
    sell_b, buy_b = get_adjusted_prices(binance_price, slippage)

    #  print('Data: {}'.format(data.current_dt))
    #  print('Poloniex: {}'.format(poloniex_price))
    #  print('Binance: {}'.format(binance_price))

    if is_profitable_after_fees(sell_p, buy_b, context.poloniex, context.binance):
        # Buy on binance, sell on poloniex
        order(asset=context.binance_trading_pair,
                amount=1,
                limit_price=binance_price)

        order(asset=context.poloniex_trading_pair,
                amount=-1,
                limit_price=poloniex_price)
    elif is_profitable_after_fees(sell_b, buy_p, context.binance, context.poloniex):
        # buy poloniex, sell binance
        order(asset=context.binance_trading_pair,
                amount=-1,
                limit_price=binance_price)

        order(asset=context.poloniex_trading_pair,
                amount=1,
                limit_price=poloniex_price)

    record(
        poloniex_price=poloniex_price,
        binance_price=binance_price,
        cash=context.portfolio.cash,
    )

def is_profitable_after_fees(sell_price, buy_price, sell_market, buy_market):
    sell_fee = get_fee(sell_market, sell_price)
    buy_fee = get_fee(buy_market, buy_price)
    expected_profit = sell_price - buy_price - sell_fee - buy_fee

    if expected_profit > 0:
        print("Sell {} at {}, buy {} at {}".format(sell_market.name, sell_price, buy_market.name, buy_price))
        print("Total fees: {}".format(buy_fee + sell_fee))
        print("Expected profit: {}".format(expected_profit))
        return True
    return False

def get_fee(market, price):
    return market.api.fees['trading']['taker'] * price

def get_adjusted_prices(price, slippage):
    adj_sell_price = price * (1 - slippage)
    adj_buy_price = price * (1 + slippage)
    return adj_sell_price, adj_buy_price

def analyze(context, perf):
    exchange = list(context.exchanges.values())[0]
    quote_currency = exchange.quote_currency.upper()

    #  print(perf)

    #  1st graph
    ax1 = plt.subplot(411)
    perf.loc[:, ['portfolio_value']].plot(ax=ax1)
    ax1.legend_.remove()
    ax1.set_title("Portfolio Value ({})".format(quote_currency), rotation=0)
    start, end = ax1.get_ylim()

    ax1.yaxis.set_ticks(np.arange(start, end, (end-start) / 5))

    # Second graph
    ax2 = plt.subplot(412, sharex=ax1)
    perf.loc[:, ['poloniex_price']].plot(ax = ax2, label = 'Price')
    ax2.legend_.remove()
    ax2.set_title('Price ({asset} / {quote})'.format(asset = context.asset.symbol, quote = quote_currency
        ), rotation=0)
    start, end = ax2.get_ylim()
    #  ax2.yaxis.set_ticks(np.arange(floor(start), ceil(end), 300))
    ax2.yaxis.set_ticks(np.arange(start, end, (start-end) / 5))
    ax2.set_title('Poloniex Price', rotation=0)

    transaction_df = extract_transactions(perf)
    if not transaction_df.empty:
        buy_df = transaction_df[transaction_df['amount'] > 0]
        sell_df = transaction_df[transaction_df['amount'] < 0]
        ax2.scatter(
                buy_df.index.to_pydatetime(),
                perf.loc[buy_df.index, 'poloniex_price'],
                marker = '^',
                s = 50,
                c = 'green',
                label = ''
                )
        ax2.scatter(
                sell_df.index.to_pydatetime(),
                perf.loc[sell_df.index, 'poloniex_price'],
                marker = 'v',
                s = 50,
                c = 'red',
                label = ''
                )

    ax3 = plt.subplot(413, sharex=ax1)
    perf.loc[:, ['binance_price']].plot(ax = ax3, label = 'Price')
    ax3.legend_.remove()
    ax3.set_title('Price ({asset} / {quote})'.format(asset = context.asset.symbol, quote = quote_currency
        ), rotation=0)
    start, end = ax3.get_ylim()
    #  ax2.yaxis.set_ticks(np.arange(floor(start), ceil(end), 300))
    ax3.yaxis.set_ticks(np.arange(start, end, (start-end) / 5))
    ax3.set_title('Binance Price', rotation=0)

    transaction_df = extract_transactions(perf)
    if not transaction_df.empty:
        buy_df = transaction_df[transaction_df['amount'] > 0]
        sell_df = transaction_df[transaction_df['amount'] < 0]
        ax3.scatter(
                buy_df.index.to_pydatetime(),
                perf.loc[buy_df.index, 'binance_price'],
                marker = '^',
                s = 50,
                c = 'green',
                label = ''
                )
        ax3.scatter(
                sell_df.index.to_pydatetime(),
                perf.loc[sell_df.index, 'binance_price'],
                marker = 'v',
                s = 50,
                c = 'red',
                label = ''
                )

    # Third graph (cash)
    #  ax3 = plt.subplot(513, sharex=ax1)
    #  perf.cash.plot(ax=ax3)
    #  ax3.set_title('Cash ({})'.format(quote_currency), rotation=0)

    ax4 = plt.subplot(414, sharex=ax1)
    perf.max_drawdown.plot(ax=ax4, kind='area', color='coral', alpha=0.7)
    ax4.set_title('Max drawdown', rotation=0)
    ax4.set_ylim(-1.0, 0)




    #  perf[[
        #  'treasury',
        #  'algorithm',
        #  'benchmark',
        #  ]] = perf[[
        #  'treasury_period_return',
        #  'algorithm_period_return',
        #  'benchmark_period_return',
        #  ]]
#
    #  ax5 = plt.subplot(515, sharex=ax1)
    #  perf[[
        #  'treasury',
        #  'algorithm',
        #  'benchmark',
        #  ]].plot(ax=ax5)
    #  ax5.set_ylabel('Percent Change')



    plt.savefig("arbitrage.png")

    #  fig = plt.figure()
    #  ax1 = plt.subplot(311)
    #  perf.portfolio_value.plot(ax=ax1)
#
    #  ax2 = plt.subplot(312, sharex=ax1)
    #  perf.benchmark_period_return.plot(ax=ax2)

    #  print(perf.columns)

    #  ax3 = plt.subplot(313, sharex=ax1)
    #  perf.alpha.plot(ax=ax3)

    plt.show()

    print("Starting Cash: $", perf.starting_cash.iloc[0])
    print("Ending portfolio value: $", perf.portfolio_value.iloc[-1])
    print("Cash: $", perf.cash.iloc[-1])
    print("Ending cash: $", perf.ending_cash.iloc[-1])
    print("Max Drawdown: ", perf.max_drawdown.min() * 100, "%")
    print("Algorithm Period Return: ", perf.algorithm_period_return.iloc[-1] * 100, "%")
    print("Pnl $", perf.pnl.sum())

    print(get_pretty_stats(perf))





#  if __name__ == '__main__':
run_algorithm(capital_base=1000,
        data_frequency='minute',
        initialize=initialize,
        handle_data=handle_data,
        analyze=analyze,
        exchange_name='poloniex, binance',
        quote_currency='usdt',
        live=False,
        start=pd.to_datetime('2017-1-1', utc=True),
        end=pd.to_datetime('2018-1-1', utc=True),
        )
