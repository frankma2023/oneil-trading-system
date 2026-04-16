#!/usr/bin/env python3
# 欧奈尔追盘日扫描器 v2
# 严格按照《追盘日定义.md》和对齐的量化规则实现
# 2026-04-14 全新开发

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class FollowThroughSignal(Enum):
    """追盘日信号状态枚举"""
    NONE = "none"                 # 无信号
    ACTIVE = "active"             # 有效追盘日信号
    FAILED = "failed"             # 追盘日已失效
    EXPIRED = "expired"           # 追盘日已过期（超过25日）


class FollowThroughType(Enum):
    """追盘日类型枚举"""
    STANDARD = "standard"         # 标准追盘日
    STRONG = "strong"             # 强势追盘日（进阶条件）


@dataclass
class FollowThroughDay:
    """追盘日数据"""
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
    avg_volume_10: float = 0.0   # 前10日均量
    
    # 追盘日特征
    is_followthrough: bool = False          # 是否为追盘日
    followthrough_type: Optional[FollowThroughType] = None  # 追盘日类型
    followthrough_strength: int = 0         # 追盘日强度（1-3）
    dynamic_threshold: float = 0.015        # 动态阈值（默认1.5%）
    
    # 反弹尝试上下文
    is_attempt_start: bool = False          # 是否为反弹尝试起点
    attempt_start_date: Optional[str] = None  # 反弹尝试起点日期
    days_since_attempt: int = 0             # 距离反弹尝试起点的天数
    
    # 技术特征
    position_in_range: float = 0.0          # 收盘价在区间中的位置 (close-low)/(high-low)
    upper_shadow_ratio: float = 0.0         # 上影线/实体比率
    
    # 失效状态
    is_failed: bool = False                 # 是否已失效
    failure_reason: Optional[str] = None    # 失效原因
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'date': self.date,
            'index_code': self.index_code,
            'change_pct': self.change_pct,
            'volume_ratio': self.volume_ratio,
            'avg_volume_10': self.avg_volume_10,
            'is_followthrough': self.is_followthrough,
            'followthrough_type': self.followthrough_type.value if self.followthrough_type else None,
            'followthrough_strength': self.followthrough_strength,
            'dynamic_threshold': self.dynamic_threshold,
            'is_attempt_start': self.is_attempt_start,
            'attempt_start_date': self.attempt_start_date,
            'days_since_attempt': self.days_since_attempt,
            'position_in_range': self.position_in_range,
            'upper_shadow_ratio': self.upper_shadow_ratio,
            'is_failed': self.is_failed,
            'failure_reason': self.failure_reason,
        }


class FollowThroughScanner:
    """追盘日扫描器（v2）"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化追盘日扫描器
        
        参数:
            config: 配置字典，包含追盘日识别参数
        """
        self.config = config or self.get_default_config()
        
    @staticmethod
    def get_default_config() -> Dict:
        """获取默认配置"""
        return {
            # 反弹尝试起点定义
            'attempt_min_gain': 0.001,               # 起点最小涨幅（0.1%）
            'attempt_min_position': 0.5,             # 起点最小区间位置（50%分位）
            
            # 追盘日定义 - 核心条件
            'min_days_since_attempt': 4,            # 最小天数（第4天）
            'max_days_since_attempt': 7,            # 最大天数（第7天，可配置至10）
            
            # 价格条件
            'default_gain_threshold': 0.015,        # 默认涨幅阈值（1.5%）
            'dynamic_percentile': 90,               # 动态阈值百分位数（90%）
            'dynamic_lookback_days': 20,            # 动态阈值回看天数
            
            # 成交量条件
            'volume_ma_days': 10,                   # 成交量均线天数
            'volume_ratio_to_ma': 1.1,              # 成交量对均量比率
            'volume_ratio_to_prev': 1.0,            # 成交量对前一日比率
            
            # 进阶条件（提高信号可靠性）
            'strong_gain_threshold': 0.025,         # 强势追盘日最小涨幅（2.5%）
            'strong_volume_ratio_to_ma': 1.2,       # 强势追盘日成交量对均量比率
            'min_position_in_range': 0.5,           # 最小区间位置（50%分位）
            'max_upper_shadow_ratio': 2.0,          # 最大上影线/实体比率
            
            # 失效条件
            'stop_loss_days': 5,                    # 止损观察期（5日）
            'distribution_days_threshold': 4,       # 抛盘日累积阈值（10日内）
            'distribution_lookback_days': 10,       # 抛盘日累积观察期
            'negation_min_gain': -0.01,             # 否定日最小跌幅（-1.0%）
            'negation_consecutive_days': 2,         # 连续否定日数量
            'negation_volume_ratio_to_ma': 1.1,     # 否定日成交量对均量比率
            
            # 其他
            'low_lookback_days': 25,                # 低点回看天数（过去25个交易日）
            'max_attempt_duration': 25,             # 最大尝试持续时间（25个交易日）
        }
    
    def prepare_trading_day(self, 
                           current_row: pd.Series, 
                           prev_row: pd.Series,
                           volume_ma_10: float = None) -> FollowThroughDay:
        """
        准备交易日数据
        
        参数:
            current_row: 当前交易日数据
            prev_row: 前一交易日数据
            volume_ma_10: 前10日均量（可选）
            
        返回:
            FollowThroughDay: 准备好的交易日对象
        """
        day = FollowThroughDay(
            date=str(current_row['date']),
            index_code=current_row.get('index_code', '000985'),
            open=float(current_row['open']),
            high=float(current_row['high']),
            low=float(current_row['low']),
            close=float(current_row['close']),
            volume=float(current_row['volume']),
        )
        
        # 计算涨跌幅
        if prev_row['close'] > 0:
            day.change_pct = (day.close - prev_row['close']) / prev_row['close']
        else:
            day.change_pct = 0.0
        
        # 计算成交量比率
        if prev_row['volume'] > 0:
            day.volume_ratio = day.volume / prev_row['volume']
        else:
            day.volume_ratio = 1.0
        
        # 设置均量
        if volume_ma_10 is not None:
            day.avg_volume_10 = volume_ma_10
        
        # 计算技术特征
        high_low_range = day.high - day.low
        if high_low_range > 0:
            day.position_in_range = (day.close - day.low) / high_low_range
        
        body_size = abs(day.close - day.open)
        if body_size > 0:
            upper_shadow = day.high - max(day.open, day.close)
            day.upper_shadow_ratio = upper_shadow / body_size
        
        return day
    
    def is_attempt_start(self, day: FollowThroughDay, prev_day: FollowThroughDay) -> bool:
        """
        判断是否为反弹尝试起点
        
        规则：
        1. 涨幅 ≥ 0.1% （优先条件）
        2. 或者收盘价位于区间上半部（>50%分位）（备选条件）
        """
        # 检查是否创过去25日最低收盘价（需要在外部计算）
        
        # 规则1：涨幅 ≥ 0.1%
        if day.change_pct >= self.config['attempt_min_gain']:
            return True
        
        # 规则2：收盘价位于区间上半部（>50%分位）
        if day.position_in_range >= self.config['attempt_min_position']:
            return True
        
        return False
    
    def calculate_dynamic_threshold(self, recent_returns: List[float]) -> float:
        """
        计算动态阈值（过去20日涨幅的90%分位数）
        
        参数:
            recent_returns: 最近N日的涨跌幅列表
            
        返回:
            float: 动态阈值（小数）
        """
        if not recent_returns:
            return self.config['default_gain_threshold']
        
        # 计算百分位数
        threshold = np.percentile(recent_returns, self.config['dynamic_percentile'])
        
        # 确保阈值不低于默认值
        return max(threshold, self.config['default_gain_threshold'])
    
    def check_followthrough_conditions(self, day: FollowThroughDay) -> Tuple[bool, Optional[FollowThroughType], int]:
        """
        检查是否满足追盘日条件
        
        返回:
            tuple: (是否追盘日, 类型, 强度)
        """
        # 1. 时间窗口检查（在外部处理）
        
        # 2. 价格条件
        if day.change_pct < day.dynamic_threshold:
            return False, None, 0
        
        # 3. 成交量条件
        if day.avg_volume_10 <= 0:
            return False, None, 0
        
        # 成交量 > 前10日均量 × 1.1
        if day.volume <= day.avg_volume_10 * self.config['volume_ratio_to_ma']:
            return False, None, 0
        
        # 成交量 > 前一日成交量
        if day.volume_ratio < self.config['volume_ratio_to_prev']:
            return False, None, 0
        
        # 4. 进阶条件判断（强势追盘日）
        is_strong = False
        strength = 1  # 默认强度
        
        # 检查强势追盘日条件
        if (day.change_pct >= self.config['strong_gain_threshold'] and
            day.volume >= day.avg_volume_10 * self.config['strong_volume_ratio_to_ma']):
            is_strong = True
            strength = 3  # 最高强度
        else:
            # 计算标准追盘日强度（基于涨幅和量能）
            gain_ratio = day.change_pct / day.dynamic_threshold
            volume_ratio = day.volume / (day.avg_volume_10 * self.config['volume_ratio_to_ma'])
            strength_score = (gain_ratio + volume_ratio) / 2
            strength = min(2, max(1, int(strength_score * 2)))
        
        # 5. 额外形态条件（可选）
        # 收盘价位于区间上半部
        if day.position_in_range < self.config['min_position_in_range']:
            strength = max(1, strength - 1)  # 降低强度
        
        # 上影线不宜过长
        if day.upper_shadow_ratio > self.config['max_upper_shadow_ratio']:
            strength = max(1, strength - 1)  # 降低强度
        
        followthrough_type = FollowThroughType.STRONG if is_strong else FollowThroughType.STANDARD
        
        return True, followthrough_type, strength
    
    def check_failure_conditions(self, 
                                followthrough_day: FollowThroughDay,
                                subsequent_days: List[FollowThroughDay],
                                distribution_counts: List[int]) -> Tuple[bool, Optional[str]]:
        """
        检查追盘日是否失效
        
        参数:
            followthrough_day: 追盘日对象
            subsequent_days: 追盘日后的交易日列表（按日期升序）
            distribution_counts: 追盘日后每日的抛盘日累积数量列表
            
        返回:
            tuple: (是否失效, 失效原因)
        """
        stop_loss_price = followthrough_day.low
        
        for i, day in enumerate(subsequent_days):
            days_since_followthrough = i + 1
            
            # 条件1：跌破止损价（5日内）
            if days_since_followthrough <= self.config['stop_loss_days']:
                if day.close < stop_loss_price:
                    return True, f"第{days_since_followthrough}天跌破止损价"
            
            # 条件2：抛盘日累积过多（10日内）
            if days_since_followthrough <= self.config['distribution_lookback_days']:
                if distribution_counts[i] >= self.config['distribution_days_threshold']:
                    return True, f"第{days_since_followthrough}天抛盘日累积{distribution_counts[i]}个"
            
            # 条件3：连续2个强力否定日
            if days_since_followthrough >= 2:
                # 检查前2个交易日是否均为否定日
                if i >= 1:
                    prev_day = subsequent_days[i-1]
                    prev_negation = self.is_negation_day(prev_day)
                    curr_negation = self.is_negation_day(day)
                    
                    if prev_negation and curr_negation:
                        return True, f"第{days_since_followthrough-1}-{days_since_followthrough}天连续强力否定"
        
        return False, None
    
    def is_negation_day(self, day: FollowThroughDay) -> bool:
        """判断是否为强力否定日"""
        # 跌幅 ≥ 1.0%
        if day.change_pct > self.config['negation_min_gain']:
            return False
        
        # 放量条件：成交量 > 前10日均量 × 1.1
        if day.volume <= day.avg_volume_10 * self.config['negation_volume_ratio_to_ma']:
            return False
        
        # 成交量 > 前一日成交量
        if day.volume_ratio < self.config['volume_ratio_to_prev']:
            return False
        
        return True
    
    def find_lowest_close(self, days: List[FollowThroughDay], lookback: int = 25) -> Optional[str]:
        """
        寻找过去N个交易日的最低收盘价日期
        
        返回:
            str: 最低收盘价日期，或None
        """
        if len(days) < lookback:
            return None
        
        # 取最近lookback天
        recent_days = days[-lookback:]
        
        # 找到最低收盘价
        min_close = float('inf')
        min_date = None
        
        for day in recent_days:
            if day.close < min_close:
                min_close = day.close
                min_date = day.date
        
        return min_date


class FollowThroughWindow:
    """追盘日窗口分析器"""
    
    def __init__(self, window_days: int = 100):
        """
        初始化追盘日窗口
        
        参数:
            window_days: 窗口天数
        """
        self.window_days = window_days
        self.days: List[FollowThroughDay] = []
        self.current_attempt_start: Optional[str] = None
        self.current_attempt_days: int = 0
        self.active_followthrough: Optional[FollowThroughDay] = None
        self.followthrough_history: List[FollowThroughDay] = []
        
    def add_day(self, day: FollowThroughDay):
        """添加交易日到窗口"""
        self.days.append(day)
        
        # 保持窗口大小
        if len(self.days) > self.window_days:
            self.days = self.days[-self.window_days:]
    
    def scan_followthrough(self, scanner: FollowThroughScanner) -> List[FollowThroughDay]:
        """
        扫描追盘日信号
        
        参数:
            scanner: 追盘日扫描器
            
        返回:
            更新后的交易日列表
        """
        if len(self.days) < scanner.config['low_lookback_days']:
            return self.days
        
        # 重置当前状态
        self.current_attempt_start = None
        self.current_attempt_days = 0
        
        # 寻找最低收盘价
        lowest_date = scanner.find_lowest_close(self.days, scanner.config['low_lookback_days'])
        
        if lowest_date is None:
            return self.days
        
        # 找到最低收盘价后的第一个反弹尝试起点
        found_attempt = False
        attempt_start_index = -1
        
        for i, day in enumerate(self.days):
            if day.date <= lowest_date:
                continue
            
            # 检查是否为反弹尝试起点
            if i == 0:
                continue  # 需要前一日数据
            
            prev_day = self.days[i-1]
            if scanner.is_attempt_start(day, prev_day):
                self.current_attempt_start = day.date
                self.current_attempt_days = 1
                day.is_attempt_start = True
                day.attempt_start_date = day.date
                found_attempt = True
                attempt_start_index = i
                break
        
        if not found_attempt:
            return self.days
        
        # 从尝试起点开始扫描后续交易日
        for i in range(attempt_start_index + 1, len(self.days)):
            current_day = self.days[i]
            days_since_attempt = i - attempt_start_index + 1
            
            # 设置上下文信息
            current_day.attempt_start_date = self.current_attempt_start
            current_day.days_since_attempt = days_since_attempt
            
            # 检查时间窗口
            if (days_since_attempt < scanner.config['min_days_since_attempt'] or 
                days_since_attempt > scanner.config['max_days_since_attempt']):
                continue
            
            # 计算动态阈值（使用过去20日涨幅）
            lookback_start = max(0, i - scanner.config['dynamic_lookback_days'])
            recent_returns = [d.change_pct for d in self.days[lookback_start:i]]
            current_day.dynamic_threshold = scanner.calculate_dynamic_threshold(recent_returns)
            
            # 检查追盘日条件
            is_followthrough, followthrough_type, strength = scanner.check_followthrough_conditions(current_day)
            
            if is_followthrough:
                current_day.is_followthrough = True
                current_day.followthrough_type = followthrough_type
                current_day.followthrough_strength = strength
                
                # 如果还没有活跃的追盘日，设置为活跃
                if self.active_followthrough is None:
                    self.active_followthrough = current_day
                    self.followthrough_history.append(current_day)
                
                # 更新列表
                self.days[i] = current_day
        
        return self.days
    
    def update_failure_status(self, scanner: FollowThroughScanner, distribution_counts: List[int]):
        """更新失效状态"""
        if self.active_followthrough is None:
            return
        
        # 找到追盘日后的交易日
        followthrough_index = -1
        for i, day in enumerate(self.days):
            if day.date == self.active_followthrough.date:
                followthrough_index = i
                break
        
        if followthrough_index == -1:
            return
        
        # 获取后续交易日
        subsequent_days = self.days[followthrough_index + 1:]
        
        # 检查失效条件
        is_failed, reason = scanner.check_failure_conditions(
            self.active_followthrough, 
            subsequent_days,
            distribution_counts[:len(subsequent_days)] if distribution_counts else []
        )
        
        if is_failed:
            self.active_followthrough.is_failed = True
            self.active_followthrough.failure_reason = reason
            self.active_followthrough = None
    
    def get_current_status(self) -> Dict:
        """获取当前状态"""
        if self.active_followthrough is None:
            return {
                'signal': FollowThroughSignal.NONE.value,
                'active_followthrough': None,
                'attempt_start': self.current_attempt_start,
                'attempt_days': self.current_attempt_days,
                'followthrough_count': len(self.followthrough_history),
            }
        
        signal = FollowThroughSignal.ACTIVE
        if self.active_followthrough.is_failed:
            signal = FollowThroughSignal.FAILED
        
        return {
            'signal': signal.value,
            'active_followthrough': self.active_followthrough.to_dict(),
            'attempt_start': self.current_attempt_start,
            'attempt_days': self.current_attempt_days,
            'followthrough_count': len(self.followthrough_history),
        }