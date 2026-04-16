#!/usr/bin/env python3
# FastAPI主应用
# 提供欧奈尔投资系统的Web API接口

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import uvicorn
import logging

from data.access import get_data_access
from core.market.distribution_scanner import MultiIndexScanner

# 导入抛盘日API路由
from api.endpoints.distribution import router as distribution_router
from api.endpoints.backtest import router as backtest_router
from api.endpoints.followthrough_v2 import router as followthrough_router

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="欧奈尔投资系统 API",
    description="基于威廉·欧奈尔投资理念的专业投资分析系统",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# 注册API路由
app.include_router(distribution_router)
app.include_router(backtest_router)
app.include_router(followthrough_router)

# 依赖注入
def get_db():
    """获取数据库访问实例"""
    return get_data_access()

def get_scanner():
    """获取市场扫描器实例"""
    data_access = get_data_access()
    return MultiIndexScanner(data_access)


@app.get("/favicon.svg")
async def get_favicon():
    """提供网站图标"""
    return FileResponse("web/static/favicon.svg")

@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径，重定向到大盘扫描页面"""
    return FileResponse("web/pages/market_scan/index.html")


# 简洁的页面路由
@app.get("/market_scan.html", response_class=HTMLResponse)
async def market_scan_page():
    """大盘扫描页面"""
    return FileResponse("web/pages/market_scan/index.html")


@app.get("/industry_scan.html", response_class=HTMLResponse)
async def industry_scan_page():
    """行业扫描页面（待开发）"""
    # 暂时重定向到大盘扫描
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/market_scan.html")


@app.get("/stock_scan.html", response_class=HTMLResponse)
async def stock_scan_page():
    """个股筛选页面（待开发）"""
    # 暂时返回占位页面
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>个股筛选 · 欧奈尔投资系统</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="/static/css/dark_theme.css">
    </head>
    <body>
        <div style="padding: 2rem; text-align: center;">
            <h1>个股筛选功能正在开发中</h1>
            <p>基于CAN SLIM评分系统的个股筛选工具</p>
            <a href="/market_scan.html">返回大盘扫描</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/pattern_scan.html", response_class=HTMLResponse)
async def pattern_scan_page():
    """形态识别页面（待开发）"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>形态识别 · 欧奈尔投资系统</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="/static/css/dark_theme.css">
    </head>
    <body>
        <div style="padding: 2rem; text-align: center;">
            <h1>形态识别功能正在开发中</h1>
            <p>欧奈尔形态（杯柄、双重底等）识别工具</p>
            <a href="/market_scan.html">返回大盘扫描</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/backtest_lab.html", response_class=HTMLResponse)
async def backtest_lab_page():
    """回测实验室页面（待开发）"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>回测实验室 · 欧奈尔投资系统</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="/static/css/dark_theme.css">
    </head>
    <body>
        <div style="padding: 2rem; text-align: center;">
            <h1>回测实验室功能正在开发中</h1>
            <p>策略验证、参数优化、绩效评估工具</p>
            <a href="/market_scan.html">返回大盘扫描</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/backtest.html", response_class=HTMLResponse)
async def backtest_page():
    """抛盘日参数回测页面"""
    return FileResponse("web/pages/backtest/index.html")

@app.get("/followthrough_backtest.html", response_class=HTMLResponse)
async def followthrough_backtest_page():
    """追盘日参数回测页面"""
    return FileResponse("web/pages/followthrough_backtest/index.html")


@app.get("/portfolio.html", response_class=HTMLResponse)
async def portfolio_page():
    """持仓管理页面（待开发）"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>持仓管理 · 欧奈尔投资系统</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="/static/css/dark_theme.css">
    </head>
    <body>
        <div style="padding: 2rem; text-align: center;">
            <h1>持仓管理功能正在开发中</h1>
            <p>仓位管理、信号监控、风险控制工具</p>
            <a href="/market_scan.html">返回大盘扫描</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/dashboard.html", response_class=HTMLResponse)
async def dashboard_page():
    """总览仪表板页面（待开发）"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>总览仪表板 · 欧奈尔投资系统</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="/static/css/dark_theme.css">
    </head>
    <body>
        <div style="padding: 2rem; text-align: center;">
            <h1>总览仪表板功能正在开发中</h1>
            <p>系统概览、风险监控、绩效总览工具</p>
            <a href="/market_scan.html">返回大盘扫描</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# 市场数据API
@app.get("/api/market/dates")
async def get_market_dates():
    """获取可用的交易日列表"""
    data = get_data_access()
    dates = data.get_trading_dates()
    return {"dates": dates[-100:]}  # 返回最近100个交易日


@app.get("/api/market/analysis")
async def analyze_market(
    start_date: str = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    index_code: str = Query("000985", description="指数代码，默认中证全指"),
    scanner: MultiIndexScanner = Depends(get_scanner)
):
    """分析指定时间段的市场状况"""
    try:
        # 如果没有提供日期，使用最近60天
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=60)).strftime('%Y-%m-%d')
        
        logger.info(f"分析市场: {index_code} {start_date} 到 {end_date}")
        
        # 执行分析 - 使用 MultiIndexScanner 的 analyze_index 方法
        days = scanner.analyze_index(index_code, start_date, end_date)
        
        # 获取市场状态
        combined_analysis = scanner.get_combined_analysis()
        index_stats = combined_analysis.get(index_code, {})
        
        # 获取指数名称映射
        index_name_map = {
            "000985": "中证全指",
            "000300": "沪深300",
        }
        index_name = index_name_map.get(index_code, index_code)
        
        # 计算基本统计
        total_days = len(days)
        distribution_days = [d for d in days if d['distribution_type'] != 'none']
        flat_days = [d for d in days if d['is_flat_day']]
        confirmation_days = [d for d in days if d['is_confirmation_day']]
        
        # 计算加权抛盘日总数
        weighted_total = sum(d['distribution_weight'] for d in distribution_days)
        
        # 确定市场状态
        market_status = "正常状态"
        if weighted_total >= 8:
            market_status = "熊市状态"
        elif weighted_total >= 5:
            market_status = "承压状态"
        
        stats = {
            'total_days': total_days,
            'distribution_days': len(distribution_days),
            'flat_days': len(flat_days),
            'confirmation_days': len(confirmation_days),
            'weighted_total': weighted_total,
            'market_status': market_status,
            'index_name': index_name,
        }
        
        return {
            'metadata': {
                'index_code': index_code,
                'index_name': index_name,
                'start_date': start_date,
                'end_date': end_date,
                'total_days': total_days,
            },
            'statistics': stats,
            'market_days': days,
            'combined_analysis': combined_analysis,
        }
        
    except Exception as e:
        logger.error(f"市场分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/indices")
async def get_market_indices():
    """获取市场指数列表"""
    data = get_data_access()
    indices = data.get_market_indices()
    return {"indices": indices}


@app.get("/api/market/index/{index_code}")
async def get_index_data(
    index_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """获取指数数据"""
    data = get_data_access()
    df = data.get_index_data(index_code, start_date, end_date)
    
    if df.empty:
        raise HTTPException(status_code=404, detail=f"指数 {index_code} 无数据")
    
    return {
        'index_code': index_code,
        'data': df.reset_index().to_dict('records')
    }


@app.get("/api/market/summary")
async def get_market_summary(
    days: int = Query(30, description="天数，默认30天")
):
    """获取市场摘要（最近N天） - 基于抛盘日分析"""
    try:
        data = get_data_access()
        
        # 计算日期范围
        end_date = data.get_latest_trading_date()
        if not end_date:
            raise HTTPException(status_code=404, detail="无交易日数据")
        
        end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_date_dt = end_date_dt - timedelta(days=days * 2)  # 多取一些天数，确保有足够交易日
        start_date = start_date_dt.strftime('%Y-%m-%d')
        
        # 创建多指数扫描器
        scanner = MultiIndexScanner(data)
        
        # 分析两个主要指数
        indices = ["000985", "000300"]
        distribution_totals = []
        detailed_stats = {}
        
        for index_code in indices:
            try:
                scanner.analyze_index(index_code, start_date, end_date)
                combined = scanner.get_combined_analysis()
                index_stats = combined.get(index_code, {})
                
                distribution_totals.append(index_stats.get('distribution_total', 0))
                detailed_stats[index_code] = {
                    'distribution_total': index_stats.get('distribution_total', 0),
                    'market_status': index_stats.get('market_status', '未知'),
                    'stats': index_stats.get('stats', {}),
                }
            except Exception as idx_e:
                logger.error(f"指数 {index_code} 分析失败: {idx_e}")
                distribution_totals.append(0)
                detailed_stats[index_code] = {
                    'error': str(idx_e),
                    'distribution_total': 0,
                    'market_status': '错误',
                }
        
        avg_distribution = sum(distribution_totals) / len(distribution_totals) if distribution_totals else 0
        
        # 判断市场状态
        if avg_distribution >= 8:
            market_status = "熊市状态"
            recommendation = "暂停选股"
        elif avg_distribution >= 5:
            market_status = "承压状态"
            recommendation = "谨慎选股"
        else:
            market_status = "正常状态"
            recommendation = "正常选股"
        
        summary = {
            'date': end_date,
            'analysis_days': days,
            'distribution_count_avg': round(avg_distribution, 2),
            'distribution_count_985': distribution_totals[0] if len(distribution_totals) > 0 else 0,
            'distribution_count_300': distribution_totals[1] if len(distribution_totals) > 1 else 0,
            'market_status': market_status,
            'recommendation': recommendation,
            'detailed_stats': detailed_stats,
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"获取市场摘要失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 个股数据API
@app.get("/api/stocks/search")
async def search_stocks(
    query: str = Query(..., description="搜索关键词（代码或名称）"),
    limit: int = Query(20, description="返回结果数量")
):
    """搜索股票"""
    data = get_data_access()
    stocks = data.get_stock_list()
    
    results = []
    query_lower = query.lower()
    
    for stock in stocks:
        if (query_lower in stock['stock_code'].lower() or 
            query_lower in stock.get('name', '').lower()):
            results.append(stock)
            if len(results) >= limit:
                break
    
    return {"stocks": results}


@app.get("/api/stocks/{stock_code}")
async def get_stock_data(
    stock_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """获取股票数据"""
    data = get_data_access()
    df = data.get_stock_data(stock_code, start_date, end_date)
    
    if df.empty:
        raise HTTPException(status_code=404, detail=f"股票 {stock_code} 无数据")
    
    # 获取股票基本信息
    stocks = data.get_stock_list()
    stock_info = next((s for s in stocks if s['stock_code'] == stock_code), {})
    
    return {
        'stock_code': stock_code,
        'stock_info': stock_info,
        'data': df.reset_index().to_dict('records')
    }


# 回测API
@app.get("/api/backtest/strategies")
async def get_backtest_strategies():
    """获取可用的回测策略列表"""
    strategies = [
        {
            'id': 'distribution_day',
            'name': '抛盘日择时策略',
            'description': '基于抛盘日计数的市场择时策略',
            'parameters': [
                {'name': 'distribution_threshold', 'type': 'int', 'default': 3, 'min': 1, 'max': 10},
                {'name': 'follow_through_enabled', 'type': 'bool', 'default': True},
                {'name': 'initial_position', 'type': 'float', 'default': 0.5, 'min': 0, 'max': 1},
            ]
        },
        # 可以添加更多策略
    ]
    return {"strategies": strategies}


if __name__ == "__main__":
    # 开发服务器
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )