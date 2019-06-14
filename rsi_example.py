import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from logbook import Logger
from math import floor, ceil

from catalyst import run_algorithm
from catalyst.api import order_target_percent, record, symbol
from catalyst.exchange.utils.stats_utils import extract_transactions

# Before you run, make sure you ingest the data..
# catalyst ingest-exchange -x bitfinex -i btc_usd -f minute

def initialize(context):
    # Run at the beginning, takes context
    # Context can be used to store variables needed throughout the algo
    context.asset       = symbol('btc_usdt')
    context.iterations  = 0
    context.base_price  = None

def handle_data(context, data):
    # Runs on every minute/day depending on timeframe specified at runtime, takes context and data
    # Context is our initial/global variables
    # Data is updated every bar

    # RSI requires 14 days of data, so we'll just iterate through and increment our counter until we have done this 14 times
    RSI_periods = 14

    context.iterations += 1
    if context.iterations < RSI_periods:
        # Dont go any further if there are less than 14 days
        return

    # Calling .history on the data object returns a number of data points
    # With frequency , we define how many TIME-FRAMES (in this case, minutes (as set in run_algorithm)), one bar consists of
    # Here this means we’ll be calculating the RSI for the 30 minute chart.
    RSI_data = data.history(context.asset,
            "price",
            bar_count = RSI_periods,
            frequency = "1d"
            )

    # compute RSI
    oversold = 30
    overbought = 70

    deltas  = RSI_data.diff()
    seed    = deltas[:RSI_periods + 1]
    up      = seed[seed >= 0].sum() / RSI_periods
    down    = -seed[seed < 0].sum() / RSI_periods

    RS = up / down
    RSI = 100 - (100 / (1 + RS))
    # End compute RSI

    # get current price
    # Calling .current on the data, gets the current price for a given asset
    # Can also get: “price”, “last_traded”, “open”, “high”, “low”, “close”, “volume”
    price = data.current(context.asset, "price")

    if context.base_price == None:
        # Store the price of the first candle so we can see how much things change against it later
        context.base_price = price

    # Calculate the percent change of the current price relative to the first candle price
    price_change = (price - context.base_price) / context.base_price

    # We use record to save off any data we want to log or graph later
    record(price = price,
            cash = context.portfolio.cash,
            price_change = price_change,
            RSI = RSI
            )

    # Check that we don't have any open orders. We'll only place an order if existing orders have filled/closed
    orders = context.blotter.open_orders
    if len(orders) > 0:
        return

    # We check that we can trade an asset (i.e. the exchange is accepting orders, not closed etc)
    if not data.can_trade(context.asset):
        print("Cannot trade right now")
        return

    # Get the amount of open positions for the asset in question
    pos_amount = context.portfolio.positions[context.asset].amount

    # Algo logic, if we have no open positions and the rsi is less than oversold, then we buy
    if pos_amount == 0 and RSI <= oversold:
        # Positive denotes a BUY
        # order_target_percent places an order for a percentage of our capital, ranging from 0.0 to 1.0. i.e. .5 would be 50% of our capital
        order_target_percent(context.asset, 1)

    elif pos_amount < 0 and RSI <= 40:
        order_target_percent(context.asset, 0)

    elif pos_amount == 0 and RSI >= overbought:
        # Negative denotes a SELL
        order_target_percent(context.asset, -1)

    elif pos_amount > 0 and RSI >= 60:
        order_target_percent(context.asset, 0)



def analyze(context, perf):
    # get the quote_currency that was passed as a parameter to the simulation


    exchange = list(context.exchanges.values())[0]
    quote_currency = exchange.quote_currency.upper()
#
    #  first chart: portfolio value
    ax1 = plt.subplot(411)
    perf.loc[:, ['portfolio_value']].plot(ax=ax1)
    ax1.legend_.remove()
    ax1.set_ylabel('Portfolio Value\n({})'.format(quote_currency))
    start, end = ax1.get_ylim()
    ax1.locator_params(numticks=12)

    ymin, ymax = ax1.get_ylim()
    ax1.set_yticks(np.round(np.linspace(ymin, ymax, 3), 2))

    #ax1.yaxis.set_ticks(np.arange(floor(start), ceil(end), 10))

    # second chart: asset price, buys & sells
    ax2 = plt.subplot(412, sharex=ax1)
    perf.loc[:, ['price']].plot(ax = ax2, label = 'Price')
    ax2.legend_.remove()
    ax2.set_ylabel('{asset}\n({quote})'.format(asset = context.asset.symbol, quote = quote_currency
        ))
    start, end = ax2.get_ylim()
    ax2.yaxis.set_ticks(np.arange(floor(start), ceil(end), 300))

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
        #  third chart: relative strength index
    ax3 = plt.subplot(413, sharex = ax1)
    perf.loc[:, ['RSI']].plot(ax = ax3)
    plt.axhline(y = 30, linestyle = 'dotted', color = 'grey')
    plt.axhline(y = 70, linestyle = 'dotted', color = 'grey')
    ax3.legend_.remove()
    ax3.set_ylabel('RSI')
    start, end = ax3.get_ylim()
    ax3.yaxis.set_ticks(np.arange(0, 100, 10))

    #  fourth chart: percentage return of the algorithm vs holding
    ax4 = plt.subplot(414, sharex=ax1)
    perf.loc[:, ['algorithm_period_return', 'price_change']].plot(ax=ax4)
    ax4.legend_.remove()
    ax4.set_ylabel('Percent Change')
    start, end = ax4.get_ylim()
    ax4.yaxis.set_ticks(np.arange(start, end, (end - start) / 5))

    plt.savefig("rsi_example.png")
    plt.show()


# Run the algorithm, passing in our functions
if __name__ == "__main__":
    run_algorithm(
        capital_base = 1000,
        data_frequency = "daily",
        initialize = initialize,
        handle_data = handle_data,
        analyze = analyze,
        exchange_name = "poloniex",
        algo_namespace = 'rsi_example',
        quote_currency = "usdt",
        live = False,
        start = pd.to_datetime("2017-1-1", utc = True),
        end = pd.to_datetime("2018-1-1", utc = True)
    )
