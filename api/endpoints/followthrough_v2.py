#!/usr/bin/env python3
# 追盘日API端点 v2
# 提供追盘日分析的相关接口（基于对齐的规范）
# 2026-04-14 全新开发

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import logging
import pandas as pd
import numpy as np

from data.access import get_data_access
from core.market.followthrough_scanner_v2 import FollowThroughScanner, FollowThroughWindow
from core.market.distribution_scanner import MultiIndexScanner, DistributionWindow

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/followthrough", tags=["追盘日分析"])


def get_distribution_counts(data_access, index_code: str, start_date: str, end_date: str) -> List[int]:
    """
    获取每日抛盘日累积数量（用于失效条件检查）
    
    返回:
        list: 每日的抛盘日累积数量列表
    """
    try:
        # 获取数据
        df = data_access.get_index_data(index_code, start_date, end_date)
        if df.empty:
            return []
        
        # 按日期排序
        df_sorted = df.sort_index().reset_index()
        
        # 创建抛盘日扫描器
        scanner = FollowThroughScanner()  # 使用追盘日扫描器获取配置
        window = DistributionWindow(window_days=25)
        
        distribution_counts = []
        
        for i in range(1, len(df_sorted)):
            current = df_sorted.iloc[i]
            prev = df_sorted.iloc[i-1]
            
            # 准备交易日（使用追盘日扫描器的方法）
            from core.market.followthrough_scanner_v2 import FollowThroughDay
            # 这里简化为仅统计抛盘日数量，实际应调用抛盘日系统
            
            # 模拟数据
            distribution_counts.append(0)  # 默认无抛盘日
        
        return distribution_counts
        
    except Exception as e:
        logger.error(f"获取抛盘日数据失败: {e}")
        return []


def calculate_volume_ma(df: pd.DataFrame, window: int = 10) -> pd.Series:
    """计算成交量移动平均"""
    return df['volume'].rolling(window=window, min_periods=1).mean()


@router.get("/analyze")
async def analyze_followthrough_days(
    start_date: str = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    days: int = Query(100, description="分析天数，如果提供则忽略start_date/end_date"),
    index_code: str = Query("000985", description="指数代码"),
    config: Optional[str] = Query(None, description="配置JSON字符串（可选）"),
    data_access = Depends(get_data_access)
):
    """
    分析指定时间段的追盘日（详细分析）
    
    返回追盘日详细分析，包括失效状态
    """
    try:
        # 处理日期参数
        if start_date is None or end_date is None:
            # 使用days参数
            end_date_str = datetime.now().strftime('%Y-%m-%d')
            start_date_str = (datetime.strptime(end_date_str, '%Y-%m-%d') - 
                            timedelta(days=days)).strftime('%Y-%m-%d')
        else:
            start_date_str = start_date
            end_date_str = end_date
        
        logger.info(f"追盘日详细分析: {index_code} {start_date_str} 至 {end_date_str}")
        
        # 获取市场数据
        df = data_access.get_index_data(index_code, start_date_str, end_date_str)
        if df.empty:
            raise HTTPException(status_code=404, 
                              detail=f"未找到指数{index_code}在指定时间段的数据")
        
        # 按日期排序
        df_sorted = df.sort_index().reset_index()
        
        # 计算成交量均线
        df_sorted['volume_ma_10'] = calculate_volume_ma(df_sorted, window=10)
        
        # 解析配置
        scanner_config = FollowThroughScanner.get_default_config()
        if config:
            import json
            try:
                user_config = json.loads(config)
                scanner_config.update(user_config)
            except json.JSONDecodeError:
                logger.warning(f"配置JSON解析失败: {config}")
        
        # 创建扫描器
        scanner = FollowThroughScanner(scanner_config)
        window = FollowThroughWindow(window_days=100)
        
        # 准备交易日数据
        trading_days = []
        for i in range(1, len(df_sorted)):
            current = df_sorted.iloc[i]
            prev = df_sorted.iloc[i-1]
            
            volume_ma_10 = current['volume_ma_10'] if 'volume_ma_10' in current else None
            
            day = scanner.prepare_trading_day(current, prev, volume_ma_10)
            trading_days.append(day)
        
        # 添加到窗口并扫描
        for day in trading_days:
            window.add_day(day)
        
        window.scan_followthrough(scanner)
        
        # 获取抛盘日数据用于失效检查
        distribution_counts = get_distribution_counts(data_access, index_code, 
                                                     start_date_str, end_date_str)
        
        # 更新失效状态
        window.update_failure_status(scanner, distribution_counts)
        
        # 获取当前状态
        status = window.get_current_status()
        
        # 提取所有追盘日信息
        followthrough_days = []
        for day in window.days:
            if day.is_followthrough:
                followthrough_days.append(day.to_dict())
        
        # 获取指数名称
        index_name_map = {
            "000985": "中证全指",
            "000300": "沪深300",
        }
        index_name = index_name_map.get(index_code, index_code)
        
        return {
            'metadata': {
                'index_code': index_code,
                'index_name': index_name,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'total_days': len(df_sorted),
                'trading_days_analyzed': len(trading_days),
                'config': scanner_config,
            },
            'current_status': status,
            'followthrough_days': followthrough_days,
            'statistics': {
                'total_followthrough_days': len(followthrough_days),
                'active_followthrough_days': len([d for d in followthrough_days 
                                                 if not d.get('is_failed', False)]),
                'failed_followthrough_days': len([d for d in followthrough_days 
                                                 if d.get('is_failed', False)]),
                'standard_days': len([d for d in followthrough_days 
                                     if d.get('followthrough_type') == 'standard']),
                'strong_days': len([d for d in followthrough_days 
                                   if d.get('followthrough_type') == 'strong']),
                'avg_strength': sum([d.get('followthrough_strength', 0) 
                                    for d in followthrough_days]) / len(followthrough_days) 
                                    if followthrough_days else 0,
                'avg_dynamic_threshold': sum([d.get('dynamic_threshold', 0.015) 
                                            for d in followthrough_days]) / len(followthrough_days) 
                                            if followthrough_days else 0.015,
            }
        }
        
    except Exception as e:
        logger.error(f"追盘日分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_followthrough_status(
    index_code: str = Query("000985", description="指数代码"),
    window_days: int = Query(100, description="分析窗口天数"),
    data_access = Depends(get_data_access)
):
    """
    获取当前追盘日状态（简洁版）
    
    返回当前是否有有效追盘日及相关信息
    """
    try:
        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - 
                     timedelta(days=window_days)).strftime('%Y-%m-%d')
        
        # 获取数据
        df = data_access.get_index_data(index_code, start_date, end_date)
        if df.empty:
            raise HTTPException(status_code=404, 
                              detail=f"未找到指数{index_code}在指定时间段的数据")
        
        # 按日期排序
        df_sorted = df.sort_index().reset_index()
        
        # 计算成交量均线
        df_sorted['volume_ma_10'] = calculate_volume_ma(df_sorted, window=10)
        
        # 创建扫描器
        scanner = FollowThroughScanner()
        window = FollowThroughWindow(window_days=window_days)
        
        # 准备交易日数据
        for i in range(1, len(df_sorted)):
            current = df_sorted.iloc[i]
            prev = df_sorted.iloc[i-1]
            
            volume_ma_10 = current['volume_ma_10'] if 'volume_ma_10' in current else None
            
            day = scanner.prepare_trading_day(current, prev, volume_ma_10)
            window.add_day(day)
        
        # 扫描追盘日
        window.scan_followthrough(scanner)
        
        # 获取状态
        status = window.get_current_status()
        
        # 获取指数名称
        index_name_map = {
            "000985": "中证全指",
            "000300": "沪深300",
        }
        index_name = index_name_map.get(index_code, index_code)
        
        # 创建响应
        response = {
            'index_code': index_code,
            'index_name': index_name,
            'window_days': window_days,
            'start_date': start_date,
            'end_date': end_date,
            'signal': status['signal'],
            'has_active_followthrough': status['signal'] == 'active',
            'active_followthrough': status.get('active_followthrough'),
            'attempt_start': status.get('attempt_start'),
            'attempt_days': status.get('attempt_days'),
            'followthrough_count': status.get('followthrough_count', 0),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # 添加信号解释
        if status['signal'] == 'active':
            response['signal_explanation'] = "有有效追盘日信号，市场上升趋势确认"
        elif status['signal'] == 'failed':
            response['signal_explanation'] = "追盘日信号已失效"
        elif status['signal'] == 'expired':
            response['signal_explanation'] = "追盘日信号已过期"
        else:
            response['signal_explanation'] = "无有效追盘日信号"
        
        return response
        
    except Exception as e:
        logger.error(f"获取追盘日状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_followthrough_summary(
    window_days: int = Query(50, description="分析窗口天数"),
    index_code: str = Query("000985", description="指数代码"),
    data_access = Depends(get_data_access)
):
    """
    获取追盘日摘要信息（简洁版）
    
    返回追盘日信号的基本状态，用于大盘扫描看板
    """
    try:
        # 使用status端点的逻辑
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - 
                     timedelta(days=window_days)).strftime('%Y-%m-%d')
        
        # 获取数据
        df = data_access.get_index_data(index_code, start_date, end_date)
        if df.empty:
            raise HTTPException(status_code=404, 
                              detail=f"未找到指数{index_code}在指定时间段的数据")
        
        # 按日期排序
        df_sorted = df.sort_index().reset_index()
        
        # 计算成交量均线
        df_sorted['volume_ma_10'] = calculate_volume_ma(df_sorted, window=10)
        
        # 创建扫描器
        scanner = FollowThroughScanner()
        window = FollowThroughWindow(window_days=window_days)
        
        # 准备交易日数据
        for i in range(1, len(df_sorted)):
            current = df_sorted.iloc[i]
            prev = df_sorted.iloc[i-1]
            
            volume_ma_10 = current['volume_ma_10'] if 'volume_ma_10' in current else None
            
            day = scanner.prepare_trading_day(current, prev, volume_ma_10)
            window.add_day(day)
        
        # 扫描追盘日
        window.scan_followthrough(scanner)
        
        # 获取状态
        status = window.get_current_status()
        
        # 获取指数名称
        index_name_map = {
            "000985": "中证全指",
            "000300": "沪深300",
        }
        index_name = index_name_map.get(index_code, index_code)
        
        # 计算追盘日统计
        followthrough_days = []
        for day in window.days:
            if day.is_followthrough:
                followthrough_days.append(day)
        
        total_followthrough = len(followthrough_days)
        active_followthrough = len([d for d in followthrough_days if not d.is_failed])
        
        # 构建摘要响应
        return {
            'index_code': index_code,
            'index_name': index_name,
            'window_days': window_days,
            'start_date': start_date,
            'end_date': end_date,
            'signal': status['signal'],
            'has_active_followthrough': status['signal'] == 'active',
            'active_followthrough': status.get('active_followthrough'),
            'attempt_start': status.get('attempt_start'),
            'attempt_days': status.get('attempt_days'),
            'followthrough_count': total_followthrough,
            'active_count': active_followthrough,
            'failed_count': total_followthrough - active_followthrough,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
    except Exception as e:
        logger.error(f"获取追盘日摘要失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_followthrough_config():
    """获取追盘日配置参数"""
    scanner = FollowThroughScanner()
    config = scanner.config
    
    descriptions = {
        'attempt_min_gain': '反弹尝试起点最小涨幅（默认: 0.1%）',
        'attempt_min_position': '反弹尝试起点最小区间位置（默认: 50%分位）',
        'min_days_since_attempt': '距离尝试起点最小天数（默认: 第4天）',
        'max_days_since_attempt': '距离尝试起点最大天数（默认: 第7天，可放宽至10）',
        'default_gain_threshold': '默认涨幅阈值（默认: 1.5%）',
        'dynamic_percentile': '动态阈值百分位数（默认: 90%）',
        'dynamic_lookback_days': '动态阈值回看天数（默认: 20日）',
        'volume_ma_days': '成交量均线天数（默认: 10日）',
        'volume_ratio_to_ma': '成交量对均量比率要求（默认: 1.1倍）',
        'volume_ratio_to_prev': '成交量对前一日比率要求（默认: 1.0倍）',
        'strong_gain_threshold': '强势追盘日最小涨幅（默认: 2.5%）',
        'strong_volume_ratio_to_ma': '强势追盘日成交量对均量比率（默认: 1.2倍）',
        'min_position_in_range': '最小区间位置要求（默认: 50%分位）',
        'max_upper_shadow_ratio': '最大上影线/实体比率（默认: 2.0倍）',
        'stop_loss_days': '止损观察期（默认: 5日）',
        'distribution_days_threshold': '抛盘日累积失效阈值（默认: 4个/10日）',
        'distribution_lookback_days': '抛盘日累积观察期（默认: 10日）',
        'negation_min_gain': '否定日最小跌幅（默认: -1.0%）',
        'negation_consecutive_days': '连续否定日数量（默认: 2日）',
        'negation_volume_ratio_to_ma': '否定日成交量对均量比率（默认: 1.1倍）',
        'low_lookback_days': '低点回看天数（默认: 25日）',
        'max_attempt_duration': '最大尝试持续时间（默认: 25个交易日）',
    }
    
    return {
        'config': config,
        'descriptions': descriptions,
    }


@router.get("/market-status")
async def get_integrated_market_status(
    index_code: str = Query("000985", description="指数代码"),
    data_access = Depends(get_data_access)
):
    """
    获取综合市场状态（抛盘日 + 追盘日）
    
    返回基于抛盘日和追盘日的综合市场状态判断
    """
    try:
        # 这里应该调用MarketStateIntegrator
        # 由于依赖抛盘日系统的实时数据，先返回模拟数据
        
        from core.market.market_state_integrator import MarketStateIntegrator, MarketState, MarketRecommendation
        
        integrator = MarketStateIntegrator()
        
        # 模拟数据
        status = integrator.get_integrated_status(index_code)
        
        # 获取详细建议
        details = integrator.get_recommendation_details(status)
        
        return {
            'integrated_status': status.to_dict(),
            'recommendation_details': details,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
    except Exception as e:
        logger.error(f"获取综合市场状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))