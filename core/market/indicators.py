#!/usr/bin/env python3
# 欧奈尔市场指标计算
# 全新实现，不依赖旧系统

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class MarketDay:
    """市场日分析结果"""
    date: str
    index_code: str
    change_pct: float  # 涨跌幅（小数，如0.01表示1%）
    volume: float
    volume_ratio: float  # 成交量相对于前一日比率
    close_position: float  # 收盘价在日内位置（0-1，0.5表示中间）
    
    # 欧奈尔指标
    is_distribution_day: bool = False  # 抛盘日
    is_accumulation_day: bool = False  # 吸筹日  
    is_follow_through_day: bool = False  # 追盘日
    distribution_type: Optional[str] = None  # standard/fake_yang/intraday_reversal
    
    # 技术特征
    upper_shadow_ratio: float = 0.0  # 上影线比例
    lower_shadow_ratio: float = 0.0  # 下影线比例
    body_size: float = 0.0  # 实体大小
    gap_up: bool = False  # 向上跳空
    gap_down: bool = False  # 向下跳空


class MarketScanner:
    """欧奈尔市场扫描器"""
    
    def __init__(self, data_access=None):
        self.data_access = data_access
        self.default_index = "000985"  # 中证全指
        
        # 欧奈尔参数配置（可调整）
        self.config = {
            # 抛盘日参数
            "distribution": {
                "standard_change_threshold": -0.002,  # 跌幅≥0.2%
                "standard_volume_ratio": 1.0,  # 成交量放大
                "fake_yang_change_max": 0.001,  # 微涨≤0.1%
                "fake_yang_volume_ratio": 1.5,  # 成交量放大1.5倍
                "intraday_reversal_change_max": 0.002,  # 涨跌幅≤0.2%
                "intraday_reversal_volume_ratio": 1.2,
                "close_position_threshold": 0.5,  # 收盘在下半区
                "upper_shadow_threshold": 2.0,  # 上影线>实体2倍
            },
            # 吸筹日参数
            "accumulation": {
                "change_threshold": 0.002,  # 涨幅≥0.2%
                "volume_ratio": 1.0,  # 成交量放大
                "close_position_threshold": 0.5,  # 收盘在上半区
            },
            # 追盘日参数
            "follow_through": {
                "change_threshold": 0.012,  # 涨幅≥1.2%
                "volume_threshold": 1.0,  # 成交量放大
                "days_after_low": 4,  # 低点后至少4天
                "confirmation_days": 3,  # 需要3天确认
            },
            # 滑动窗口
            "window_days": 25,  # 25日滑动窗口
        }
    
    def analyze_index(self, index_code: str = None, start_date: str = None, end_date: str = None) -> List[MarketDay]:
        """分析指数数据，识别欧奈尔市场日"""
        if index_code is None:
            index_code = self.default_index
        
        # 获取指数数据
        df = self.data_access.get_index_data(index_code, start_date, end_date)
        if df.empty:
            logger.warning(f"指数 {index_code} 无数据")
            return []
        
        # 重置索引以便按位置访问
        df_reset = df.reset_index()
        results = []
        
        for i in range(1, len(df_reset)):  # 从第2天开始，需要前一日数据
            row = df_reset.iloc[i]
            prev_row = df_reset.iloc[i-1]
            
            # 基础计算
            change_pct = row['change_pct'] if 'change_pct' in row else (row['close'] / prev_row['close'] - 1)
            volume = row['volume']
            prev_volume = prev_row['volume']
            volume_ratio = volume / prev_volume if prev_volume > 0 else 1.0
            
            # 计算K线特征
            body_size = abs(row['close'] - row['open'])
            total_range = row['high'] - row['low']
            
            if total_range > 0:
                upper_shadow = row['high'] - max(row['open'], row['close'])
                lower_shadow = min(row['open'], row['close']) - row['low']
                upper_shadow_ratio = upper_shadow / body_size if body_size > 0 else 0
                lower_shadow_ratio = lower_shadow / body_size if body_size > 0 else 0
                close_position = (row['close'] - row['low']) / total_range
            else:
                upper_shadow_ratio = 0
                lower_shadow_ratio = 0
                close_position = 0.5
            
            # 跳空检测
            gap_up = row['low'] > prev_row['high']
            gap_down = row['high'] < prev_row['low']
            
            # 创建市场日对象
            market_day = MarketDay(
                date=row['date'].strftime('%Y-%m-%d'),
                index_code=index_code,
                change_pct=change_pct,
                volume=volume,
                volume_ratio=volume_ratio,
                close_position=close_position,
                upper_shadow_ratio=upper_shadow_ratio,
                lower_shadow_ratio=lower_shadow_ratio,
                body_size=body_size,
                gap_up=gap_up,
                gap_down=gap_down,
            )
            
            # 识别欧奈尔指标
            self._identify_distribution_day(market_day)
            self._identify_accumulation_day(market_day)
            
            results.append(market_day)
        
        # 识别追盘日（需要知道低点）
        self._identify_follow_through_days(results)
        
        return results
    
    def _identify_distribution_day(self, day: MarketDay):
        """识别抛盘日（三种类型）"""
        cfg = self.config["distribution"]
        
        # 1. 标准抛盘日：下跌且放量
        if (day.change_pct <= cfg["standard_change_threshold"] and 
            day.volume_ratio >= cfg["standard_volume_ratio"] and
            day.close_position <= cfg["close_position_threshold"]):
            day.is_distribution_day = True
            day.distribution_type = "standard"
            return
        
        # 2. 假阳线抛盘日：微涨但放量，收盘在下部
        if (0 < day.change_pct <= cfg["fake_yang_change_max"] and
            day.volume_ratio >= cfg["fake_yang_volume_ratio"] and
            day.close_position <= 0.25):  # 收盘在下部25%
            day.is_distribution_day = True
            day.distribution_type = "fake_yang"
            return
        
        # 3. 日内反转抛盘日：小幅涨跌，长上影线
        if (abs(day.change_pct) <= cfg["intraday_reversal_change_max"] and
            day.volume_ratio >= cfg["intraday_reversal_volume_ratio"] and
            day.upper_shadow_ratio >= cfg["upper_shadow_threshold"] and
            day.close_position <= 0.25):
            day.is_distribution_day = True
            day.distribution_type = "intraday_reversal"
    
    def _identify_accumulation_day(self, day: MarketDay):
        """识别吸筹日：上涨且放量"""
        cfg = self.config["accumulation"]
        
        if (day.change_pct >= cfg["change_threshold"] and
            day.volume_ratio >= cfg["volume_ratio"] and
            day.close_position >= cfg["close_position_threshold"]):
            day.is_accumulation_day = True
    
    def _identify_follow_through_days(self, days: List[MarketDay]):
        """识别追盘日：低点后至少4天，涨幅≥1.2%且放量"""
        if len(days) < 10:  # 需要足够数据
            return
        
        cfg = self.config["follow_through"]
        
        # 寻找近期低点
        for i in range(cfg["days_after_low"], len(days) - cfg["confirmation_days"]):
            # 检查前几日是否是低点
            is_low = True
            for j in range(1, cfg["days_after_low"]):
                if days[i-j].change_pct < days[i].change_pct:
                    is_low = False
                    break
            
            if not is_low:
                continue
            
            # 检查后续几天是否有追盘日
            for j in range(1, cfg["confirmation_days"] + 1):
                if i + j >= len(days):
                    break
                
                day = days[i + j]
                if (day.change_pct >= cfg["change_threshold"] and
                    day.volume_ratio >= cfg["volume_threshold"]):
                    day.is_follow_through_day = True
                    break
    
    def calculate_market_health(self, days: List[MarketDay], window_days: int = 25) -> pd.DataFrame:
        """计算市场健康度评分"""
        if not days:
            return pd.DataFrame()
        
        dates = []
        health_scores = []
        distribution_counts = []
        accumulation_counts = []
        
        for i in range(window_days - 1, len(days)):
            window = days[i-window_days+1:i+1]
            
            # 计算指标
            dist_count = sum(1 for d in window if d.is_distribution_day)
            accum_count = sum(1 for d in window if d.is_accumulation_day)
            
            # 基础健康度评分（0-100）
            # 抛盘日越多，分数越低；吸筹日越多，分数越高
            base_score = 50
            dist_penalty = min(dist_count * 8, 40)  # 每个抛盘日扣8分，最多扣40
            accum_bonus = min(accum_count * 6, 30)  # 每个吸筹日加6分，最多加30
            
            # 近期趋势（最近5天涨跌）
            recent_trend = 0
            if i >= 4:
                recent_changes = [d.change_pct for d in days[i-4:i+1]]
                recent_trend = sum(recent_changes) * 1000  # 放大到合理范围
            
            # 综合评分
            health_score = base_score - dist_penalty + accum_bonus + min(max(recent_trend, -10), 10)
            health_score = max(0, min(100, health_score))  # 限制在0-100
            
            dates.append(days[i].date)
            health_scores.append(health_score)
            distribution_counts.append(dist_count)
            accumulation_counts.append(accum_count)
        
        return pd.DataFrame({
            'date': dates,
            'health_score': health_scores,
            'distribution_count': distribution_counts,
            'accumulation_count': accumulation_counts,
        })
    
    def generate_signals(self, days: List[MarketDay]) -> List[Dict]:
        """生成市场信号"""
        signals = []
        
        if not days:
            return signals
        
        # 计算滑动窗口计数
        window_days = self.config["window_days"]
        
        for i in range(window_days - 1, len(days)):
            window = days[i-window_days+1:i+1]
            dist_count = sum(1 for d in window if d.is_distribution_day)
            accum_count = sum(1 for d in window if d.is_accumulation_day)
            
            signal = {
                'date': days[i].date,
                'distribution_count': dist_count,
                'accumulation_count': accum_count,
                'signal': 'neutral',
                'strength': 0,
                'recommendation': '持有',
            }
            
            # 抛盘日信号
            if dist_count >= 5:
                signal['signal'] = 'strong_sell'
                signal['strength'] = dist_count
                signal['recommendation'] = '大幅减仓，市场见顶确认'
            elif dist_count >= 3:
                signal['signal'] = 'moderate_sell'
                signal['strength'] = dist_count
                signal['recommendation'] = '谨慎，抛压增加'
            
            # 追盘日信号（优先级更高）
            if days[i].is_follow_through_day:
                signal['signal'] = 'strong_buy'
                signal['strength'] = 10
                signal['recommendation'] = '市场确认上升趋势，可加仓'
            
            signals.append(signal)
        
        return signals
    
    def get_summary_statistics(self, days: List[MarketDay]) -> Dict:
        """获取市场统计数据"""
        if not days:
            return {}
        
        total_days = len(days)
        dist_days = sum(1 for d in days if d.is_distribution_day)
        accum_days = sum(1 for d in days if d.is_accumulation_day)
        follow_through_days = sum(1 for d in days if d.is_follow_through_day)
        
        # 按类型统计抛盘日
        dist_by_type = {}
        for d in days:
            if d.is_distribution_day and d.distribution_type:
                dist_by_type[d.distribution_type] = dist_by_type.get(d.distribution_type, 0) + 1
        
        # 近期趋势
        recent_days = min(20, total_days)
        recent_changes = [d.change_pct for d in days[-recent_days:]]
        avg_change = sum(recent_changes) / len(recent_changes) if recent_changes else 0
        
        return {
            'total_days': total_days,
            'distribution_days': dist_days,
            'accumulation_days': accum_days,
            'follow_through_days': follow_through_days,
            'distribution_by_type': dist_by_type,
            'recent_avg_change': avg_change,
            'data_range': f"{days[0].date} 到 {days[-1].date}" if days else "无数据",
        }


# 工具函数
def analyze_market_period(start_date: str, end_date: str, index_code: str = "000985") -> Dict:
    """分析指定时间段的市场状况"""
    from data.access import get_data_access
    
    data = get_data_access()
    scanner = MarketScanner(data)
    
    days = scanner.analyze_index(index_code, start_date, end_date)
    health_df = scanner.calculate_market_health(days)
    signals = scanner.generate_signals(days)
    stats = scanner.get_summary_statistics(days)
    
    return {
        'market_days': days,
        'health_data': health_df,
        'signals': signals,
        'statistics': stats,
        'scanner': scanner,
    }


if __name__ == "__main__":
    # 测试市场扫描器
    import logging
    logging.basicConfig(level=logging.INFO)
    
    from data.access import get_data_access
    
    print("测试欧奈尔市场扫描器...")
    
    data = get_data_access()
    scanner = MarketScanner(data)
    
    # 测试最近60天数据
    latest_date = data.get_latest_trading_date()
    if latest_date:
        end_date = latest_date
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=90)).strftime('%Y-%m-%d')
        
        print(f"分析时间段: {start_date} 到 {end_date}")
        
        days = scanner.analyze_index(start_date=start_date, end_date=end_date)
        
        if days:
            print(f"分析完成，共 {len(days)} 个交易日")
            
            # 统计结果
            stats = scanner.get_summary_statistics(days)
            print(f"\n市场统计:")
            print(f"  总交易日: {stats['total_days']}")
            print(f"  抛盘日: {stats['distribution_days']}")
            print(f"  吸筹日: {stats['accumulation_days']}")
            print(f"  追盘日: {stats['follow_through_days']}")
            
            if stats['distribution_by_type']:
                print(f"  抛盘日类型分布:")
                for typ, count in stats['distribution_by_type'].items():
                    print(f"    {typ}: {count}")
            
            # 最近信号
            signals = scanner.generate_signals(days)
            if signals:
                latest_signal = signals[-1]
                print(f"\n最新信号 ({latest_signal['date']}):")
                print(f"  信号: {latest_signal['signal']}")
                print(f"  抛盘日计数: {latest_signal['distribution_count']}")
                print(f"  建议: {latest_signal['recommendation']}")
            
            # 健康度
            health_df = scanner.calculate_market_health(days)
            if not health_df.empty:
                latest_health = health_df.iloc[-1]
                print(f"\n市场健康度:")
                print(f"  日期: {latest_health['date']}")
                print(f"  健康度评分: {latest_health['health_score']:.1f}/100")
                print(f"  25日抛盘日计数: {latest_health['distribution_count']}")
        else:
            print("无市场数据")
    else:
        print("无法获取最新交易日")