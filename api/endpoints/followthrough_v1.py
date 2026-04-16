#!/usr/bin/env python3
# 追盘日API端点
# 提供追盘日分析的相关接口

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import logging
import pandas as pd

from data.access import get_data_access
from core.market.distribution_scanner import MultiIndexScanner, DistributionScanner, DistributionWindow
from core.market.followthrough_scanner import FollowThroughScanner, FollowThroughDay, FollowThroughWindow

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/followthrough", tags=["追盘日分析"])


def get_market_status_history(data_access, index_code: str, start_date: str, end_date: str) -> List[Tuple[str, str]]:
    """
    获取市场状态历史记录
    
    返回:
        list of (date, market_status)
    """
    try:
        # 获取数据
        df = data_access.get_index_data(index_code, start_date, end_date)
        if df.empty:
            return []
        
        # 按日期排序
        df_sorted = df.sort_index().reset_index()
        
        # 创建抛盘日扫描器
        scanner = DistributionScanner()
        window = DistributionWindow(window_days=25)
        
        market_status_history = []
        
        for i in range(1, len(df_sorted)):
            current = df_sorted.iloc[i]
            prev = df_sorted.iloc[i-1]
            
            # 准备交易日
            day = scanner.prepare_trading_day(current, prev)
            day = scanner.analyze_distribution_day(day)
            
            # 添加到窗口
            window.add_day(day)
            
            # 获取当前市场状态
            stats = window.get_detailed_stats()
            market_status = stats['market_status']
            
            market_status_history.append((str(current['date']), market_status))
        
        return market_status_history
        
    except Exception as e:
        logger.error(f"获取市场状态历史失败: {e}")
        return []


@router.get("/analyze")
async def analyze_followthrough_days(
    start_date: str = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    days: int = Query(100, description="分析天数，如果提供则忽略start_date/end_date"),
    index_code: str = Query("000985", description="指数代码"),
    data_access = Depends(get_data_access)
):
    """
    分析指定时间段的追盘日
    
    返回追盘日详细分析
    """
    try:
        # 处理日期参数
        if start_date is None or end_date is None:
            # 使用days参数
            end_date_str = datetime.now().strftime('%Y-%m-%d')
            start_date_str = (datetime.strptime(end_date_str, '%Y-%m-%d') - timedelta(days=days)).strftime('%Y-%m-%d')
        else:
            start_date_str = start_date
            end_date_str = end_date
        
        logger.info(f"分析追盘日: {index_code} {start_date_str} 至 {end_date_str}")
        
        # 获取市场数据
        df = data_access.get_index_data(index_code, start_date_str, end_date_str)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到指数{index_code}在指定时间段的数据")
        
        # 按日期排序
        df_sorted = df.sort_index().reset_index()
        
        # 获取市场状态历史
        market_status_history = get_market_status_history(data_access, index_code, start_date_str, end_date_str)
        
        # 创建追盘日扫描器
        scanner = FollowThroughScanner()
        followthrough_days = []
        
        # 准备交易日数据
        trading_days = []
        for i in range(1, len(df_sorted)):
            current = df_sorted.iloc[i]
            prev = df_sorted.iloc[i-1]
            
            day = scanner.prepare_trading_day(current, prev)
            trading_days.append(day)
        
        # 扫描追盘日
        trading_days = scanner.scan_followthrough_days(trading_days, market_status_history)
        
        # 确认追盘日
        trading_days = scanner.confirm_followthrough_days(trading_days)
        
        # 提取追盘日信息
        for day in trading_days:
            if day.followthrough_type.value != "none":
                followthrough_days.append({
                    'date': day.date,
                    'index_code': day.index_code,
                    'change_pct': day.change_pct,
                    'volume_ratio': day.volume_ratio,
                    'followthrough_type': day.followthrough_type.value,
                    'followthrough_strength': day.followthrough_strength,
                    'is_confirmed': day.is_confirmed,
                    'days_since_attempt': day.days_since_attempt,
                    'attempt_day_date': day.attempt_day_date,
                })
        
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
            },
            'followthrough_days': followthrough_days,
            'statistics': {
                'total_followthrough_days': len(followthrough_days),
                'confirmed_days': len([d for d in followthrough_days if d['is_confirmed']]),
                'standard_days': len([d for d in followthrough_days if d['followthrough_type'] == 'standard']),
                'strong_days': len([d for d in followthrough_days if d['followthrough_type'] == 'strong']),
                'confirmation_rate': len([d for d in followthrough_days if d['is_confirmed']]) / len(followthrough_days) if followthrough_days else 0,
            }
        }
        
    except Exception as e:
        logger.error(f"追盘日分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_followthrough_summary(
    window_days: int = Query(50, description="分析窗口天数"),
    index_code: str = Query("000985", description="指数代码"),
    data_access = Depends(get_data_access)
):
    """
    获取追盘日摘要信息
    
    返回最近窗口内的追盘日统计
    """
    try:
        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=window_days * 2)).strftime('%Y-%m-%d')
        
        # 调用analyze接口
        # 这里可以优化，避免重复计算
        # 暂时直接调用analyze函数
        result = await analyze_followthrough_days(
            start_date=start_date,
            end_date=end_date,
            days=None,
            index_code=index_code,
            data_access=data_access
        )
        
        # 提取最近window_days天的数据
        followthrough_days = result['followthrough_days']
        recent_days = []
        
        # 计算截止日期
        cutoff_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=window_days)).strftime('%Y-%m-%d')
        
        for day in followthrough_days:
            if day['date'] >= cutoff_date:
                recent_days.append(day)
        
        # 统计
        stats = result['statistics']
        
        # 获取市场状态
        market_status_history = get_market_status_history(data_access, index_code, cutoff_date, end_date)
        current_market_status = market_status_history[-1][1] if market_status_history else "未知"
        
        return {
            'index_code': index_code,
            'index_name': result['metadata']['index_name'],
            'window_days': window_days,
            'start_date': cutoff_date,
            'end_date': end_date,
            'current_market_status': current_market_status,
            'followthrough_days_count': len(recent_days),
            'confirmed_days_count': len([d for d in recent_days if d['is_confirmed']]),
            'latest_followthrough': recent_days[-1]['date'] if recent_days else None,
            'latest_confirmed': None,
            'confirmation_rate': stats['confirmation_rate'],
        }
        
    except Exception as e:
        logger.error(f"获取追盘日摘要失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_followthrough_config():
    """获取追盘日配置参数"""
    scanner = FollowThroughScanner()
    return {
        'config': scanner.config,
        'description': {
            'followthrough_min_gain': '追盘日最小涨幅（默认1.5%）',
            'followthrough_min_volume_ratio': '追盘日最小成交量比率（默认1.0）',
            'strong_followthrough_gain': '强势追盘日最小涨幅（默认2.5%）',
            'strong_followthrough_volume_ratio': '强势追盘日最小成交量比率（默认1.2）',
            'attempt_day_min_gain': '反弹尝试日最小涨幅（默认0.5%）',
            'attempt_day_min_volume_ratio': '反弹尝试日最小成交量比率（默认0.9）',
            'min_days_since_attempt': '距离反弹尝试日的最小天数（默认4）',
            'max_days_since_attempt': '距离反弹尝试日的最大天数（默认7）',
            'confirmation_days_window': '确认窗口天数（默认3）',
            'confirmation_min_gain': '确认日最小涨幅（默认0.2%）',
        }
    }