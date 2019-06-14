from catalyst.api import symbol, record, order
from catalyst import run_algorithm
import matplotlib.pyplot as plt
import numpy as np

import pandas as pd

def initialize(context):
    context.asset = symbol('btc_usdt')
    context.bought = False
    context.sold = False


def handle_data(context, data):
    price = data.current(context.asset, 'price')
    record(price=price, cash=context.portfolio.cash)

    if not context.bought and price > 5900:
        order(context.asset, 1)
        context.bought = True

    if context.bought and not context.sold and price > 6200:
        order(context.asset, -1)
        context.sold = True


def analyze(context, perf):
    exchange = list(context.exchanges.values())[0]
    quote_currency = exchange.quote_currency.upper()

    # 1st graph
    ax1 = plt.subplot(311)
    perf.loc[:, ['portfolio_value']].plot(ax=ax1)
    ax1.legend_.remove()
    ax1.set_ylabel("Portfolio Value\n{}".format(quote_currency))
    start, end = ax1.get_ylim()

    ax1.yaxis.set_ticks(np.arange(start, end, (end-start) / 5))


    # Second graph

    ax2 = plt.subplot(312, sharex=ax1)
    perf.loc[:, ['price']].plot(ax=ax2, label='Price')
    ax2.legend_.remove()
    ax2.set_ylabel("{asset}\n({currency})".format(
        asset=context.asset.symbol,
        currency=quote_currency
    ))

    start, end = ax2.get_ylim()
    ax2.yaxis.set_ticks(np.arange(start, end, (start-end) / 5))


    # Third graph (cash)
    ax3 = plt.subplot(313, sharex=ax1)
    perf.cash.plot(ax=ax3)
    ax3.set_ylabel('Cash\n{}'.format(quote_currency))

    plt.savefig("graph_example.png")
    plt.show()



if __name__ == '__main__':
    run_algorithm(capital_base=10000,
            data_frequency='minute',
            initialize=initialize,
            handle_data=handle_data,
            analyze=analyze,
            exchange_name='poloniex',
            quote_currency='usdt',
            live=False,
            start=pd.to_datetime('2017-10-28', utc=True),
            end=pd.to_datetime('2017-10-30', utc=True),
            )
