#!/usr/bin/env python3
# 抛盘日API端点
# 提供抛盘日分析的相关接口

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import logging

from data.access import get_data_access
from core.market.distribution_scanner import MultiIndexScanner, DistributionScanner

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/distribution", tags=["抛盘日分析"])


@router.get("/analyze")
async def analyze_distribution_days(
    start_date: str = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    days: int = Query(None, description="分析天数，如果提供则忽略start_date/end_date"),
    index_codes: str = Query("000985,000300", description="指数代码，用逗号分隔"),
    data_access = Depends(get_data_access)
):
    """
    分析指定时间段的抛盘日
    
    返回两个指数的抛盘日详细分析
    """
    try:
        # 解析指数代码
        indices = [code.strip() for code in index_codes.split(",") if code.strip()]
        if not indices:
            indices = ["000985", "000300"]
        
        # 处理日期参数
        if days is not None:
            # 使用days参数
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days)).strftime('%Y-%m-%d')
        else:
            # 使用start_date/end_date参数
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=60)).strftime('%Y-%m-%d')
        
        logger.info(f"分析抛盘日: 指数={indices}, {start_date} 到 {end_date}")
        
        # 创建多指数扫描器
        scanner = MultiIndexScanner(data_access)
        
        results = {}
        
        for index_code in indices:
            try:
                # 分析指数
                days = scanner.analyze_index(index_code, start_date, end_date)
                
                # 获取综合分析
                combined = scanner.get_combined_analysis()
                
                results[index_code] = {
                    'metadata': {
                        'index_code': index_code,
                        'start_date': start_date,
                        'end_date': end_date,
                        'total_days': len(days),
                    },
                    'days': days[-30:],  # 返回最近30天的数据
                    'stats': combined.get(index_code, {}).get('stats', {}),
                    'market_status': combined.get(index_code, {}).get('market_status', '未知'),
                }
                
            except Exception as e:
                logger.error(f"指数 {index_code} 分析失败: {e}")
                results[index_code] = {
                    'error': str(e),
                    'metadata': {
                        'index_code': index_code,
                        'start_date': start_date,
                        'end_date': end_date,
                    }
                }
        
        return {
            'metadata': {
                'start_date': start_date,
                'end_date': end_date,
                'indices': indices,
            },
            'results': results,
        }
        
    except Exception as e:
        logger.error(f"抛盘日分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_distribution_summary(
    days: int = Query(30, description="分析天数，默认30天"),
    data_access = Depends(get_data_access)
):
    """
    获取抛盘日摘要（最近N天）
    """
    try:
        # 获取最新交易日
        latest_date = data_access.get_latest_trading_date()
        if not latest_date:
            raise HTTPException(status_code=404, detail="无交易日数据")
        
        # 计算开始日期
        latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
        start_dt = latest_dt - timedelta(days=days * 2)  # 多取一些天数
        start_date = start_dt.strftime('%Y-%m-%d')
        
        # 创建扫描器
        scanner = MultiIndexScanner(data_access)
        
        indices = ["000985", "000300"]
        summary = {}
        
        for index_code in indices:
            try:
                # 分析指数
                scanner.analyze_index(index_code, start_date, latest_date)
                
                # 获取综合分析
                combined = scanner.get_combined_analysis()
                index_stats = combined.get(index_code, {})
                
                summary[index_code] = {
                    'distribution_total': index_stats.get('distribution_total', 0),
                    'market_status': index_stats.get('market_status', '未知'),
                    'stats': index_stats.get('stats', {}),
                    'latest_date': latest_date,
                }
                
            except Exception as e:
                logger.error(f"指数 {index_code} 摘要获取失败: {e}")
                summary[index_code] = {
                    'error': str(e),
                    'latest_date': latest_date,
                }
        
        # 综合判断
        combined_status = "正常"
        total_distributions = sum(
            s.get('distribution_total', 0) 
            for s in summary.values() 
            if isinstance(s, dict) and 'distribution_total' in s
        )
        
        # 计算平均抛盘日数
        valid_indices = [s for s in summary.values() if isinstance(s, dict) and 'distribution_total' in s]
        average_distribution = total_distributions / len(valid_indices) if valid_indices else 0
        
        if average_distribution >= 8:
            combined_status = "熊市状态"
            recommendation = "暂停选股，降低仓位"
        elif average_distribution >= 5:
            combined_status = "承压状态"
            recommendation = "谨慎选股，控制仓位"
        else:
            combined_status = "正常状态"
            recommendation = "正常选股"
        
        return {
            'date': latest_date,
            'analysis_days': days,
            'indices': summary,  # 重命名为indices以匹配前端
            'combined_status': combined_status,
            'average_distribution': round(average_distribution, 2),
            'recommendation': recommendation,
            'total_distributions': total_distributions,
        }
        
    except Exception as e:
        logger.error(f"抛盘日摘要获取失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_distribution_types():
    """
    获取抛盘日类型定义
    """
    return {
        'types': [
            {
                'id': 'standard',
                'name': '标准抛盘日',
                'description': '当日下跌（涨幅 ≤ -0.1%）且成交量 > 前一日',
                'conditions': [
                    '收盘价 < 前一日收盘价',
                    '当日成交量 > 前一日',
                    '当日涨跌幅 ≤ -0.1%',
                ]
            },
            {
                'id': 'special',
                'name': '特殊抛盘日（假阳线/滞涨）',
                'description': '当日收涨但涨幅 < 0.2%，成交量 > 前一日1.3倍，且上影线足够长',
                'conditions': [
                    '收盘涨幅 < 0.2%',
                    '盘中最高涨幅 ≥ 0.5%',
                    '成交量 > 前一日 × 1.3',
                    '上影线 ≥ 实体 × 1.5',
                ]
            },
            {
                'id': 'intraday_reversal',
                'name': '盘中反转抛盘日',
                'description': '当日收阴，成交量 > 前一日1.2倍，上影线足够长，且盘中曾上涨 ≥ 0.5%后回落',
                'conditions': [
                    '收盘价 < 开盘价（收阴）',
                    '成交量 > 前一日 × 1.2',
                    '上影线 ≥ 实体 × 1.5',
                    '盘中最高价 ≥ 前一日收盘价 × 1.005',
                ]
            }
        ],
        'rules': [
            {
                'name': '平盘日过滤',
                'description': '涨跌幅绝对值 < 0.05% 的交易日不计为任何抛盘日'
            },
            {
                'name': '多重计数规则',
                'description': '若指数单日跌幅 ≥ -1.5% 且放量，计为 2个抛盘日'
            },
            {
                'name': '确认日抵消机制',
                'description': '升势确认日（涨幅 ≥ 1.5% 且成交量 ≥ 前一日）可抵消 1个抛盘日'
            },
            {
                'name': '窗口滚动',
                'description': '严格滚动 25 个交易日，超过25天的抛盘日自动移出统计'
            },
            {
                'name': '市场状态判断',
                'description': '抛盘日≥5:承压状态，抛盘日≥8:熊市状态'
            }
        ]
    }


@router.get("/config")
async def get_distribution_config():
    """
    获取抛盘日配置参数
    """
    scanner = DistributionScanner()
    
    return {
        'config': scanner.config,
        'description': '欧奈尔抛盘日扫描器配置参数',
        'note': '所有百分比值均为小数形式（如0.01表示1%）',
    }


@router.get("/history/{index_code}")
async def get_distribution_history(
    index_code: str,
    limit: int = Query(100, description="返回记录数，默认100"),
    data_access = Depends(get_data_access)
):
    """
    获取指数的抛盘日历史记录
    """
    try:
        # 获取最新交易日
        latest_date = data_access.get_latest_trading_date()
        if not latest_date:
            raise HTTPException(status_code=404, detail="无交易日数据")
        
        # 获取足够的数据（假设每天都有数据）
        latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
        start_dt = latest_dt - timedelta(days=limit * 2)
        start_date = start_dt.strftime('%Y-%m-%d')
        
        # 创建扫描器
        scanner = MultiIndexScanner(data_access)
        
        # 分析指数
        days = scanner.analyze_index(index_code, start_date, latest_date)
        
        # 筛选有抛盘日的交易日
        distribution_days = [
            day for day in days 
            if day.get('distribution_type') != 'none'
        ]
        
        # 按日期倒序排序
        distribution_days.sort(key=lambda x: x['date'], reverse=True)
        
        return {
            'index_code': index_code,
            'total_days': len(days),
            'distribution_days': len(distribution_days),
            'history': distribution_days[:limit],
        }
        
    except Exception as e:
        logger.error(f"抛盘日历史获取失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_status")
async def get_market_status(
    data_access = Depends(get_data_access)
):
    """
    获取当前市场状态
    """
    try:
        # 获取最近60天数据
        latest_date = data_access.get_latest_trading_date()
        if not latest_date:
            raise HTTPException(status_code=404, detail="无交易日数据")
        
        latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
        start_dt = latest_dt - timedelta(days=60)
        start_date = start_dt.strftime('%Y-%m-%d')
        
        # 创建扫描器
        scanner = MultiIndexScanner(data_access)
        
        indices = ["000985", "000300"]
        status_results = {}
        
        for index_code in indices:
            try:
                # 分析指数
                scanner.analyze_index(index_code, start_date, latest_date)
                
                # 获取综合分析
                combined = scanner.get_combined_analysis()
                index_stats = combined.get(index_code, {})
                
                status_results[index_code] = {
                    'market_status': index_stats.get('market_status', '未知'),
                    'distribution_total': index_stats.get('distribution_total', 0),
                    'stats': index_stats.get('stats', {}),
                }
                
            except Exception as e:
                logger.error(f"指数 {index_code} 状态获取失败: {e}")
                status_results[index_code] = {
                    'error': str(e),
                    'market_status': '错误',
                }
        
        # 综合状态判断
        totals = [
            s.get('distribution_total', 0) 
            for s in status_results.values() 
            if isinstance(s, dict) and 'distribution_total' in s
        ]
        
        avg_total = sum(totals) / len(totals) if totals else 0
        
        if avg_total >= 8:
            combined_status = "熊市状态"
            recommendation = "暂停选股，降低仓位"
        elif avg_total >= 5:
            combined_status = "承压状态"
            recommendation = "谨慎选股，控制仓位"
        else:
            combined_status = "正常状态"
            recommendation = "正常选股"
        
        return {
            'date': latest_date,
            'indices': status_results,
            'combined_status': combined_status,
            'recommendation': recommendation,
            'average_distribution': round(avg_total, 2),
        }
        
    except Exception as e:
        logger.error(f"市场状态获取失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))