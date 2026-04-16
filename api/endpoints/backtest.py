#!/usr/bin/env python3
"""
抛盘日回测API端点
支持参数化回测，用户可调整各种阈值参数
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import logging

from data.access import get_data_access
from core.market.distribution_scanner import DistributionScanner, DistributionWindow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.post("/distribution")
async def run_distribution_backtest(
    flat_day_threshold: float = Query(0.0005, description="平盘日阈值（涨跌幅绝对值<此值不计）"),
    standard_distribution_threshold: float = Query(-0.001, description="标准抛盘日跌幅阈值"),
    standard_volume_ratio: float = Query(1.05, description="标准抛盘日成交量比率（默认: 1.05，需放量5%）"),
    special_max_gain: float = Query(0.002, description="特殊抛盘日最大涨幅"),
    special_intraday_min: float = Query(0.005, description="特殊抛盘日盘中最低涨幅"),
    special_volume_ratio: float = Query(1.3, description="特殊抛盘日成交量比率"),
    special_upper_shadow_ratio: float = Query(1.5, description="特殊抛盘日上影线比率"),
    intraday_volume_ratio: float = Query(1.2, description="盘中反转成交量比率"),
    intraday_upper_shadow_ratio: float = Query(1.5, description="盘中反转上影线比率"),
    heavy_distribution_threshold: float = Query(-0.015, description="重抛盘日跌幅阈值"),
    heavy_volume_ratio: float = Query(1.0, description="重抛盘日成交量比率"),
    confirmation_day_gain: float = Query(0.015, description="确认日涨幅阈值"),
    confirmation_volume_ratio: float = Query(1.0, description="确认日成交量比率"),
    pressure_threshold: int = Query(5, description="承压状态阈值"),
    bear_threshold: int = Query(8, description="熊市状态阈值"),
    window_days: int = Query(25, description="分析天数"),
    index_code: str = Query("000985", description="指数代码"),
    data_access = Depends(get_data_access)
):
    """
    运行抛盘日参数化回测
    
    允许用户调整所有抛盘日检测参数，返回详细分析结果
    """
    try:
        # 构建配置
        config = {
            "flat_day_threshold": flat_day_threshold,
            "standard_distribution_threshold": standard_distribution_threshold,
            "standard_volume_ratio": standard_volume_ratio,
            "special_max_gain": special_max_gain,
            "special_intraday_min": special_intraday_min,
            "special_volume_ratio": special_volume_ratio,
            "special_upper_shadow_ratio": special_upper_shadow_ratio,
            "intraday_volume_ratio": intraday_volume_ratio,
            "intraday_upper_shadow_ratio": intraday_upper_shadow_ratio,
            "heavy_distribution_threshold": heavy_distribution_threshold,
            "heavy_volume_ratio": heavy_volume_ratio,
            "confirmation_day_gain": confirmation_day_gain,
            "confirmation_volume_ratio": confirmation_volume_ratio,
            "pressure_threshold": pressure_threshold,
            "bear_threshold": bear_threshold,
            "window_days": window_days,
        }
        
        # 创建扫描器
        scanner = DistributionScanner(config)
        
        # 获取最新交易日
        latest_date = data_access.get_latest_trading_date()
        if not latest_date:
            raise HTTPException(status_code=404, detail="无交易日数据")
        
        # 获取交易日列表
        trading_dates = data_access.get_trading_dates(end_date=latest_date)
        if len(trading_dates) < window_days:
            analysis_dates = trading_dates
            logger.warning(f"只有 {len(trading_dates)} 个交易日，少于请求的 {window_days} 天")
        else:
            analysis_dates = trading_dates[-window_days:]
        
        start_date = analysis_dates[0]
        end_date = analysis_dates[-1]
        
        # 获取指数数据
        df = data_access.get_index_data(index_code, start_date, end_date)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"指数 {index_code} 无数据")
        
        # 按日期排序
        df_sorted = df.sort_index().reset_index()
        
        # 分析每个交易日 - 使用DistributionWindow管理滚动窗口和抵消机制
        window = DistributionWindow(window_days=window_days)
        
        for i in range(1, len(df_sorted)):
            current = df_sorted.iloc[i]
            prev = df_sorted.iloc[i-1]
            
            # 准备交易日数据
            day = scanner.prepare_trading_day(current, prev)
            
            # 分析抛盘日
            day = scanner.analyze_distribution_day(day)
            
            # 添加到窗口（窗口会自动更新统计）
            window.add_day(day)
        
        # 应用确认日抵消机制（按时间顺序抵消最早的抛盘日）
        offset_applications = 0  # 抵消操作次数
        offset_weight_total = 0  # 抵消的权重总数
        
        while window.confirmation_days:
            # 记录抵消前的加权总数
            before_weight = window.distribution_counts["total"]
            
            # 应用抵消
            if not window.apply_confirmation_offset():
                break
                
            # 记录抵消后的加权总数变化
            after_weight = window.distribution_counts["total"]
            offset_weight_total += (before_weight - after_weight)
            offset_applications += 1
        
        # 获取窗口统计
        stats = window.get_detailed_stats()
        
        # 从窗口数据中提取详细抛盘日列表
        distribution_days = []
        heavy_count = 0
        flat_day_count = 0
        confirmation_total_count = 0  # 总共识别出的确认日数量（包括已使用的）
        
        for day in window.days:
            if day.is_flat_day:
                flat_day_count += 1
            
            if day.is_confirmation_day:
                confirmation_total_count += 1
            
            if day.distribution_type.value != "none":
                # 记录抛盘日
                dist_info = {
                    'date': day.date,
                    'type': day.distribution_type.value,
                    'weight': day.distribution_weight,
                    'change_pct': day.change_pct,
                    'volume_ratio': day.volume_ratio,
                    'is_confirmation': day.is_confirmation_day,
                    'upper_shadow_ratio': day.upper_shadow / day.body_size if day.body_size > 0 else None,
                    'intraday_high_pct': day.intraday_high_pct,
                }
                distribution_days.append(dist_info)
                
                # 统计重抛盘日
                if day.distribution_weight == 2:
                    heavy_count += 1
        
        # 根据加权总数和用户阈值计算市场状态
        weighted_total = stats['weighted_total']
        if weighted_total >= bear_threshold:
            market_status = "熊市状态"
        elif weighted_total >= pressure_threshold:
            market_status = "承压状态"
        else:
            market_status = "正常状态"
        
        # 获取指数名称
        index_name_map = {
            "000985": "中证全指",
            "000300": "沪深300",
        }
        index_name = index_name_map.get(index_code, index_code)
        
        # 返回结果
        return {
            'metadata': {
                'index_code': index_code,
                'index_name': index_name,
                'start_date': start_date,
                'end_date': end_date,
                'total_days': len(analysis_dates),
                'config': config,
            },
            'statistics': {
                'flat_days': flat_day_count,
                'standard_days': stats['standard'],
                'special_days': stats['special'],
                'intraday_reversal_days': stats['intraday_reversal'],
                'heavy_days': heavy_count,
                'confirmation_days': confirmation_total_count,
                'confirmation_days_used': offset_applications,  # 实际用于抵消的确认日数量
                'confirmation_days_remaining': confirmation_total_count - offset_applications,  # 剩余的确认日数量
                'offset_weight_total': offset_weight_total,  # 抵消的权重总数
                'raw_total': stats['raw_total'],
                'weighted_total': stats['weighted_total'],
                'market_status': market_status,
            },
            'distribution_days': distribution_days,
        }
        
    except Exception as e:
        logger.error(f"抛盘日回测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))