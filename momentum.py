from catalyst.api import symbol, record, order_target_percent, get_datetime, commission, slippage
from catalyst.exchange.utils.stats_utils import extract_transactions
from catalyst import run_algorithm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def initialize(context):
    context.asset = symbol('btc_usdt')
    context.i = 0
    context.holding = False

def handle_data(context, data):
    look_back_window = 20

    # Skip until we can calc absolute momentum
    context.i += 1
    if context.i < look_back_window:
        return

    btc_history = data.history(context.asset, 'price', bar_count=look_back_window, frequency='1D')

    percent_change = btc_history.pct_change(look_back_window - 1)[-1] * 100

    price = data.current(context.asset, 'price')

    # Trading logic
    # Buy if percentage change > 0

    if percent_change > 0:
        if not context.holding:
            order_target_percent(context.asset, 1)
            context.holding = True

    # Sell otherwise
    else:
        if context.holding:
            order_target_percent(context.asset, 0)
            context.holding = False

    record(price=price,
           cash=context.portfolio.cash,
           percent_change=percent_change)


def analyze(context, perf):
    exchange = list(context.exchanges.values())[0]
    quote_currency = exchange.quote_currency.upper()

    #  1st graph
    ax1 = plt.subplot(411)
    perf.loc[:, ['portfolio_value']].plot(ax=ax1)
    ax1.legend_.remove()
    ax1.set_title("Portfolio Value ({})".format(quote_currency), rotation=0)
    start, end = ax1.get_ylim()

    ax1.yaxis.set_ticks(np.arange(start, end, (end-start) / 5))

    # Second graph
    ax2 = plt.subplot(412, sharex=ax1)
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
    #  ax3 = plt.subplot(513, sharex=ax1)
    #  perf.cash.plot(ax=ax3)
    #  ax3.set_title('Cash ({})'.format(quote_currency), rotation=0)

    ax4 = plt.subplot(413, sharex=ax1)
    perf.max_drawdown.plot(ax=ax4, kind='area', color='coral', alpha=0.7)
    ax4.set_title('Max drawdown', rotation=0)
    ax4.set_ylim(-1.0, 0)

    ax5 = plt.subplot(414, sharex=ax1)
    perf.percent_change.plot(ax=ax5)
    ax5.set_title('Percent Change', rotation=0)



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



    plt.savefig("momentum.png")

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
