#!/usr/bin/env python3
# 全新欧奈尔抛盘日扫描器
# 严格按照《抛盘日定义.md》文档实现
# 2026-04-14 全新开发

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class DistributionType(Enum):
    """抛盘日类型枚举"""
    NONE = "none"                 # 无抛盘日
    STANDARD = "standard"         # 标准抛盘日
    SPECIAL = "special"           # 特殊抛盘日（假阳线/滞涨）
    INTRADAY_REVERSAL = "intraday_reversal"  # 盘中反转抛盘日


class MarketIndex(Enum):
    """市场指数枚举"""
    CSI_ALL = "000985"     # 中证全指
    CSI_300 = "000300"     # 沪深300


@dataclass
class TradingDay:
    """交易日完整数据"""
    date: str                     # 日期 YYYY-MM-DD
    index_code: str              # 指数代码
    
    # 价格数据
    open: float
    high: float
    low: float
    close: float
    volume: float                # 成交量
    
    # 衍生数据
    change_pct: float = 0.0      # 涨跌幅（小数）
    volume_ratio: float = 1.0    # 成交量相对前一日比率
    
    # 技术特征
    upper_shadow: float = 0.0    # 上影线长度
    lower_shadow: float = 0.0    # 下影线长度
    body_size: float = 0.0       # 实体大小（绝对值）
    intraday_high_pct: float = 0.0  # 盘中最高涨幅（小数）
    intraday_low_pct: float = 0.0   # 盘中最低涨幅（小数）
    
    # 抛盘日分析结果
    is_flat_day: bool = False           # 是否是平盘日
    distribution_type: DistributionType = DistributionType.NONE
    distribution_weight: int = 0        # 抛盘日权重（1或2）
    
    # 确认日
    is_confirmation_day: bool = False   # 是否是升势确认日


class DistributionScanner:
    """抛盘日扫描器 - 严格按照欧奈尔定义实现"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化扫描器
        
        参数:
            config: 配置字典，包含所有阈值参数
        """
        self.config = self._get_default_config()
        if config:
            self.config.update(config)
        
        logger.info(f"抛盘日扫描器初始化完成，配置: {self.config}")
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            # 平盘日过滤阈值
            "flat_day_threshold": 0.0005,  # 涨跌幅绝对值<0.05%
            
            # 标准抛盘日
            "standard_distribution_threshold": -0.001,  # 跌幅≤-0.1%
            "standard_volume_ratio": 1.05,              # 成交量>前一日1.05倍
            
            # 特殊抛盘日（假阳线/滞涨）
            "special_max_gain": 0.002,                 # 涨幅<0.2%
            "special_intraday_min": 0.005,             # 盘中最高≥0.5%
            "special_volume_ratio": 1.3,               # 成交量>前一日1.3倍
            "special_upper_shadow_ratio": 1.5,         # 上影线≥实体×1.5
            
            # 盘中反转抛盘日
            "intraday_volume_ratio": 1.2,              # 成交量>前一日1.2倍
            "intraday_upper_shadow_ratio": 1.5,        # 上影线≥实体×1.5
            
            # 多重计数规则
            "heavy_distribution_threshold": -0.015,    # 跌幅≥-1.5%且放量计为2个
            "heavy_volume_ratio": 1.0,                 # 成交量>前一日
            
            # 升势确认日
            "confirmation_day_gain": 0.015,            # 涨幅≥1.5%
            "confirmation_volume_ratio": 1.0,          # 成交量≥前一日
            
            # 滚动窗口
            "window_days": 25,                         # 25个交易日滚动窗口
            
            # 市场状态阈值
            "pressure_threshold": 5,                   # 承压状态阈值（≥5个）
            "bear_threshold": 8,                       # 熊市状态阈值（≥8个）
        }
    
    def prepare_trading_day(self, row: pd.Series, prev_row: pd.Series = None) -> TradingDay:
        """
        准备交易日数据，计算所有技术特征
        
        参数:
            row: 当前交易日数据
            prev_row: 前一交易日数据
            
        返回:
            TradingDay对象
        """
        # 基本价格数据
        day = TradingDay(
            date=row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
            index_code=row.get('index_code', '000985'),
            open=float(row['open']),
            high=float(row['high']),
            low=float(row['low']),
            close=float(row['close']),
            volume=float(row['volume']),
        )
        
        # 计算涨跌幅
        if prev_row is not None:
            prev_close = float(prev_row['close'])
            day.change_pct = (day.close / prev_close) - 1
            
            # 计算成交量比率
            prev_volume = float(prev_row['volume'])
            day.volume_ratio = day.volume / prev_volume if prev_volume > 0 else 1.0
        
        # 计算盘中最高/最低涨幅
        if prev_row is not None:
            prev_close = float(prev_row['close'])
            day.intraday_high_pct = (day.high / prev_close) - 1
            day.intraday_low_pct = (day.low / prev_close) - 1
        
        # 计算技术特征
        day = self._calculate_technical_features(day)
        
        # 检查平盘日
        day.is_flat_day = self._is_flat_day(day)
        
        return day
    
    def _calculate_technical_features(self, day: TradingDay) -> TradingDay:
        """计算技术特征：上影线、下影线、实体大小"""
        # 计算实体大小（绝对值）
        day.body_size = abs(day.close - day.open)
        
        # 计算上影线（最高 - max(开盘, 收盘)）
        day.upper_shadow = day.high - max(day.open, day.close)
        
        # 计算下影线（min(开盘, 收盘) - 最低）
        day.lower_shadow = min(day.open, day.close) - day.low
        
        return day
    
    def _is_flat_day(self, day: TradingDay) -> bool:
        """检查是否是平盘日（涨跌幅绝对值<0.05%）"""
        return abs(day.change_pct) < self.config["flat_day_threshold"]
    
    def analyze_distribution_day(self, day: TradingDay) -> TradingDay:
        """
        分析单个交易日的抛盘日状态
        
        严格按照优先级：反转日 > 特殊日 > 标准日
        
        参数:
            day: 交易日数据
            
        返回:
            更新后的交易日数据
        """
        # 检查是否是平盘日
        day.is_flat_day = self._is_flat_day(day)
        
        # 如果是平盘日，不计算抛盘日
        if day.is_flat_day:
            day.distribution_type = DistributionType.NONE
            day.distribution_weight = 0
            return day
        
        # 按优先级检查抛盘日类型
        distribution_info = None
        
        # 1. 检查盘中反转抛盘日（最高优先级）
        if self._is_intraday_reversal(day):
            distribution_info = (DistributionType.INTRADAY_REVERSAL, 1)
        
        # 2. 检查特殊抛盘日（第二优先级）
        elif self._is_special_distribution(day):
            distribution_info = (DistributionType.SPECIAL, 1)
        
        # 3. 检查标准抛盘日（最低优先级）
        elif self._is_standard_distribution(day):
            weight = 2 if self._is_heavy_distribution(day) else 1
            distribution_info = (DistributionType.STANDARD, weight)
        
        # 设置结果
        if distribution_info:
            day.distribution_type, day.distribution_weight = distribution_info
        else:
            day.distribution_type = DistributionType.NONE
            day.distribution_weight = 0
        
        # 检查是否是升势确认日
        day.is_confirmation_day = self._is_confirmation_day(day)
        
        return day
    
    def _is_intraday_reversal(self, day: TradingDay) -> bool:
        """
        检查盘中反转抛盘日
        
        条件:
        1. 收盘价 < 开盘价（收阴）
        2. 成交量 > 前一日 × 1.2
        3. 上影线 ≥ 实体 × 1.5
        4. 盘中最高曾上涨 ≥ 0.5%
        """
        # 条件1: 收阴
        if day.close >= day.open:
            return False
        
        # 条件2: 成交量放大
        if day.volume_ratio < self.config["intraday_volume_ratio"]:
            return False
        
        # 条件3: 上影线条件
        if day.body_size > 0:  # 避免除零
            upper_shadow_ratio = day.upper_shadow / day.body_size
            if upper_shadow_ratio < self.config["intraday_upper_shadow_ratio"]:
                return False
        else:
            # 实体为0，不符合条件
            return False
        
        # 条件4: 盘中最高曾上涨 ≥ 0.5%
        if day.intraday_high_pct < self.config["special_intraday_min"]:
            return False
        
        return True
    
    def _is_special_distribution(self, day: TradingDay) -> bool:
        """
        检查特殊抛盘日（假阳线/滞涨）
        
        条件（必须同时满足）:
        1. 收盘涨幅 < 0.2%
        2. 盘中最高涨幅 ≥ 0.5%
        3. 成交量 > 前一日 × 1.3
        4. 上影线 ≥ 实体 × 1.5
        """
        # 条件1: 收盘涨幅 < 0.2%
        if day.change_pct >= self.config["special_max_gain"]:
            return False
        
        # 条件2: 盘中最高涨幅 ≥ 0.5%
        if day.intraday_high_pct < self.config["special_intraday_min"]:
            return False
        
        # 条件3: 成交量放大
        if day.volume_ratio < self.config["special_volume_ratio"]:
            return False
        
        # 条件4: 上影线条件
        if day.body_size > 0:  # 避免除零
            upper_shadow_ratio = day.upper_shadow / day.body_size
            if upper_shadow_ratio < self.config["special_upper_shadow_ratio"]:
                return False
        else:
            # 实体为0，不符合条件
            return False
        
        return True
    
    def _is_standard_distribution(self, day: TradingDay) -> bool:
        """
        检查标准抛盘日
        
        条件:
        1. 跌幅 ≤ -0.1%
        2. 成交量 > 前一日
        """
        # 条件1: 跌幅 ≤ -0.1%
        if day.change_pct > self.config["standard_distribution_threshold"]:
            return False
        
        # 条件2: 成交量放大
        if day.volume_ratio <= self.config["standard_volume_ratio"]:
            return False
        
        return True
    
    def _is_heavy_distribution(self, day: TradingDay) -> bool:
        """
        检查是否是重抛盘日（跌幅≥-1.5%且放量，计为2个抛盘日）
        """
        # 必须是标准抛盘日
        if not self._is_standard_distribution(day):
            return False
        
        # 跌幅 ≥ -1.5%
        if day.change_pct < self.config["heavy_distribution_threshold"]:
            return False
        
        # 成交量放大
        if day.volume_ratio < self.config["heavy_volume_ratio"]:
            return False
        
        return True
    
    def _is_confirmation_day(self, day: TradingDay) -> bool:
        """
        检查是否是升势确认日
        
        条件:
        1. 涨幅 ≥ 1.5%
        2. 成交量 ≥ 前一日
        """
        # 条件1: 涨幅 ≥ 1.5%
        if day.change_pct < self.config["confirmation_day_gain"]:
            return False
        
        # 条件2: 成交量放大
        if day.volume_ratio < self.config["confirmation_volume_ratio"]:
            return False
        
        return True


class DistributionWindow:
    """25交易日滚动窗口管理器"""
    
    def __init__(self, window_days: int = 25):
        self.window_days = window_days
        self.days: List[TradingDay] = []  # 按日期排序，最新的在最后
        
        # 抛盘日统计
        self.distribution_counts = {
            DistributionType.STANDARD: 0,
            DistributionType.SPECIAL: 0,
            DistributionType.INTRADAY_REVERSAL: 0,
            "total": 0,  # 加权总数
            "raw_total": 0,  # 原始计数（未加权）
        }
        
        # 确认日列表
        self.confirmation_days: List[TradingDay] = []
    
    def add_day(self, day: TradingDay) -> None:
        """
        添加交易日到窗口，并更新统计
        
        参数:
            day: 交易日数据
        """
        # 添加到窗口
        self.days.append(day)
        
        # 按日期排序
        self.days.sort(key=lambda x: x.date)
        
        # 维护窗口大小
        if len(self.days) > self.window_days:
            removed_day = self.days.pop(0)
            self._remove_day_from_stats(removed_day)
        
        # 更新统计
        self._update_stats(day)
        
        # 如果是确认日，添加到确认日列表
        if day.is_confirmation_day:
            self.confirmation_days.append(day)
    
    def _remove_day_from_stats(self, day: TradingDay) -> None:
        """从统计中移除交易日"""
        if day.distribution_type != DistributionType.NONE:
            # 更新抛盘日计数
            self.distribution_counts[day.distribution_type] -= 1
            self.distribution_counts["raw_total"] -= 1
            self.distribution_counts["total"] -= day.distribution_weight
        
        # 从确认日列表中移除（如果存在）
        if day in self.confirmation_days:
            self.confirmation_days.remove(day)
    
    def _update_stats(self, day: TradingDay) -> None:
        """更新统计信息"""
        if day.distribution_type != DistributionType.NONE:
            # 更新抛盘日计数
            self.distribution_counts[day.distribution_type] += 1
            self.distribution_counts["raw_total"] += 1
            self.distribution_counts["total"] += day.distribution_weight
    
    def apply_confirmation_offset(self) -> bool:
        """
        应用确认日抵消机制
        
        规则:
        1. 找到窗口内日期最早的、且抛盘日计数>0的那一天
        2. 将该天的抛盘日计数减1
        3. 一个确认日只能抵消1个抛盘日计数
        
        返回:
            bool: 是否成功抵消
        """
        if not self.confirmation_days:
            return False
        
        # 获取最早的确认日
        confirmation_day = min(self.confirmation_days, key=lambda x: x.date)
        
        # 找到窗口内最早的抛盘日
        for day in self.days:
            if day.distribution_weight > 0:
                # 保存原始类型，用于统计更新
                original_type = day.distribution_type
                
                # 抵消操作
                day.distribution_weight -= 1
                
                # 如果权重减为0，更新类型
                if day.distribution_weight == 0:
                    day.distribution_type = DistributionType.NONE
                
                # 更新统计 - 使用原始类型
                self.distribution_counts[original_type] -= 1
                self.distribution_counts["raw_total"] -= 1
                self.distribution_counts["total"] -= 1
                
                # 从确认日列表中移除已使用的确认日
                self.confirmation_days.remove(confirmation_day)
                
                return True
        
        return False
    
    def get_market_status(self) -> Tuple[str, int]:
        """
        获取市场状态
        
        返回:
            tuple: (状态描述, 抛盘日总数)
        """
        total = self.distribution_counts["total"]
        
        if total >= 8:
            return ("熊市状态", total)
        elif total >= 5:
            return ("承压状态", total)
        else:
            return ("正常状态", total)
    
    def get_detailed_stats(self) -> Dict:
        """获取详细统计信息"""
        return {
            "standard": self.distribution_counts[DistributionType.STANDARD],
            "special": self.distribution_counts[DistributionType.SPECIAL],
            "intraday_reversal": self.distribution_counts[DistributionType.INTRADAY_REVERSAL],
            "raw_total": self.distribution_counts["raw_total"],
            "weighted_total": self.distribution_counts["total"],
            "confirmation_days": len(self.confirmation_days),
            "window_size": len(self.days),
            "market_status": self.get_market_status()[0],
        }


class MultiIndexScanner:
    """多指数扫描器"""
    
    def __init__(self, data_access, config: Optional[Dict] = None):
        """
        初始化多指数扫描器
        
        参数:
            data_access: 数据访问对象
            config: 配置字典
        """
        self.data_access = data_access
        self.config = config or {}
        
        # 创建指数扫描器
        self.scanner = DistributionScanner(config)
        
        # 为每个指数创建窗口
        self.windows = {
            MarketIndex.CSI_ALL.value: DistributionWindow(),
            MarketIndex.CSI_300.value: DistributionWindow(),
        }
    
    def analyze_index(self, index_code: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        分析指定指数的历史数据
        
        参数:
            index_code: 指数代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        返回:
            list: 分析结果列表
        """
        # 获取指数数据
        df = self.data_access.get_index_data(index_code, start_date, end_date)
        if df.empty:
            logger.warning(f"指数 {index_code} 无数据")
            return []
        
        results = []
        
        # 按时间顺序分析
        df_sorted = df.sort_values('date').reset_index()
        
        for i in range(1, len(df_sorted)):
            current_row = df_sorted.iloc[i]
            prev_row = df_sorted.iloc[i-1]
            
            # 准备交易日数据
            day = self.scanner.prepare_trading_day(current_row, prev_row)
            
            # 分析抛盘日
            day = self.scanner.analyze_distribution_day(day)
            
            # 添加到窗口
            if index_code in self.windows:
                self.windows[index_code].add_day(day)
            
            # 转换为字典格式返回
            results.append({
                'date': day.date,
                'index_code': day.index_code,
                'change_pct': day.change_pct,
                'volume_ratio': day.volume_ratio,
                'is_flat_day': day.is_flat_day,
                'distribution_type': day.distribution_type.value,
                'distribution_weight': day.distribution_weight,
                'is_confirmation_day': day.is_confirmation_day,
                'upper_shadow_ratio': day.upper_shadow / day.body_size if day.body_size > 0 else 0,
                'intraday_high_pct': day.intraday_high_pct,
            })
        
        return results
    
    def get_combined_analysis(self) -> Dict:
        """
        获取多指数综合分析
        
        返回:
            dict: 综合分析结果
        """
        result = {}
        
        for index_code, window in self.windows.items():
            stats = window.get_detailed_stats()
            
            # 应用确认日抵消（如果需要）
            while window.confirmation_days:
                if not window.apply_confirmation_offset():
                    break
            
            result[index_code] = {
                'stats': stats,
                'market_status': window.get_market_status()[0],
                'distribution_total': window.distribution_counts["total"],
            }
        
        return result


# 使用示例
if __name__ == "__main__":
    # 测试抛盘日扫描器
    scanner = DistributionScanner()
    
    # 创建测试数据
    test_day = TradingDay(
        date="2024-01-01",
        index_code="000985",
        open=100.0,
        high=102.0,
        low=99.0,
        close=99.8,
        volume=1000000,
        change_pct=-0.002,  # -0.2%
        volume_ratio=1.5,
    )
    
    # 计算技术特征
    test_day = scanner._calculate_technical_features(test_day)
    
    # 分析抛盘日
    result = scanner.analyze_distribution_day(test_day)
    
    print(f"日期: {result.date}")
    print(f"抛盘日类型: {result.distribution_type.value}")
    print(f"抛盘日权重: {result.distribution_weight}")
    print(f"是否是确认日: {result.is_confirmation_day}")