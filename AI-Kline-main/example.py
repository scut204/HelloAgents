import os
from dotenv import load_dotenv

from modules.data_fetcher import StockDataFetcher
from modules.technical_analyzer import TechnicalAnalyzer
from modules.visualizer import Visualizer
from modules.ai_analyzer import AIAnalyzer

# 加载环境变量
load_dotenv()

def analyze_stock(stock_code, period='1年', save_path='./output'):
    """示例函数：分析指定股票"""
    # 确保输出目录存在
    os.makedirs(save_path, exist_ok=True)
    
    # 初始化各模块
    data_fetcher = StockDataFetcher()
    technical_analyzer = TechnicalAnalyzer()
    visualizer = Visualizer()
    ai_analyzer = AIAnalyzer()
    
    # 获取股票数据
    print(f"正在获取 {stock_code} 的历史数据...")
    stock_data = data_fetcher.fetch_stock_data(stock_code, period)
    
    # 获取财务和新闻数据
    print(f"正在获取 {stock_code} 的财务和新闻数据...")
    financial_data = data_fetcher.fetch_financial_data(stock_code)
    news_data = data_fetcher.fetch_news_data(stock_code)
    
    # 计算技术指标
    print("正在计算技术指标...")
    indicators = technical_analyzer.calculate_indicators(stock_data)
    
    # 生成可视化图表
    print("正在生成K线图和技术指标图...")
    chart_path = visualizer.create_charts(stock_data, indicators, stock_code, save_path)
    
    # AI分析预测
    print("正在使用AI分析预测未来走势...")
    analysis_result = ai_analyzer.analyze(stock_data, indicators, financial_data, news_data, stock_code, save_path)
    
    # 保存分析结果
    result_path = os.path.join(save_path, f"{stock_code}_analysis_result.txt")
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(analysis_result)
    
    print(f"\n分析完成！")
    print(f"K线图和技术指标图已保存至: {chart_path}")
    print(f"AI分析结果已保存至: {result_path}")
    
    return analysis_result

# 示例：分析平安银行(000001)股票
if __name__ == "__main__":
    # 分析平安银行
    result = analyze_stock('000001')
    print("\n分析结果预览:")
    print(result[:500] + "...")
    
    # 您可以尝试分析其他股票，例如:
    # analyze_stock('600519')  # 贵州茅台
    # analyze_stock('000858')  # 五粮液
    # analyze_stock('601318')  # 中国平安