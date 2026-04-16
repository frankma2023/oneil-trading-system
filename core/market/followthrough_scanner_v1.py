#!/usr/bin/env python3
# 欧奈尔追盘日扫描器
# 2026-04-14 开发

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class FollowThroughType(Enum):
    """追盘日类型枚举"""
    NONE = "none"                 # 无追盘日
    STANDARD = "standard"         # 标准追盘日
    STRONG = "strong"             # 强势追盘日（涨幅更大/量能更强）


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
    
    # 追盘日特征
    followthrough_type: FollowThroughType = FollowThroughType.NONE
    followthrough_strength: int = 0      # 追盘日强度（1-3）
    is_confirmed: bool = False           # 是否已确认（后续交易日验证）
    
    # 上下文信息
    days_since_attempt: int = 0          # 距离反弹尝试日的天数
    attempt_day_date: Optional[str] = None  # 反弹尝试日日期
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'date': self.date,
            'index_code': self.index_code,
            'change_pct': self.change_pct,
            'volume_ratio': self.volume_ratio,
            'followthrough_type': self.followthrough_type.value,
            'followthrough_strength': self.followthrough_strength,
            'is_confirmed': self.is_confirmed,
            'days_since_attempt': self.days_since_attempt,
            'attempt_day_date': self.attempt_day_date,
        }


class FollowThroughScanner:
    """追盘日扫描器"""
    
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
            # 市场状态判断
            'bear_market_threshold': 8,      # 熊市状态阈值（加权抛盘日）
            'pressure_market_threshold': 5,  # 承压状态阈值
            
            # 反弹尝试定义
            'attempt_day_min_gain': 0.005,   # 反弹尝试日最小涨幅（0.5%）
            'attempt_day_min_volume_ratio': 0.9,  # 反弹尝试日最小成交量比率
            
            # 追盘日定义
            'followthrough_min_gain': 0.015,      # 追盘日最小涨幅（1.5%）
            'followthrough_min_volume_ratio': 1.0,  # 追盘日最小成交量比率
            'strong_followthrough_gain': 0.025,   # 强势追盘日最小涨幅（2.5%）
            'strong_followthrough_volume_ratio': 1.2,  # 强势追盘日最小成交量比率
            
            # 时间窗口
            'min_days_since_attempt': 4,     # 距离反弹尝试日的最小天数
            'max_days_since_attempt': 7,     # 距离反弹尝试日的最大天数
            
            # 确认规则
            'confirmation_days_window': 3,   # 确认窗口天数（追盘日后几个交易日验证）
            'confirmation_min_gain': 0.002,  # 确认日最小涨幅（0.2%）
        }
    
    def prepare_trading_day(self, current_row: pd.Series, prev_row: pd.Series) -> FollowThroughDay:
        """
        准备交易日数据
        
        参数:
            current_row: 当前交易日数据
            prev_row: 前一交易日数据
            
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
        
        return day
    
    def analyze_followthrough_day(self, day: FollowThroughDay, 
                                  market_status: str,
                                  attempt_day_date: Optional[str] = None,
                                  days_since_attempt: int = 0) -> FollowThroughDay:
        """
        分析是否为追盘日
        
        参数:
            day: 交易日对象
            market_status: 市场状态（'熊市状态', '承压状态', '正常状态'）
            attempt_day_date: 反弹尝试日日期
            days_since_attempt: 距离反弹尝试日的天数
            
        返回:
            更新后的交易日对象
        """
        # 设置上下文信息
        day.attempt_day_date = attempt_day_date
        day.days_since_attempt = days_since_attempt
        
        # 只有在熊市或承压状态下才分析追盘日
        if market_status not in ['熊市状态', '承压状态']:
            day.followthrough_type = FollowThroughType.NONE
            return day
        
        # 检查时间窗口
        if days_since_attempt < self.config['min_days_since_attempt']:
            day.followthrough_type = FollowThroughType.NONE
            return day
        
        if days_since_attempt > self.config['max_days_since_attempt']:
            day.followthrough_type = FollowThroughType.NONE
            return day
        
        # 检查追盘日基本条件
        if day.change_pct < self.config['followthrough_min_gain']:
            day.followthrough_type = FollowThroughType.NONE
            return day
        
        if day.volume_ratio < self.config['followthrough_min_volume_ratio']:
            day.followthrough_type = FollowThroughType.NONE
            return day
        
        # 判断追盘日类型
        if (day.change_pct >= self.config['strong_followthrough_gain'] and 
            day.volume_ratio >= self.config['strong_followthrough_volume_ratio']):
            day.followthrough_type = FollowThroughType.STRONG
            day.followthrough_strength = 3  # 最高强度
        else:
            day.followthrough_type = FollowThroughType.STANDARD
            # 根据涨幅和量能计算强度（1-2）
            gain_ratio = day.change_pct / self.config['followthrough_min_gain']
            volume_ratio = day.volume_ratio / self.config['followthrough_min_volume_ratio']
            strength = min(2, int((gain_ratio + volume_ratio) / 2))
            day.followthrough_strength = max(1, strength)
        
        return day
    
    def find_attempt_day(self, days: List[FollowThroughDay], 
                         start_index: int = 0) -> Optional[Tuple[int, str]]:
        """
        寻找反弹尝试日
        
        参数:
            days: 交易日列表（按日期升序排列）
            start_index: 开始搜索的索引
            
        返回:
            tuple: (索引, 日期) 或 None
        """
        for i in range(start_index, len(days)):
            day = days[i]
            
            # 检查是否为反弹尝试日
            if (day.change_pct >= self.config['attempt_day_min_gain'] and
                day.volume_ratio >= self.config['attempt_day_min_volume_ratio']):
                return i, day.date
        
        return None
    
    def scan_followthrough_days(self, days: List[FollowThroughDay], 
                                market_status_history: List[Tuple[str, str]]) -> List[FollowThroughDay]:
        """
        扫描追盘日
        
        参数:
            days: 交易日列表（按日期升序排列）
            market_status_history: 市场状态历史列表[(日期, 状态)]
            
        返回:
            更新后的交易日列表
        """
        if len(days) < self.config['max_days_since_attempt'] + 1:
            return days
        
        # 创建市场状态字典
        status_dict = {date: status for date, status in market_status_history}
        
        # 寻找所有反弹尝试日
        attempt_indices = []
        i = 0
        while i < len(days):
            result = self.find_attempt_day(days, i)
            if result is None:
                break
            attempt_idx, attempt_date = result
            attempt_indices.append(attempt_idx)
            i = attempt_idx + 1
        
        # 对每个反弹尝试日，检查后续的追盘日
        for attempt_idx in attempt_indices:
            attempt_date = days[attempt_idx].date
            
            # 检查反弹尝试日时的市场状态
            if attempt_date not in status_dict:
                continue
            
            market_status = status_dict[attempt_date]
            
            # 只有熊市或承压状态下的反弹尝试才有意义
            if market_status not in ['熊市状态', '承压状态']:
                continue
            
            # 检查后续交易日（第4-7天）
            for offset in range(self.config['min_days_since_attempt'], 
                              self.config['max_days_since_attempt'] + 1):
                followthrough_idx = attempt_idx + offset
                
                if followthrough_idx >= len(days):
                    break
                
                day = days[followthrough_idx]
                
                # 检查追盘日
                day = self.analyze_followthrough_day(
                    day, 
                    market_status, 
                    attempt_date, 
                    offset
                )
                
                # 更新列表
                days[followthrough_idx] = day
        
        return days
    
    def confirm_followthrough_days(self, days: List[FollowThroughDay]) -> List[FollowThroughDay]:
        """
        确认追盘日（后续交易日验证）
        
        参数:
            days: 交易日列表
            
        返回:
            更新后的交易日列表
        """
        window = self.config['confirmation_days_window']
        
        for i in range(len(days)):
            day = days[i]
            
            if day.followthrough_type == FollowThroughType.NONE:
                continue
            
            # 检查后续几个交易日是否验证
            confirmed = False
            for j in range(1, min(window + 1, len(days) - i)):
                next_day = days[i + j]
                
                # 如果后续交易日上涨，则确认追盘日有效
                if next_day.change_pct >= self.config['confirmation_min_gain']:
                    confirmed = True
                    break
            
            day.is_confirmed = confirmed
        
        return days


class FollowThroughWindow:
    """追盘日窗口分析器"""
    
    def __init__(self, window_days: int = 50):
        """
        初始化追盘日窗口
        
        参数:
            window_days: 窗口天数
        """
        self.window_days = window_days
        self.days: List[FollowThroughDay] = []
        
    def add_day(self, day: FollowThroughDay):
        """添加交易日到窗口"""
        self.days.append(day)
        
        # 保持窗口大小
        if len(self.days) > self.window_days:
            self.days = self.days[-self.window_days:]
    
    def get_followthrough_stats(self) -> Dict:
        """获取追盘日统计信息"""
        total_days = len(self.days)
        followthrough_days = [d for d in self.days if d.followthrough_type != FollowThroughType.NONE]
        confirmed_days = [d for d in followthrough_days if d.is_confirmed]
        
        # 按类型统计
        standard_days = [d for d in followthrough_days if d.followthrough_type == FollowThroughType.STANDARD]
        strong_days = [d for d in followthrough_days if d.followthrough_type == FollowThroughType.STRONG]
        
        return {
            'total_days': total_days,
            'followthrough_days_count': len(followthrough_days),
            'confirmed_days_count': len(confirmed_days),
            'standard_days_count': len(standard_days),
            'strong_days_count': len(strong_days),
            'confirmation_rate': len(confirmed_days) / len(followthrough_days) if followthrough_days else 0,
            'latest_followthrough': followthrough_days[-1].date if followthrough_days else None,
            'latest_confirmed': confirmed_days[-1].date if confirmed_days else None,
        }
    
    def get_followthrough_days(self) -> List[Dict]:
        """获取所有追盘日详细信息"""
        followthrough_days = [d for d in self.days if d.followthrough_type != FollowThroughType.NONE]
        return [d.to_dict() for d in followthrough_days]