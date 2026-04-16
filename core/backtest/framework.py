#!/usr/bin/env python3
# 科学回测框架
# 用于验证欧奈尔指标和策略的有效性

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    parameters: Dict[str, Any]
    start_date: str
    end_date: str
    
    # 绩效指标
    total_return: float = 0.0  # 总收益率
    annual_return: float = 0.0  # 年化收益率
    sharpe_ratio: float = 0.0  # 夏普比率
    max_drawdown: float = 0.0  # 最大回撤
    win_rate: float = 0.0  # 胜率
    profit_factor: float = 0.0  # 盈亏比
    total_trades: int = 0  # 总交易次数
    
    # 交易记录
    trades: List[Dict] = field(default_factory=list)
    equity_curve: pd.Series = None
    drawdown_curve: pd.Series = None
    
    # 其他数据
    execution_time: float = 0.0  # 执行时间（秒）
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        result = {
            'strategy_name': self.strategy_name,
            'parameters': self.parameters,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'performance': {
                'total_return': self.total_return,
                'annual_return': self.annual_return,
                'sharpe_ratio': self.sharpe_ratio,
                'max_drawdown': self.max_drawdown,
                'win_rate': self.win_rate,
                'profit_factor': self.profit_factor,
                'total_trades': self.total_trades,
            },
            'execution_time': self.execution_time,
            'metadata': self.metadata,
        }
        return result
    
    def summary(self) -> str:
        """生成摘要文本"""
        return f"""
策略: {self.strategy_name}
时间段: {self.start_date} 到 {self.end_date}
参数: {json.dumps(self.parameters, ensure_ascii=False, indent=2)}
        
绩效指标:
  总收益率: {self.total_return:.2%}
  年化收益率: {self.annual_return:.2%}
  夏普比率: {self.sharpe_ratio:.2f}
  最大回撤: {self.max_drawdown:.2%}
  胜率: {self.win_rate:.2%}
  盈亏比: {self.profit_factor:.2f}
  交易次数: {self.total_trades}
        
执行时间: {self.execution_time:.2f}秒
"""


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.results_cache = {}  # 缓存回测结果
        
    def run(self, strategy: 'BaseStrategy', 
            start_date: str, 
            end_date: str,
            save_results: bool = True) -> BacktestResult:
        """执行回测"""
        import time
        start_time = time.time()
        
        logger.info(f"开始回测策略: {strategy.name}, 时间段: {start_date} 到 {end_date}")
        
        # 初始化策略
        strategy.initialize()
        
        # 获取数据
        data = strategy.get_data(start_date, end_date)
        if data.empty:
            raise ValueError(f"数据为空，时间段: {start_date} 到 {end_date}")
        
        # 初始化投资组合
        portfolio = {
            'cash': self.initial_capital,
            'positions': {},  # {code: {'shares':数量, 'avg_price':成本价}}
            'equity': [self.initial_capital],  # 权益曲线
            'dates': [data.index[0]],
        }
        
        trades = []
        signals = []
        
        # 逐日回测
        for i, (date, row) in enumerate(data.iterrows()):
            current_date = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            
            # 生成信号
            signal = strategy.generate_signal(date, row, portfolio, data.iloc[:i+1] if i > 0 else pd.DataFrame())
            if signal:
                signals.append({
                    'date': current_date,
                    'signal': signal.signal_type,
                    'strength': signal.strength,
                    'reason': signal.reason,
                })
                
                # 执行交易
                if signal.signal_type in ['buy', 'sell']:
                    trade = self._execute_trade(signal, portfolio, row)
                    if trade:
                        trades.append(trade)
            
            # 更新持仓市值
            total_value = portfolio['cash']
            for code, pos in portfolio['positions'].items():
                # 简化：假设能按收盘价卖出
                if code in row and pd.notna(row[code]):
                    total_value += pos['shares'] * row[code]
                # 实际中需要获取个股价格
            
            portfolio['equity'].append(total_value)
            portfolio['dates'].append(current_date)
        
        # 计算绩效指标
        equity_series = pd.Series(portfolio['equity'][1:], index=pd.to_datetime(portfolio['dates'][1:]))
        
        result = BacktestResult(
            strategy_name=strategy.name,
            parameters=strategy.get_parameters(),
            start_date=start_date,
            end_date=end_date,
            trades=trades,
            equity_curve=equity_series,
            execution_time=time.time() - start_time,
        )
        
        # 计算绩效指标
        self._calculate_performance(result)
        
        # 缓存结果
        if save_results:
            result_hash = self._get_result_hash(result)
            self.results_cache[result_hash] = result
        
        logger.info(f"回测完成，总收益率: {result.total_return:.2%}")
        return result
    
    def _execute_trade(self, signal: 'TradeSignal', portfolio: Dict, market_data: pd.Series) -> Optional[Dict]:
        """执行交易（简化版）"""
        # 简化实现，实际需要根据信号类型和持仓执行
        trade = {
            'date': signal.date,
            'signal': signal.signal_type,
            'reason': signal.reason,
            'price': market_data.get('close', 0) if hasattr(market_data, 'get') else 0,
        }
        return trade
    
    def _calculate_performance(self, result: BacktestResult):
        """计算绩效指标"""
        if result.equity_curve is None or len(result.equity_curve) < 2:
            return
        
        equity = result.equity_curve
        returns = equity.pct_change().dropna()
        
        if len(returns) == 0:
            return
        
        # 总收益率
        result.total_return = (equity.iloc[-1] / equity.iloc[0] - 1)
        
        # 年化收益率
        days = (equity.index[-1] - equity.index[0]).days
        if days > 0:
            result.annual_return = (1 + result.total_return) ** (365.25 / days) - 1
        
        # 夏普比率（假设无风险利率0）
        if returns.std() > 0:
            result.sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
        
        # 最大回撤
        cummax = equity.expanding().max()
        drawdown = (equity - cummax) / cummax
        result.max_drawdown = drawdown.min()
        
        # 交易统计（简化）
        if result.trades:
            winning_trades = [t for t in result.trades if t.get('profit', 0) > 0]
            result.win_rate = len(winning_trades) / len(result.trades) if result.trades else 0
            result.total_trades = len(result.trades)
    
    def _get_result_hash(self, result: BacktestResult) -> str:
        """生成结果哈希值用于缓存"""
        content = f"{result.strategy_name}_{json.dumps(result.parameters)}_{result.start_date}_{result.end_date}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def run_parameter_sweep(self, strategy_class, param_grid: Dict[str, List], 
                           start_date: str, end_date: str) -> List[BacktestResult]:
        """参数扫描"""
        results = []
        
        # 生成所有参数组合
        param_combinations = self._generate_param_combinations(param_grid)
        
        logger.info(f"开始参数扫描，共 {len(param_combinations)} 种组合")
        
        for i, params in enumerate(param_combinations, 1):
            logger.info(f"测试参数组合 {i}/{len(param_combinations)}: {params}")
            
            strategy = strategy_class(**params)
            result = self.run(strategy, start_date, end_date, save_results=False)
            results.append(result)
        
        return results
    
    def _generate_param_combinations(self, param_grid: Dict[str, List]) -> List[Dict]:
        """生成参数组合网格"""
        from itertools import product
        
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        
        combinations = []
        for combo in product(*values):
            param_dict = dict(zip(keys, combo))
            combinations.append(param_dict)
        
        return combinations
    
    def compare_results(self, results: List[BacktestResult]) -> pd.DataFrame:
        """比较多个回测结果"""
        records = []
        
        for result in results:
            records.append({
                'strategy': result.strategy_name,
                **result.parameters,
                'total_return': result.total_return,
                'annual_return': result.annual_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'win_rate': result.win_rate,
                'profit_factor': result.profit_factor,
                'total_trades': result.total_trades,
            })
        
        return pd.DataFrame(records)
    
    def save_result(self, result: BacktestResult, filepath: str = None):
        """保存回测结果"""
        if filepath is None:
            # 自动生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"backtest_{result.strategy_name}_{timestamp}.json"
            filepath = Path("backtest_results") / filename
            Path("backtest_results").mkdir(exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"结果保存到: {filepath}")
    
    def load_result(self, filepath: str) -> BacktestResult:
        """加载回测结果"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 重新创建结果对象（简化）
        result = BacktestResult(
            strategy_name=data['strategy_name'],
            parameters=data['parameters'],
            start_date=data['start_date'],
            end_date=data['end_date'],
        )
        
        if 'performance' in data:
            perf = data['performance']
            result.total_return = perf.get('total_return', 0)
            result.annual_return = perf.get('annual_return', 0)
            result.sharpe_ratio = perf.get('sharpe_ratio', 0)
            result.max_drawdown = perf.get('max_drawdown', 0)
            result.win_rate = perf.get('win_rate', 0)
            result.profit_factor = perf.get('profit_factor', 0)
            result.total_trades = perf.get('total_trades', 0)
        
        return result


# 策略基类
class BaseStrategy:
    """策略基类"""
    
    def __init__(self, name: str = "BaseStrategy"):
        self.name = name
    
    def initialize(self):
        """初始化策略"""
        pass
    
    def get_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取策略所需数据"""
        raise NotImplementedError
    
    def generate_signal(self, date, market_data: pd.Series, 
                       portfolio: Dict, history: pd.DataFrame) -> Optional['TradeSignal']:
        """生成交易信号"""
        raise NotImplementedError
    
    def get_parameters(self) -> Dict:
        """获取策略参数"""
        return {}


@dataclass
class TradeSignal:
    """交易信号"""
    date: str
    signal_type: str  # buy/sell/hold
    strength: float = 1.0
    reason: str = ""
    parameters: Dict = field(default_factory=dict)


# 示例策略：基于抛盘日计数的市场择时策略
class DistributionDayStrategy(BaseStrategy):
    """抛盘日择时策略"""
    
    def __init__(self, 
                 distribution_threshold: int = 3,
                 follow_through_enabled: bool = True,
                 initial_position: float = 0.5):
        super().__init__(name="DistributionDayStrategy")
        self.distribution_threshold = distribution_threshold
        self.follow_through_enabled = follow_through_enabled
        self.initial_position = initial_position  # 初始仓位比例
        
        # 内部状态
        self.market_scanner = None
        self.data_access = None
    
    def initialize(self):
        """初始化"""
        from data.access import get_data_access
        from core.market.indicators import MarketScanner
        
        self.data_access = get_data_access()
        self.market_scanner = MarketScanner(self.data_access)
    
    def get_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取市场数据"""
        # 获取中证全指数据
        df = self.data_access.get_index_data("000985", start_date, end_date)
        return df
    
    def generate_signal(self, date, market_data: pd.Series, 
                       portfolio: Dict, history: pd.DataFrame) -> Optional[TradeSignal]:
        """生成信号"""
        if history.empty:
            return None
        
        # 分析历史市场数据
        days = self.market_scanner.analyze_index(start_date=history.index[0].strftime('%Y-%m-%d'),
                                                 end_date=date.strftime('%Y-%m-%d'))
        
        if not days:
            return None
        
        # 计算25日抛盘日计数
        window_days = 25
        recent_days = days[-window_days:] if len(days) >= window_days else days
        dist_count = sum(1 for d in recent_days if d.is_distribution_day)
        
        # 检查最新交易日
        latest_day = days[-1] if days else None
        
        signal_type = "hold"
        reason = ""
        
        # 抛盘日信号
        if dist_count >= self.distribution_threshold:
            signal_type = "sell"
            reason = f"抛盘日计数达到{dist_count}，超过阈值{self.distribution_threshold}"
        
        # 追盘日信号（优先级更高）
        elif (self.follow_through_enabled and latest_day and 
              latest_day.is_follow_through_day):
            signal_type = "buy"
            reason = "出现追盘日，市场确认上升趋势"
        
        if signal_type != "hold":
            return TradeSignal(
                date=date.strftime('%Y-%m-%d'),
                signal_type=signal_type,
                strength=min(dist_count / 5.0, 1.0) if signal_type == "sell" else 1.0,
                reason=reason,
                parameters={
                    'distribution_count': dist_count,
                    'threshold': self.distribution_threshold,
                }
            )
        
        return None
    
    def get_parameters(self) -> Dict:
        return {
            'distribution_threshold': self.distribution_threshold,
            'follow_through_enabled': self.follow_through_enabled,
            'initial_position': self.initial_position,
        }


# 性能分析工具
class PerformanceAnalyzer:
    """绩效分析器"""
    
    @staticmethod
    def calculate_metrics(equity_curve: pd.Series) -> Dict:
        """计算绩效指标"""
        if equity_curve.empty or len(equity_curve) < 2:
            return {}
        
        returns = equity_curve.pct_change().dropna()
        
        metrics = {
            'total_return': equity_curve.iloc[-1] / equity_curve.iloc[0] - 1,
            'volatility': returns.std() * np.sqrt(252),
            'sharpe_ratio': returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0,
            'sortino_ratio': PerformanceAnalyzer._calculate_sortino(returns),
            'max_drawdown': PerformanceAnalyzer._calculate_max_drawdown(equity_curve),
            'calmar_ratio': PerformanceAnalyzer._calculate_calmar(equity_curve),
            'win_rate': (returns > 0).mean() if len(returns) > 0 else 0,
            'profit_factor': PerformanceAnalyzer._calculate_profit_factor(returns),
            'skewness': returns.skew(),
            'kurtosis': returns.kurtosis(),
        }
        
        return metrics
    
    @staticmethod
    def _calculate_sortino(returns: pd.Series) -> float:
        """计算索提诺比率"""
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return 0
        downside_std = downside_returns.std()
        if downside_std == 0:
            return 0
        return returns.mean() / downside_std * np.sqrt(252)
    
    @staticmethod
    def _calculate_max_drawdown(equity: pd.Series) -> float:
        """计算最大回撤"""
        cummax = equity.expanding().max()
        drawdown = (equity - cummax) / cummax
        return drawdown.min()
    
    @staticmethod
    def _calculate_calmar(equity: pd.Series) -> float:
        """计算Calmar比率"""
        max_dd = PerformanceAnalyzer._calculate_max_drawdown(equity)
        if max_dd == 0:
            return 0
        total_return = equity.iloc[-1] / equity.iloc[0] - 1
        return total_return / abs(max_dd)
    
    @staticmethod
    def _calculate_profit_factor(returns: pd.Series) -> float:
        """计算盈亏比"""
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0
        return gross_profit / gross_loss


if __name__ == "__main__":
    # 测试回测框架
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("测试回测框架...")
    
    # 创建回测引擎
    engine = BacktestEngine(initial_capital=100000)
    
    # 创建策略
    strategy = DistributionDayStrategy(
        distribution_threshold=3,
        follow_through_enabled=True,
        initial_position=0.5
    )
    
    # 运行回测（最近一年）
    end_date = "2024-12-31"  # 假设的结束日期
    start_date = "2024-01-01"
    
    try:
        result = engine.run(strategy, start_date, end_date)
        print(result.summary())
        
        # 测试参数扫描
        param_grid = {
            'distribution_threshold': [2, 3, 4],
            'follow_through_enabled': [True, False],
        }
        
        print("\n测试参数扫描...")
        results = engine.run_parameter_sweep(DistributionDayStrategy, param_grid, start_date, end_date)
        
        if results:
            comparison = engine.compare_results(results)
            print("\n参数扫描结果:")
            print(comparison.to_string())
            
            # 找出最佳参数
            best_idx = comparison['sharpe_ratio'].idxmax()
            best_params = comparison.iloc[best_idx]
            print(f"\n最佳参数组合（夏普比率最高）:")
            print(f"  抛盘日阈值: {best_params['distribution_threshold']}")
            print(f"  追盘日启用: {best_params['follow_through_enabled']}")
            print(f"  夏普比率: {best_params['sharpe_ratio']:.2f}")
        
    except Exception as e:
        print(f"回测测试失败: {e}")
        import traceback
        traceback.print_exc()