import pandas as pd
import numpy as np

class TechnicalAnalyzer:
    """
    技术分析类，负责计算各种技术指标
    """
    
    def __init__(self):
        pass
    
    def calculate_indicators(self, stock_data):
        """
        计算各种技术指标
        
        参数:
            stock_data (pandas.DataFrame): 股票历史数据
            
        返回:
            dict: 包含各种技术指标的字典
        """
        if stock_data.empty:
            return {}
        
        # 创建结果字典
        indicators = {}
        
        # 计算移动平均线
        indicators['MA5'] = self._calculate_ma(stock_data, 5)
        indicators['MA10'] = self._calculate_ma(stock_data, 10)
        indicators['MA20'] = self._calculate_ma(stock_data, 20)
        indicators['MA30'] = self._calculate_ma(stock_data, 30)
        indicators['MA60'] = self._calculate_ma(stock_data, 60)
        
        # 计算MACD
        macd_result = self._calculate_macd(stock_data)
        indicators['MACD'] = macd_result['MACD']
        indicators['MACD_signal'] = macd_result['signal']
        indicators['MACD_hist'] = macd_result['hist']
        
        # 计算KDJ
        kdj_result = self._calculate_kdj(stock_data)
        indicators['K'] = kdj_result['K']
        indicators['D'] = kdj_result['D']
        indicators['J'] = kdj_result['J']
        
        # 计算RSI
        indicators['RSI6'] = self._calculate_rsi(stock_data, 6)
        indicators['RSI12'] = self._calculate_rsi(stock_data, 12)
        indicators['RSI24'] = self._calculate_rsi(stock_data, 24)
        
        # 计算布林带
        bollinger_result = self._calculate_bollinger_bands(stock_data)
        indicators['BOLL_upper'] = bollinger_result['upper']
        indicators['BOLL_middle'] = bollinger_result['middle']
        indicators['BOLL_lower'] = bollinger_result['lower']
        
        # 计算成交量变化
        indicators['volume_ma5'] = self._calculate_volume_ma(stock_data, 5)
        indicators['volume_ma10'] = self._calculate_volume_ma(stock_data, 10)
        
        # 计算BIAS乖离率
        indicators['BIAS6'] = self._calculate_bias(stock_data, 6)
        indicators['BIAS12'] = self._calculate_bias(stock_data, 12)
        indicators['BIAS24'] = self._calculate_bias(stock_data, 24)
        
        return indicators
    
    def _calculate_ma(self, data, window):
        """
        计算移动平均线
        """
        return data['close'].rolling(window=window).mean()
    
    def _calculate_volume_ma(self, data, window):
        """
        计算成交量移动平均线
        """
        return data['volume'].rolling(window=window).mean()
    
    def _calculate_macd(self, data, fast_period=12, slow_period=26, signal_period=9):
        """
        计算MACD指标
        """
        # 计算快速和慢速EMA
        ema_fast = data['close'].ewm(span=fast_period, adjust=False).mean()
        ema_slow = data['close'].ewm(span=slow_period, adjust=False).mean()
        
        # 计算MACD线
        macd_line = ema_fast - ema_slow
        
        # 计算信号线
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        # 计算柱状图
        histogram = macd_line - signal_line
        
        return {
            'MACD': macd_line,
            'signal': signal_line,
            'hist': histogram
        }
    
    def _calculate_kdj(self, data, n=9, m1=3, m2=3):
        """
        计算KDJ指标
        """
        # 计算最低价和最高价的n日移动窗口
        low_min = data['low'].rolling(window=n).min()
        high_max = data['high'].rolling(window=n).max()
        
        # 计算RSV
        rsv = 100 * ((data['close'] - low_min) / (high_max - low_min))
        rsv = rsv.fillna(50)
        
        # 计算K值
        k = pd.Series(0.0, index=data.index)
        d = pd.Series(0.0, index=data.index)
        j = pd.Series(0.0, index=data.index)
        
        for i in range(len(data)):
            if i == 0:
                k[i] = 50
                d[i] = 50
            else:
                k[i] = (m1 - 1) * k[i-1] / m1 + rsv[i] / m1
                d[i] = (m2 - 1) * d[i-1] / m2 + k[i] / m2
            j[i] = 3 * k[i] - 2 * d[i]
        
        return {
            'K': k,
            'D': d,
            'J': j
        }
    
    def _calculate_rsi(self, data, period):
        """
        计算RSI指标
        """
        # 计算价格变化
        delta = data['close'].diff()
        
        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # 计算平均上涨和下跌
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # 计算相对强度
        rs = avg_gain / avg_loss
        
        # 计算RSI
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_bollinger_bands(self, data, window=20, num_std=2):
        """
        计算布林带
        """
        # 计算中轨线（简单移动平均线）
        middle_band = data['close'].rolling(window=window).mean()
        
        # 计算标准差
        std = data['close'].rolling(window=window).std()
        
        # 计算上轨线和下轨线
        upper_band = middle_band + (std * num_std)
        lower_band = middle_band - (std * num_std)
        
        return {
            'upper': upper_band,
            'middle': middle_band,
            'lower': lower_band
        }
    
    def _calculate_bias(self, data, period):
        """
        计算乖离率
        """
        ma = self._calculate_ma(data, period)
        bias = (data['close'] - ma) / ma * 100
        return bias