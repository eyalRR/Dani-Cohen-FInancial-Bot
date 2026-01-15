# market_analysis.py
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np
from scipy.signal import find_peaks
import mplfinance as mpf
import logging

logger = logging.getLogger(__name__)

class MarketAnalysis:
    def fetch_data(self, ticker, period="1y"):
        """Fetch data for the given ticker."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            return yf.Ticker(ticker).history(start=start_date, end=end_date)
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return None

    def find_significant_points(self, data, window=20, distance=10):
        """Find significant peaks and troughs in the data."""
        try:
            highs = data['High'].values
            lows = data['Low'].values
            
            peaks, _ = find_peaks(highs, distance=distance)
            troughs, _ = find_peaks(-lows, distance=distance)
            
            return peaks, troughs
        except Exception as e:
            logger.error(f"Error finding significant points: {e}")
            return None, None

    def construct_channel(self, data, peaks, troughs):
        """Construct a channel from significant points."""
        try:
            x = np.arange(len(data))
            
            upper_slope, upper_intercept = np.polyfit(peaks, data['High'].iloc[peaks], 1)
            lower_intercept = np.min(data['Low'].iloc[troughs] - upper_slope * troughs)
            
            return (upper_slope, upper_intercept), (upper_slope, lower_intercept)
        except Exception as e:
            logger.error(f"Error constructing channel: {e}")
            return None

    @staticmethod
    def validate_trend(data, start_idx, end_idx, is_recent=False):
        """
        Validate trend with strict criteria
        """
        segment = data.iloc[start_idx:end_idx]
        x = np.arange(len(segment))
        y = segment['Close'].values
        
        # Linear regression calculations
        n = len(x)
        if n < 2:
            return {'isTrend': False}
        
        slope, intercept = np.polyfit(x, y, 1)
        
        # Calculate R-squared
        trend_line = slope * x + intercept
        residuals = y - trend_line
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r_squared = 1 - (ss_res / ss_tot)
        
        # Calculate trend significance
        price_range = abs(y[-1] - y[0])
        avg_price = np.mean(y)
        movement_significance = price_range / avg_price
        
        # Adjust thresholds based on period
        if is_recent:
            r_squared_threshold = 0.3
            slope_threshold = 0.008
            movement_threshold = 0.03
        else:
            r_squared_threshold = 0.4
            slope_threshold = 0.015
            movement_threshold = 0.05
        
        is_trend = (
            r_squared > r_squared_threshold and
            abs(slope) > slope_threshold and
            movement_significance > movement_threshold
        )
        
        return {
            'isTrend': is_trend,
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_squared,
            'movement_significance': movement_significance
        }

    @staticmethod
    def calculate_channel(data, start_idx, end_idx, is_long_term=False):
        """
        Calculate channel with adjusted parameters for recent periods
        """
        validation = MarketAnalysis.validate_trend(data, start_idx, end_idx, is_recent=not is_long_term)
        
        if not validation['isTrend']:
            return None
            
        segment = data.iloc[start_idx:end_idx]
        x = np.arange(len(segment))
        
        # Calculate channel boundaries
        highs = segment['High'].values
        lows = segment['Low'].values
        
        slope = validation['slope']
        trend_line = slope * x + validation['intercept']
        
        # More adaptive width calculation
        high_residuals = highs - trend_line
        low_residuals = lows - trend_line
        
        # Adjust width calculation based on period
        if is_long_term:
            width_multiplier = 1.5
        else:
            # More dynamic width for shorter periods
            volatility = np.std(segment['High'] - segment['Low'])
            avg_price = np.mean(segment['Close'])
            relative_volatility = volatility / avg_price
            width_multiplier = max(1.0, min(1.5, relative_volatility * 20))
        
        channel_width = (np.std(high_residuals) + np.std(low_residuals)) * width_multiplier
        
        upper_intercept = validation['intercept'] + channel_width/2
        lower_intercept = validation['intercept'] - channel_width/2
        
        return (
            (slope, upper_intercept),
            (slope, lower_intercept),
            (segment.index[0], segment.index[-1])
        )

    @staticmethod
    def is_similar_channel(channel1, channel2):
        """
        Check if two channels are too similar to be considered distinct
        """
        if channel1 is None or channel2 is None:
            return False
            
        # Compare slopes and intercepts
        slope1, intercept1 = channel1[0]
        slope2, intercept2 = channel2[0]
        
        # Calculate similarity thresholds
        slope_threshold = 0.1
        intercept_threshold = (channel1[1][1] - channel1[0][1]) * 0.3
        
        return (abs(slope1 - slope2) < slope_threshold and 
                abs(intercept1 - intercept2) < intercept_threshold)

    @staticmethod
    def has_significant_overlap(channel1, channel2, max_overlap=0.3):
        """
        Check if two channels have significant overlap
        Returns True if overlap is greater than max_overlap
        """
        if channel1 is None or channel2 is None:
            return False
        
        start1, end1 = channel1[2]
        start2, end2 = channel2[2]
        
        # Convert to timestamps for proper comparison
        start1_ts = start1.timestamp()
        end1_ts = end1.timestamp()
        start2_ts = start2.timestamp()
        end2_ts = end2.timestamp()
        
        # Calculate overlap
        overlap_start = max(start1_ts, start2_ts)
        overlap_end = min(end1_ts, end2_ts)
        
        if overlap_end <= overlap_start:
            return False
        
        # Calculate overlap ratio relative to the shorter channel
        overlap_length = overlap_end - overlap_start
        channel1_length = end1_ts - start1_ts
        channel2_length = end2_ts - start2_ts
        shorter_length = min(channel1_length, channel2_length)
        
        overlap_ratio = overlap_length / shorter_length
        
        return overlap_ratio > max_overlap

    @staticmethod
    def calculate_channel_quality(data, start_idx, end_idx, channel):
        """
        Calculate quality score for a channel with improved metrics
        """
        segment = data.iloc[start_idx:end_idx]
        (slope, upper_intercept), (_, lower_intercept), _ = channel
        
        x = np.arange(len(segment))
        upper_line = slope * x + upper_intercept
        lower_line = slope * x + lower_intercept
        
        highs = segment['High'].values
        lows = segment['Low'].values
        closes = segment['Close'].values
        
        # Calculate various quality metrics
        # 1. Channel touches
        tolerance = np.mean(upper_line - lower_line) * 0.05
        upper_touches = np.sum(np.abs(highs - upper_line) < tolerance)
        lower_touches = np.sum(np.abs(lows - lower_line) < tolerance)
        
        # 2. Price containment
        contains_price = np.sum((lows > lower_line) & (highs < upper_line))
        
        # 3. Trend strength
        price_range = np.max(highs) - np.min(lows)
        trend_movement = abs(closes[-1] - closes[0])
        
        # 4. Calculate scores
        touch_score = (upper_touches + lower_touches) / len(segment)
        containment_score = contains_price / len(segment)
        trend_score = trend_movement / price_range
        
        # Combine scores with weights
        final_score = (0.3 * touch_score + 
                    0.4 * containment_score + 
                    0.3 * trend_score)
        
        return final_score

    def identify_channels(self, data):
        """
        Identify channels with strict overlap control
        """
        # Identify long-term channel first
        long_term_validation = self.validate_trend(data, 0, len(data))
        long_term_channel = None
        if long_term_validation['isTrend']:
            long_term_channel = self.calculate_channel(data, 0, len(data), is_long_term=True)
        
        # Parameters for intermediate channels
        window_size = 40  # Base window size
        data_length = len(data)
        potential_channels = []
        
        # First, collect all potential channels
        for i in range(0, data_length - window_size, 20):
            window_validation = self.validate_trend(data, i, i + window_size, 
                                            is_recent=(i > data_length * 2/3))
            
            if window_validation['isTrend']:
                channel = self.calculate_channel(data, i, i + window_size, is_long_term=False)
                if channel is not None:
                    score = self.calculate_channel_quality(data, i, i + window_size, channel)
                    potential_channels.append((channel, score, i))
        
        # Sort channels by quality score
        potential_channels.sort(key=lambda x: x[1], reverse=True)
        
        # Select non-overlapping channels
        selected_channels = []
        for channel, score, start_idx in potential_channels:
            if score > 0.3:  # Minimum quality threshold
                if not any(self.has_significant_overlap(channel, existing) 
                        for existing in selected_channels):
                    selected_channels.append(channel)
        
        return long_term_channel, selected_channels

    @staticmethod
    def plot_with_channels(data, ticker, long_term_channel, intermediate_channels):
        """
        Create visualization with long-term and multiple intermediate channels
        """
        apds = []
        
        # Plot long-term channel
        if long_term_channel is not None:
            (slope, intercept), (_, lower_intercept), (start_date, end_date) = long_term_channel
            valid_mask = (data.index >= start_date) & (data.index <= end_date)
            
            long_upper = np.full(len(data), np.nan)
            long_lower = np.full(len(data), np.nan)
            
            start_idx = data.index.get_loc(start_date)
            end_idx = data.index.get_loc(end_date)
            
            x = np.arange(end_idx - start_idx + 1)
            upper_line = slope * x + intercept
            lower_line = slope * x + lower_intercept
            
            long_upper[start_idx:end_idx + 1] = upper_line
            long_lower[start_idx:end_idx + 1] = lower_line
            
            apds.extend([
                mpf.make_addplot(long_upper, color='royalblue', linestyle='--', width=2.5),
                mpf.make_addplot(long_lower, color='royalblue', linestyle='--', width=2.5)
            ])
        
        # Plot intermediate channels
        for channel in intermediate_channels:
            (slope, intercept), (_, lower_intercept), (start_date, end_date) = channel
            
            int_upper = np.full(len(data), np.nan)
            int_lower = np.full(len(data), np.nan)
            
            start_idx = data.index.get_loc(start_date)
            end_idx = data.index.get_loc(end_date)
            
            x = np.arange(end_idx - start_idx + 1)
            upper_line = slope * x + intercept
            lower_line = slope * x + lower_intercept
            
            int_upper[start_idx:end_idx + 1] = upper_line
            int_lower[start_idx:end_idx + 1] = lower_line
            
            apds.extend([
                mpf.make_addplot(int_upper, color='red', linestyle='-.', width=2.8),
                mpf.make_addplot(int_lower, color='red', linestyle='-.', width=2.8)
            ])
        
        # Setup plot style with enhanced settings
        mc = mpf.make_marketcolors(up='forestgreen', down='crimson',
                                edge='inherit', wick='inherit', volume='in')
        
        # Enhanced style settings
        s = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle=':',
            gridcolor='gray',
            y_on_right=True,  # Move Y-axis to the right
            rc={
                'axes.titlesize': 16,
                'axes.titleweight': 'bold'
            }
        )
        
        # Create plot with enhanced settings
        kwargs = {
            'type': 'candle',
            'style': s,
            'title': f'{ticker} - Last Year Performance',
            'figsize': (20, 10),  # Larger graph size
            'volume': True,
            'addplot': apds if apds else None,
            'tight_layout': True,
            'savefig': {
                'fname': f'{ticker.replace("^", "")}_analysis.png',
                'bbox_inches': 'tight',
                'dpi': 300
            },
            'datetime_format': '%d-%m-%Y',
            'ylabel': ''  # Remove Y-axis label
        }
        
        # Create and save the plot
        mpf.plot(data, **kwargs)
        
        return True