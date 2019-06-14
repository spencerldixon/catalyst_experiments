from catalyst.api import symbol, record, order_target_percent, get_datetime, commission, slippage
from catalyst.exchange.utils.stats_utils import extract_transactions
from catalyst import run_algorithm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import talib as ta

from catalyst.exchange.utils.stats_utils import get_pretty_stats

def initialize(context):
    context.asset = symbol('btc_usdt')
    context.lookback_period = 40
    context.bought = False

    #  context.set_commission(maker=0.2, taker=0.2)

def handle_data(context, data):
    price = data.current(context.asset, 'price')

    prices = data.history(
            context.asset,
            bar_count=context.lookback_period,
            fields=['price', 'open', 'high', 'low', 'close'],
            frequency='1d'
            )


    macd, macd_signal, macd_hist = ta.MACD(
                                    prices['close'].values,
                                    fastperiod=12,
                                    slowperiod=26,
                                    signalperiod=9
                                    )

    macd_current        = macd[-1]
    macd_signal_current = macd_signal[-1]

    macd_prev           = macd[-2]
    macd_signal_prev    = macd_signal[-2]

    # Record MACD
    record(
        price=price,
        cash=context.portfolio.cash,
        macd=macd[-1],
        macd_signal=macd_signal[-1],
        macd_hist=macd_hist[-1]
    )


    # Check we dont have any open orders
    #orders = context.blotter.open_orders
    #  if len(orders) > 0:
        # Manage existing trades
        #  return

    # Exit if we cannot trade
    if not data.can_trade(context.asset):
        return

    # Buy / sell signals
    if macd_prev < macd_signal_prev and macd_current > macd_signal_current:
        print("Buy opportunity")
        # Buy
        if not context.bought:
            print("BUYING")
            order_target_percent(context.asset, 1)
            context.bought = True
    elif macd_prev > macd_signal_prev and macd_current < macd_signal_current:
        # Sell
        print("Sell opportunity")
        # Buy
        if context.bought:
            print("EXITING POSITION")
            order_target_percent(context.asset, 0)
            context.bought = False



    #  if not context.bought:
        #  order_target_percent(context.asset, 1)
        #  context.bought = True
#
    #  if get_datetime().date() == context.end_date:
        #  order_target_percent(context.asset, -1)

def analyze(context, perf):
    exchange = list(context.exchanges.values())[0]
    quote_currency = exchange.quote_currency.upper()

    #  print(perf)

    #  1st graph
    ax1 = plt.subplot(511)
    perf.loc[:, ['portfolio_value']].plot(ax=ax1)
    ax1.legend_.remove()
    ax1.set_title("Portfolio Value ({})".format(quote_currency), rotation=0)
    start, end = ax1.get_ylim()

    ax1.yaxis.set_ticks(np.arange(start, end, (end-start) / 5))

    # Second graph
    ax2 = plt.subplot(512, sharex=ax1)
    perf.loc[:, ['price']].plot(ax = ax2, label = 'Price')
    ax2.legend_.remove()
    ax2.set_title('Price ({asset} / {quote})'.format(asset = context.asset.symbol, quote = quote_currency
        ), rotation=0)
    start, end = ax2.get_ylim()
    #  ax2.yaxis.set_ticks(np.arange(floor(start), ceil(end), 300))
    ax2.yaxis.set_ticks(np.arange(start, end, (start-end) / 5))

    transaction_df = extract_transactions(perf)
    if not transaction_df.empty:
        buy_df = transaction_df[transaction_df['amount'] > 0]
        sell_df = transaction_df[transaction_df['amount'] < 0]
        ax2.scatter(
                buy_df.index.to_pydatetime(),
                perf.loc[buy_df.index, 'price'],
                marker = '^',
                s = 50,
                c = 'green',
                label = ''
                )
        ax2.scatter(
                sell_df.index.to_pydatetime(),
                perf.loc[sell_df.index, 'price'],
                marker = 'v',
                s = 50,
                c = 'red',
                label = ''
                )


    # Third graph (cash)
    ax3 = plt.subplot(513, sharex=ax1)
    perf.cash.plot(ax=ax3)
    ax3.set_title('Cash ({})'.format(quote_currency), rotation=0)

    ax4 = plt.subplot(514, sharex=ax1)
    perf.max_drawdown.plot(ax=ax4, kind='area', color='coral', alpha=0.7)
    ax4.set_title('Max drawdown', rotation=0)
    ax4.set_ylim(-1.0, 0)

    ax5 = plt.subplot(515, sharex = ax1)
    perf.macd.plot(ax = ax5)
    perf.macd_signal.plot(ax = ax5)
    #  plt.axhline(y = 30, linestyle = 'dotted', color = 'grey')
    #  plt.axhline(y = 70, linestyle = 'dotted', color = 'grey')
    #  ax5.legend_.remove()
    ax5.set_ylabel('MACD')
    #  start, end = ax3.get_ylim()
    #  ax5.yaxis.set_ticks(np.arange(0, 100, 10))



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



    plt.savefig("macd_example.png")

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





if __name__ == '__main__':
    run_algorithm(capital_base=1000,
            data_frequency='daily',
            initialize=initialize,
            handle_data=handle_data,
            analyze=analyze,
            exchange_name='poloniex',
            quote_currency='usdt',
            live=False,
            start=pd.to_datetime('2017-1-1', utc=True),
            end=pd.to_datetime('2018-1-1', utc=True),
            )
