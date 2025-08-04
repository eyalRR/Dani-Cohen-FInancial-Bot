import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from scipy.signal import find_peaks
from datetime import datetime, timedelta

def fetch_data(ticker, period="1y"):
    """Fetch data for the given ticker."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    return yf.Ticker(ticker).history(start=start_date, end=end_date)

def find_significant_points(data, window=20, distance=10):
    """Find significant peaks and troughs in the data."""
    highs = data['High'].values
    lows = data['Low'].values
    
    peaks, _ = find_peaks(highs, distance=distance)
    troughs, _ = find_peaks(-lows, distance=distance)
    
    return peaks, troughs

def construct_channel(data, peaks, troughs):
    """Construct a channel from significant points."""
    x = np.arange(len(data))
    
    # Upper trendline
    upper_slope, upper_intercept = np.polyfit(peaks, data['High'].iloc[peaks], 1)
    
    # Lower trendline (parallel to upper)
    lower_intercept = np.min(data['Low'].iloc[troughs] - upper_slope * troughs)
    
    return (upper_slope, upper_intercept), (upper_slope, lower_intercept)

def identify_channels(data):
    """Identify long-term and short-term channels."""
    long_peaks, long_troughs = find_significant_points(data, window=30, distance=20)
    short_term_data = data.tail(66)
    short_peaks, short_troughs = find_significant_points(short_term_data, window=10, distance=5)
    
    long_term_channel = construct_channel(data, long_peaks, long_troughs)
    short_term_channel = construct_channel(short_term_data, short_peaks, short_troughs)
    
    return long_term_channel, short_term_channel

def plot_with_channels(data, ticker, long_term_channel, short_term_channel):
    """Create a candlestick chart with dynamic channels."""
    # Prepare channel plots
    x_long = np.arange(len(data))
    long_upper = long_term_channel[0][0] * x_long + long_term_channel[0][1]
    long_lower = long_term_channel[1][0] * x_long + long_term_channel[1][1]
    
    short_term_length = 66
    x_short = np.arange(short_term_length)
    short_upper = np.full(len(data), np.nan)
    short_lower = np.full(len(data), np.nan)
    short_upper[-short_term_length:] = short_term_channel[0][0] * x_short + short_term_channel[0][1]
    short_lower[-short_term_length:] = short_term_channel[1][0] * x_short + short_term_channel[1][1]
    
    # Create additional plots for channels
    apds = [
        mpf.make_addplot(long_upper, color='blue', linestyle='--', width=1),
        mpf.make_addplot(long_lower, color='blue', linestyle='--', width=1),
        mpf.make_addplot(short_upper, color='red', linestyle=':', width=1),
        mpf.make_addplot(short_lower, color='red', linestyle=':', width=1)
    ]
    
    # Plot candlestick chart with channels
    mpf.plot(data, type='candle', style='charles',
             title=f'{ticker} - Last Year Performance',
             ylabel='Price',
             addplot=apds,
             figsize=(12, 6),
             savefig=f'{ticker.replace("^", "")}_analysis.png')

def main():
    indices = {
        '^GSPC': 'S&P 500',
        '^NDX': 'NASDAQ-100'
    }
    
    for symbol, name in indices.items():
        data = fetch_data(symbol)
        long_term_channel, short_term_channel = identify_channels(data)
        plot_with_channels(data, name, long_term_channel, short_term_channel)
        print(f"Chart for {name} has been saved.")

if __name__ == "__main__":
    main()