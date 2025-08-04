import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from scipy.signal import find_peaks

def fetch_data(ticker, period="1y"):
    """Fetch data for the given ticker."""
    return yf.Ticker(ticker).history(period=period)

def find_significant_points(data, window=20, distance=10):
    """Find significant peaks and troughs in the data."""
    highs = data['High'].values
    lows = data['Low'].values
    
    peaks, _ = find_peaks(highs, distance=distance)
    troughs, _ = find_peaks(-lows, distance=distance)
    
    return peaks, troughs

def optimize_channel(x, y, slope, intercept):
    """Optimize the channel line to minimize distance to points."""
    distances = y - (slope * x + intercept)
    return slope, intercept + np.percentile(distances, 90)

def construct_channel(data, peaks, troughs):
    """Construct a channel from significant points."""
    x = np.arange(len(data))
    
    # Upper trendline
    upper_slope, upper_intercept = np.polyfit(peaks, data['High'].iloc[peaks], 1)
    upper_slope, upper_intercept = optimize_channel(peaks, data['High'].iloc[peaks], upper_slope, upper_intercept)
    
    # Lower trendline (parallel to upper)
    lower_intercept = np.min(data['Low'].iloc[troughs] - upper_slope * troughs)
    
    return (upper_slope, upper_intercept), (upper_slope, lower_intercept)

def identify_channels(data):
    """Identify long-term and short-term channels."""
    long_peaks, long_troughs = find_significant_points(data, window=30, distance=20)
    short_peaks, short_troughs = find_significant_points(data.tail(66), window=10, distance=5)
    
    long_term_channel = construct_channel(data, long_peaks, long_troughs)
    short_term_channel = construct_channel(data.tail(66), short_peaks, short_troughs)
    
    return long_term_channel, short_term_channel

def plot_with_channels(data, ticker, long_term_channel, short_term_channel):
    """Create a candlestick chart with dynamic channels."""
    additional_plots = []
    
    # Long-term channel
    x_long = np.arange(len(data))
    long_upper = long_term_channel[0][0] * x_long + long_term_channel[0][1]
    long_lower = long_term_channel[1][0] * x_long + long_term_channel[1][1]
    additional_plots.append(mpf.make_addplot(long_upper, color='blue', linestyle='--', width=1))
    additional_plots.append(mpf.make_addplot(long_lower, color='blue', linestyle='--', width=1))
    
    # Short-term channel
    short_term_length = 66
    x_short = np.arange(len(data) - short_term_length, len(data))
    short_upper = np.full(len(data), np.nan)
    short_lower = np.full(len(data), np.nan)
    short_upper[-short_term_length:] = short_term_channel[0][0] * np.arange(short_term_length) + short_term_channel[0][1]
    short_lower[-short_term_length:] = short_term_channel[1][0] * np.arange(short_term_length) + short_term_channel[1][1]
    additional_plots.append(mpf.make_addplot(short_upper, color='red', linestyle=':', width=1))
    additional_plots.append(mpf.make_addplot(short_lower, color='red', linestyle=':', width=1))
    
    # Plot candlestick chart with channels
    mpf.plot(data, type='candle', style='yahoo', title=f'{ticker} - 1 Year Chart with Channels',
             addplot=additional_plots, figsize=(12, 6),
             ylabel='Price')
    
    plt.legend(['Long-term Channel', 'Short-term Channel'])
    plt.show()

def main():
    indices = {
        '^GSPC': 'S&P 500',
        '^NDX': 'NASDAQ-100'
    }
    
    for symbol, name in indices.items():
        data = fetch_data(symbol)
        long_term_channel, short_term_channel = identify_channels(data)
        plot_with_channels(data, name, long_term_channel, short_term_channel)

if __name__ == "__main__":
    main()