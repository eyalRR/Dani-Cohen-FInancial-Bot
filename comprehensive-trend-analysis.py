import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import matplotlib.dates as mdates

class TrendChannelAnalyzer:
    def __init__(self):
        self.data = None
        self.long_channel = None
        self.intermediate_channels = []

    def generate_specific_data(self, n_days=300):
        """Generate data matching the specific pattern shown in the image"""
        dates = pd.date_range(start='2023-01-01', periods=n_days)
        
        # Create the specific price pattern
        x = np.linspace(0, n_days-1, n_days)
        
        # Base trend
        base_trend = 102 + 0.05 * x
        
        # Add specific movements to match the pattern
        prices = []
        for i in x:
            if i < 30:
                # Initial upward movement
                price = base_trend[int(i)] + 2 * np.sin(i/15)
            elif i < 60:
                # First plateau with slight increase
                price = base_trend[int(i)] + 3 + np.sin(i/10)
            elif i < 90:
                # Small decline
                price = base_trend[int(i)] + 2 - np.sin(i/20)
            elif i < 150:
                # Gradual increase
                price = base_trend[int(i)] + 3 + np.sin(i/25)
            elif i < 210:
                # Higher plateau with fluctuations
                price = base_trend[int(i)] + 5 + np.sin(i/15)
            elif i < 270:
                # Slight decline and consolidation
                price = base_trend[int(i)] + 4 + np.sin(i/20)
            else:
                # Final upward movement
                price = base_trend[int(i)] + 6 + np.sin(i/15)
                
            # Add small noise
            price += np.random.normal(0, 0.1)
            prices.append(price)

        self.data = pd.DataFrame({
            'date': dates,
            'price': prices
        }).set_index('date')

    def calculate_long_term_channel(self):
        """Calculate the long-term trend channel"""
        x = np.arange(len(self.data))
        y = self.data['price'].values
        
        # Calculate linear regression for long-term trend
        slope, intercept = np.polyfit(x, y, 1)
        
        # Calculate channel width based on price deviation
        trend_line = slope * x + intercept
        deviations = y - trend_line
        channel_width = np.std(deviations) * 1.5
        
        self.long_channel = {
            'slope': slope,
            'intercept': intercept,
            'width': channel_width
        }

    def calculate_intermediate_channels(self, window_size=60):
        """Calculate intermediate trend channels"""
        self.intermediate_channels = []
        
        for i in range(0, len(self.data), window_size):
            if i + window_size > len(self.data):
                break
                
            segment = self.data.iloc[i:i+window_size]
            x = np.arange(len(segment))
            y = segment['price'].values
            
            # Calculate linear regression for segment
            slope, intercept = np.polyfit(x, y, 1)
            
            # Calculate channel width for segment
            trend_line = slope * x + intercept
            deviations = y - trend_line
            channel_width = np.std(deviations) * 1.2
            
            self.intermediate_channels.append({
                'start_idx': i,
                'end_idx': i + window_size,
                'slope': slope,
                'intercept': intercept,
                'width': channel_width
            })

    def plot_channels(self):
        """Create visualization matching the reference image"""
        plt.figure(figsize=(15, 8))
        
        # Plot price line
        plt.plot(self.data.index, self.data['price'], 
                label='Price', color='#2563eb', linewidth=2)
        
        # Plot long-term channel
        x = np.arange(len(self.data))
        trend_line = self.long_channel['slope'] * x + self.long_channel['intercept']
        
        plt.plot(self.data.index, 
                trend_line + self.long_channel['width'], 
                '--', color='#ef4444', label='Long-term Channel', 
                alpha=0.8)
        plt.plot(self.data.index, 
                trend_line - self.long_channel['width'], 
                '--', color='#ef4444', 
                alpha=0.8)
        
        # Plot intermediate channels
        for channel in self.intermediate_channels:
            segment_dates = self.data.index[channel['start_idx']:channel['end_idx']]
            x_segment = np.arange(len(segment_dates))
            trend_line = channel['slope'] * x_segment + channel['intercept']
            
            plt.plot(segment_dates, 
                    trend_line + channel['width'], 
                    '--', color='#3b82f6', 
                    alpha=0.5)
            plt.plot(segment_dates, 
                    trend_line - channel['width'], 
                    '--', color='#3b82f6', 
                    alpha=0.5)
        
        # Customize plot to match reference
        plt.grid(True, alpha=0.3)
        plt.title('Corrected Trend Channels', pad=20)
        
        # Set y-axis limits and ticks
        plt.ylim(95, 130)
        plt.yticks(np.arange(95, 135, 5))
        
        # Format x-axis
        days = mdates.DayLocator(interval=30)
        plt.gca().xaxis.set_major_locator(days)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%dd'))
        
        # Add legend
        plt.legend(['Price', 'Long-term Channel', 'Intermediate Channels'])
        
        plt.tight_layout()
        return plt

def main():
    # Create analyzer and generate data
    analyzer = TrendChannelAnalyzer()
    analyzer.generate_specific_data()
    
    # Calculate channels
    analyzer.calculate_long_term_channel()
    analyzer.calculate_intermediate_channels()
    
    # Create and show plot
    plt = analyzer.plot_channels()
    plt.show()

if __name__ == "__main__":
    main()