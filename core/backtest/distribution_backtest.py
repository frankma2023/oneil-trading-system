#!/usr/bin/env python3
# 抛盘日回测框架
# 用于验证抛盘日参数的有效性和优化阈值

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta
import itertools
import json
import os

from core.market.distribution_scanner import DistributionScanner, TradingDay, DistributionType

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """回测结果"""
    config: Dict
    total_days: int
    distribution_days: int
    special_days: int
    intraday_reversal_days: int
    heavy_distribution_days: int
    confirmation_days: int
    
    # 信号质量指标
    false_positive_rate: float = 0.0  # 假阳性率
    signal_density: float = 0.0       # 信号密度（抛盘日/总交易日）
    heavy_signal_ratio: float = 0.0   # 重抛盘日占比
    
    # 市场状态统计
    pressure_days: int = 0            # 承压状态天数
    bear_days: int = 0                # 熊市状态天数
    normal_days: int = 0              # 正常状态天数
    
    # 绩效指标（需要价格数据）
    distribution_day_avg_change: float = 0.0  # 抛盘日后N日平均涨跌幅
    next_day_change: float = 0.0              # 抛盘日后1日涨跌幅
    next_5day_change: float = 0.0             # 抛盘日后5日涨跌幅


class DistributionBacktester:
    """抛盘日策略回测器"""
    
    def __init__(self, data_access=None):
        self.data_access = data_access
        self.results_cache = {}  # 缓存回测结果
    
    def run_backtest(self, index_code: str, start_date: str, end_date: str, 
                    config: Optional[Dict] = None) -> BacktestResult:
        """
        运行抛盘日回测
        
        参数:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
            config: 扫描器配置
            
        返回:
            BacktestResult对象
        """
        # 获取数据
        df = self.data_access.get_index_data(index_code, start_date, end_date)
        if df.empty:
            raise ValueError(f"指数 {index_code} 在 {start_date} 到 {end_date} 无数据")
        
        # 创建扫描器
        scanner = DistributionScanner(config)
        
        # 分析所有交易日
        df_sorted = df.sort_values('date').reset_index()
        results = []
        window_days = []
        
        for i in range(1, len(df_sorted)):
            current_row = df_sorted.iloc[i]
            prev_row = df_sorted.iloc[i-1]
            
            # 准备交易日数据
            day = scanner.prepare_trading_day(current_row, prev_row)
            
            # 分析抛盘日
            day = scanner.analyze_distribution_day(day)
            
            results.append(day)
            
            # 模拟滚动窗口（简化版）
            window_days.append(day)
            if len(window_days) > 25:
                window_days.pop(0)
        
        # 统计结果
        return self._calculate_statistics(results, window_days, config)
    
    def _calculate_statistics(self, days: List[TradingDay], window_days: List[TradingDay], 
                             config: Dict) -> BacktestResult:
        """计算回测统计结果"""
        total_days = len(days)
        
        # 抛盘日统计
        distribution_days = sum(1 for d in days if d.distribution_type != DistributionType.NONE)
        special_days = sum(1 for d in days if d.distribution_type == DistributionType.SPECIAL)
        intraday_reversal_days = sum(1 for d in days if d.distribution_type == DistributionType.INTRADAY_REVERSAL)
        heavy_distribution_days = sum(1 for d in days if d.distribution_weight == 2)
        confirmation_days = sum(1 for d in days if d.is_confirmation_day)
        
        # 信号密度
        signal_density = distribution_days / total_days if total_days > 0 else 0
        heavy_signal_ratio = heavy_distribution_days / distribution_days if distribution_days > 0 else 0
        
        # 创建结果对象
        result = BacktestResult(
            config=config,
            total_days=total_days,
            distribution_days=distribution_days,
            special_days=special_days,
            intraday_reversal_days=intraday_reversal_days,
            heavy_distribution_days=heavy_distribution_days,
            confirmation_days=confirmation_days,
            signal_density=signal_density,
            heavy_signal_ratio=heavy_signal_ratio,
        )
        
        return result
    
    def parameter_grid_search(self, index_code: str, start_date: str, end_date: str,
                             param_grid: Dict) -> List[BacktestResult]:
        """
        参数网格搜索
        
        参数:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
            param_grid: 参数网格，例如:
                {
                    "standard_distribution_threshold": [-0.001, -0.0015, -0.002],
                    "special_max_gain": [0.0015, 0.002, 0.0025],
                    "special_volume_ratio": [1.2, 1.3, 1.4],
                }
                
        返回:
            所有参数组合的回测结果列表
        """
        # 生成所有参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(itertools.product(*param_values))
        
        results = []
        
        for i, combination in enumerate(param_combinations):
            # 创建配置
            config = {}
            for name, value in zip(param_names, combination):
                config[name] = value
            
            logger.info(f"测试参数组合 {i+1}/{len(param_combinations)}: {config}")
            
            try:
                # 运行回测
                result = self.run_backtest(index_code, start_date, end_date, config)
                results.append(result)
                
            except Exception as e:
                logger.error(f"参数组合 {config} 回测失败: {e}")
                continue
        
        # 按信号密度排序（或其他指标）
        results.sort(key=lambda x: x.signal_density, reverse=True)
        
        return results
    
    def optimize_upper_shadow_ratio(self, index_code: str, start_date: str, end_date: str,
                                   test_values: List[float] = None) -> List[BacktestResult]:
        """
        优化上影线比例阈值
        
        参数:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
            test_values: 测试的上影线比例值列表
            
        返回:
            不同阈值下的回测结果
        """
        if test_values is None:
            test_values = [1.0, 1.2, 1.5, 1.8, 2.0, 2.5]
        
        results = []
        
        for ratio in test_values:
            config = {
                "special_upper_shadow_ratio": ratio,
                "intraday_upper_shadow_ratio": ratio,
            }
            
            logger.info(f"测试上影线比例: {ratio}")
            
            try:
                result = self.run_backtest(index_code, start_date, end_date, config)
                results.append(result)
            except Exception as e:
                logger.error(f"上影线比例 {ratio} 回测失败: {e}")
                continue
        
        return results
    
    def analyze_false_positives(self, index_code: str, start_date: str, end_date: str,
                               config: Optional[Dict] = None) -> pd.DataFrame:
        """
        分析假阳性信号
        
        参数:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
            config: 扫描器配置
            
        返回:
            包含假阳性分析的DataFrame
        """
        # 获取数据
        df = self.data_access.get_index_data(index_code, start_date, end_date)
        if df.empty:
            raise ValueError(f"指数 {index_code} 在 {start_date} 到 {end_date} 无数据")
        
        # 创建扫描器
        scanner = DistributionScanner(config)
        
        # 分析所有交易日
        df_sorted = df.sort_values('date').reset_index()
        analysis_data = []
        
        for i in range(1, len(df_sorted)):
            current_row = df_sorted.iloc[i]
            prev_row = df_sorted.iloc[i-1]
            
            # 准备交易日数据
            day = scanner.prepare_trading_day(current_row, prev_row)
            
            # 分析抛盘日
            day = scanner.analyze_distribution_day(day)
            
            # 判断是否是假阳性（这里简化：如果抛盘日后3日上涨，可能是假阳性）
            is_false_positive = False
            if day.distribution_type != DistributionType.NONE and i + 3 < len(df_sorted):
                next_3day_change = (df_sorted.iloc[i+3]['close'] / day.close) - 1
                if next_3day_change > 0.01:  # 后3日上涨1%以上
                    is_false_positive = True
            
            analysis_data.append({
                'date': day.date,
                'change_pct': day.change_pct,
                'distribution_type': day.distribution_type.value,
                'distribution_weight': day.distribution_weight,
                'upper_shadow_ratio': day.upper_shadow / day.body_size if day.body_size > 0 else 0,
                'body_size': day.body_size,
                'is_false_positive': is_false_positive,
            })
        
        return pd.DataFrame(analysis_data)
    
    def save_results(self, results: List[BacktestResult], filename: str):
        """保存回测结果到文件"""
        # 转换为可序列化的字典
        results_dict = []
        for result in results:
            result_dict = {
                'config': result.config,
                'total_days': result.total_days,
                'distribution_days': result.distribution_days,
                'special_days': result.special_days,
                'intraday_reversal_days': result.intraday_reversal_days,
                'heavy_distribution_days': result.heavy_distribution_days,
                'confirmation_days': result.confirmation_days,
                'signal_density': result.signal_density,
                'heavy_signal_ratio': result.heavy_signal_ratio,
            }
            results_dict.append(result_dict)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"回测结果已保存到: {filename}")
    
    def load_results(self, filename: str) -> List[BacktestResult]:
        """从文件加载回测结果"""
        with open(filename, 'r', encoding='utf-8') as f:
            results_dict = json.load(f)
        
        results = []
        for rd in results_dict:
            result = BacktestResult(
                config=rd['config'],
                total_days=rd['total_days'],
                distribution_days=rd['distribution_days'],
                special_days=rd['special_days'],
                intraday_reversal_days=rd['intraday_reversal_days'],
                heavy_distribution_days=rd['heavy_distribution_days'],
                confirmation_days=rd['confirmation_days'],
                signal_density=rd['signal_density'],
                heavy_signal_ratio=rd['heavy_signal_ratio'],
            )
            results.append(result)
        
        return results
    
    def print_results_summary(self, results: List[BacktestResult], top_n: int = 10):
        """打印回测结果摘要"""
        print("=" * 80)
        print("抛盘日参数优化结果摘要")
        print("=" * 80)
        
        # 显示前N个最佳结果
        for i, result in enumerate(results[:top_n]):
            print(f"\n排名 {i+1}:")
            print(f"  配置: {result.config}")
            print(f"  总交易日: {result.total_days}")
            print(f"  抛盘日总数: {result.distribution_days}")
            print(f"  特殊抛盘日: {result.special_days}")
            print(f"  盘中反转日: {result.intraday_reversal_days}")
            print(f"  重抛盘日: {result.heavy_distribution_days}")
            print(f"  确认日: {result.confirmation_days}")
            print(f"  信号密度: {result.signal_density:.4f}")
            print(f"  重抛盘日占比: {result.heavy_signal_ratio:.4f}")
        
        # 统计信息
        if results:
            avg_signal_density = np.mean([r.signal_density for r in results])
            max_signal_density = np.max([r.signal_density for r in results])
            min_signal_density = np.min([r.signal_density for r in results])
            
            print(f"\n统计信息:")
            print(f"  平均信号密度: {avg_signal_density:.4f}")
            print(f"  最大信号密度: {max_signal_density:.4f}")
            print(f"  最小信号密度: {min_signal_density:.4f}")
            print(f"  测试参数组合数: {len(results)}")


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 模拟数据访问对象
    class MockDataAccess:
        def get_index_data(self, index_code, start_date, end_date):
            # 创建模拟数据
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            np.random.seed(42)
            
            data = {
                'date': dates,
                'open': 100 + np.random.randn(len(dates)).cumsum() * 0.5,
                'high': 0,
                'low': 0,
                'close': 0,
                'volume': 1000000 + np.random.randn(len(dates)) * 100000,
            }
            
            df = pd.DataFrame(data)
            
            # 计算高、低、收
            df['high'] = df['open'] + abs(np.random.randn(len(dates))) * 2
            df['low'] = df['open'] - abs(np.random.randn(len(dates))) * 2
            df['close'] = df['open'] + np.random.randn(len(dates)) * 1
            
            return df
    
    # 创建回测器
    backtester = DistributionBacktester(MockDataAccess())
    
    # 定义测试参数网格
    param_grid = {
        "standard_distribution_threshold": [-0.0008, -0.001, -0.0012],
        "special_max_gain": [0.0015, 0.002, 0.0025],
        "special_volume_ratio": [1.2, 1.3, 1.4],
    }
    
    print("开始抛盘日参数优化...")
    
    # 运行网格搜索
    results = backtester.parameter_grid_search(
        index_code="000985",
        start_date="2023-01-01",
        end_date="2023-12-31",
        param_grid=param_grid
    )
    
    # 打印结果
    backtester.print_results_summary(results, top_n=5)
    
    # 测试上影线比例优化
    print("\n\n测试上影线比例优化...")
    shadow_results = backtester.optimize_upper_shadow_ratio(
        index_code="000985",
        start_date="2023-01-01",
        end_date="2023-12-31",
        test_values=[1.0, 1.2, 1.5, 1.8, 2.0]
    )
    
    for result in shadow_results:
        print(f"上影线比例 {result.config.get('special_upper_shadow_ratio', 'N/A')}: "
              f"信号密度={result.signal_density:.4f}, "
              f"特殊抛盘日={result.special_days}")