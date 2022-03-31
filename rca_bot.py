'''
Created on  09 March 2022

@author: Totes
'''

import time
import math
import tweepy
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import nasdaqdatalink


#real API
#api_key = os.environ.get('binance_api') # OR add your API KEY here

#secretKey = os.environ.get('binance_secret') # OR add your API SecretKey here

auth = tweepy.OAuthHandler()
auth.set_access_token()
api = tweepy.API(auth)

lastPrice = 0

#Test API keys
api_key  = ""

secretKey =  ""

client = Client(api_key, secretKey)

# def getAllOrdrs(tradingPair):
#     #client.API_URL = 'https://testnet.binance.vision/api'
#     orders = client.get_all_orders(symbol=tradingPair)
#     return orders

# def getRecentTrades(tradingPair):
#     #client.API_URL = 'https://testnet.binance.vision/api'
#     trades = client.get_recent_trades(symbol=tradingPair)
#     return trades

# def placeSellOrder(price, tradingPair):
#     #client.API_URL = 'https://testnet.binance.vision/api'
#     order = client.create_order(symbol=tradingPair, side='SELL', type='MARKET', quantity=100)
#     return(order)


# def cancleOrders():
#     #client.API_URL = 'https://testnet.binance.vision/api'
#     print(client.get_open_orders())
#     for row in client.get_open_orders():
#         client.cancel_order(symbol=row["symbol"], orderId=row['orderId'])
#     print(client.get_open_orders())

def tweet(order):
    api.update_status(order)

def twitterDM():
  # gets the last 10 direct messages
  messages = api.list_direct_messages(count=10)
  # set up 3 lists for our variables, this will allow us to get the latest version message we have sent
  amount = []
  time = []
  fiat = []
  mode = []
  # Run a for loop through the message subset, reverse the messages so that you get the last message sent to the bot first
  for message in reversed(messages):
    sender_id = message.message_create["sender_id"]
    if sender_id == "YOURSENDERID": #you will need to find your own sender ID
      text = message.message_create["message_data"]["text"]
      if "$" in text: # This will find our buy amount
        amount.append(text.split("$")[1])
      elif "-" in text: # this will find our time frame
        time.append(text.split("-")[1])
      elif "EUR" in text: #  this will find our trading pair
        fiat.append(text)
      elif "dca" or "edca" or "sdca" or "va" or "fngdca" in text: # this finds the mode we want
          mode.append(text)


  # ensures we get the last message sent, meaning we will be able to change one variable at a time
  dcaAmount = amount[-1]
  timeFrame = time[-1]
  fiatPair = fiat[-1]
  dcaMode = mode[-1]
  return dcaAmount, timeFrame, fiatPair, dcaMode


#def checkDip():
    #(openPrice - lastPrice)/openPrice)



def getBalances():
    # Makes a request to Biances API for the account balance of what ever you are trading EUR in my case
    client.API_URL = 'https://testnet.binance.vision/api'
    balance = client.get_asset_balance(asset = 'USDT') # Change this for your fiat pair
    return balance

def getMarketPrice(tradingPair):
    # This will get the current price for the trading pair that you
    # give the bot at start.
    # Comment out the following line if not using test API
    client.API_URL = 'https://testnet.binance.vision/api'
    price = client.get_symbol_ticker(symbol=tradingPair)
    return price

def placeBuyOrder(quantity, tradingPair):
    # Comment out the following line if not using test API
    client.API_URL = 'https://testnet.binance.vision/api'
    try:
        order = client.create_order(symbol=tradingPair, side='BUY', type='MARKET', quantity=quantity)
        #order = client.create_test_order(symbol=tradingPair, side='BUY', type='MARKET', quantity=quantity)
        toTweet = "Bought " + order["symbol"] +  " at "+  order["fills"][0]['price']
        tweet(toTweet)
    except BinanceAPIException as e:
        tweet(e)
        print(e)
    except BinanceOrderException as e:
        tweet(e)
        print(e)
    return


def dcaBot(tradingPair, dcaAmount):
    # Comment out the following line if not using test API
    client.API_URL = 'https://testnet.binance.vision/api'
    try:
        currentPrice = float(getMarketPrice(tradingPair)['price'])
        lastPrice = currentPrice

        print("The current price is for the ", tradingPair, "pair is ",  currentPrice)

        getBalance = float(getBalances()['free'])

        print("The current balance for EUR is ",  getBalance)

        symbol_info = client.get_symbol_info(tradingPair)
        step_size = 0.0
        for f in symbol_info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                step_size = float(f['stepSize'])

        if getBalance > 10:
            quantity = dcaAmount / currentPrice * 0.995

            precision = int(round(-math.log(step_size, 10), 0))

            quantity = float(round(quantity, precision))

            print("buy amount ", quantity)
            placeBuyOrder(quantity, tradingPair)
            print("The new balance for EUR is ", getBalance)

        else:
            print("Inceficent funds, bot will try again in an hour")
            time.sleep(3600)
            dcaBot(tradingPair, dcaAmount)
    except BinanceAPIException as e:
        #tweet(e)
        print(e)

# this is your log function
def logFunc(x,a,b,c):
    return a*np.log(b+x) + c

def rwa_calculations(tradingPair, buy_frequency, typeofWeight, dcaamount):
    raw_data = pd.DataFrame(nasdaqdatalink.get("BCHAIN/MKPRU")).reset_index()
    raw_data['Date'] = pd.to_datetime(raw_data['Date'])  # Ensure that the date is in datetime or graphs might look funny
    raw_data = raw_data[raw_data["Value"] > 0]  # Drop all 0 values as they will fuck up the regression bands
    # getting your x and y data from the dataframe
    xdata = np.array([x + 1 for x in range(len(raw_data))])
    ydata = np.log(raw_data["Value"])
    # here we ar fitting the curve, you can use 2 data points however I wasn't able to get a graph that looked as good with just 2 points.
    popt, pcov = curve_fit(logFunc, xdata, ydata,p0=[10, 100, 90])  # p0 is justa guess, doesn't matter as far as I know
    # This is our fitted data, remember we will need to get the ex of it to graph it
    fittedYData = logFunc(xdata, popt[0], popt[1], popt[2])
    # Draw the rainbow bands
    for i in range(-2, 6):
        raw_data[f"fitted_data{i}"] = np.exp(fittedYData + i * .455)

    historical_data = raw_data

    fibs = {"bubble": 0, "sell": 0.1, "FOMO": 0.2, "Bubble?": 0.3, "Hodl": 0.5, "cheap": 0.8, "accumulate": 1.3,
            "Buy": 2.1, "fire_sale": 3.4}
    originalRCA = {"bubble": 0, "sell": 0.1, "FOMO": 0.2, "Bubble?": 0.35, "Hodl": 0.5, "cheap": 0.75, "accumulate": 1,"Buy": 2.5, "fire_sale": 3}
    # Choose what type of weightings you want to RCA with

    if typeofWeight == "fibs":
        weighted = fibs
    else:
        weighted = originalRCA

    price_dict = getMarketPrice(tradingPair)
    current_price = float(price_dict["price"])
    print(type(current_price))
    print(historical_data["fitted_data-1"].iloc[-1])

    if current_price < historical_data["fitted_data-2"].iloc[-1]:
        print("Bitcoin is below $", historical_data["fitted_data-1"].iloc[-1], " therefore our multiplier is ", weighted["fire_sale"])
        tweet("Bitcoin is below $", historical_data["fitted_data-1"].iloc[-1], " therefore our multiplier is ", weighted["fire_sale"])
        dcaBot(tradingPair, dcaamount*weighted["fire_sale"])

    elif current_price > historical_data["fitted_data-2"].iloc[-1] and current_price < historical_data["fitted_data-1"].iloc[-1]:
        print("Bitcoin is below $", historical_data["fitted_data-1"].iloc[-1], " therefore our multiplier is ", weighted["Buy"])
        tweet()
        dcaBot(tradingPair, dcaamount*weighted["Buy"])

    elif current_price > historical_data["fitted_data-1"].iloc[-1] and current_price < historical_data["fitted_data0"].iloc[-1]:
        print("Bitcoins price falls between $", historical_data["fitted_data-1"].iloc[-1], "and $", historical_data["fitted_data0"].iloc[-1], " therefore our multiplier is ", weighted["accumulate"])
        tweet()
        dcaBot(tradingPair, dcaamount * weighted["accumulate"])

    elif current_price > historical_data["fitted_data0"].iloc[-1] and current_price < historical_data["fitted_data1"].iloc[-1]:
        print("Bitcoins price falls between $", historical_data["fitted_data0"].iloc[-1], "and $", historical_data["fitted_data1"].iloc[-1], " therefore our multiplier is ", weighted["cheap"])
        tweet()
        dcaBot(tradingPair, dcaamount * weighted["cheap"])

    elif current_price > historical_data["fitted_data1"].iloc[-1] and current_price < historical_data["fitted_data2"].iloc[-1]:
        print("Bitcoins price falls between $", historical_data["fitted_data1"].iloc[-1], "and $", historical_data["fitted_data2"].iloc[-1], " therefore our multiplier is ", weighted["Hodl"])
        tweet()
        dcaBot(tradingPair, dcaamount * weighted["Hodl"])

    elif current_price > historical_data["fitted_data2"].iloc[-1] and current_price < historical_data["fitted_data3"].iloc[-1]:
        print("Bitcoins price falls between $", historical_data["fitted_data2"].iloc[-1], "and $", historical_data["fitted_data3"].iloc[-1], " therefore our multiplier is ", weighted["Bubble?"])
        tweet()
        dcaBot(tradingPair, dcaamount * weighted["Bubble"])

    elif current_price > historical_data["fitted_data3"].iloc[-1] and current_price < historical_data["fitted_data4"].iloc[-1]:
        print("Bitcoins price falls between $", historical_data["fitted_data3"].iloc[-1], "and $", historical_data["fitted_data4"].iloc[-1], " therefore our multiplier is ", weighted["FOMO"])
        tweet()
        dcaBot(tradingPair, dcaamount * weighted["FOMO"])

    elif current_price> historical_data["fitted_data4"].iloc[-1] and current_price <  historical_data["fitted_data5"].iloc[-1]:
        print("Bitcoins price falls between $", historical_data["fitted_data4"].iloc[-1], "and $", historical_data["fitted_data5"].iloc[-1], " therefore our multiplier is ", weighted["sell"])
        tweet()
        dcaBot(tradingPair, dcaamount * weighted["sell"])

    else:
        print("Don't buy bitcoin")


if __name__ == '__main__':
    while True:

       # dcaAmount, timeFrame, fiatPair, dcaMode = twitterDM()

        dcaTimeFrame = {
            "day": 86400,
            "week": 604800,
            "month": 2629746
        }

        timeFrame = "day"
        fiatPair = "BTCUSDT" # NB This currently only works with Bitocin
        typeofWeight = "fibs"
        dcaAmount = 100

        print("This bot will check the ballence of your account until money has been lodged, you must set up standing order yourself.")

        print("You have chosen to DCA ", dcaTimeFrame[timeFrame.lower()])
        print('Press Ctrl-C to stop.')
        # Change this to your fiat crypto pair
        buyFrequency = 1 # change the buy frequency here, value speficies number of days

        rwa_calculations(fiatPair, buyFrequency, typeofWeight, dcaAmount)

        time.sleep()
