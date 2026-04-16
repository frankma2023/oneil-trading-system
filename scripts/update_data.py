#!/usr/bin/env python3
# 数据更新脚本
# 用于每日更新市场数据

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import logging

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.access import get_data_access

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_market_data():
    """更新市场数据"""
    logger.info("开始更新市场数据...")
    
    data = get_data_access()
    
    # 获取最新交易日
    latest_date = data.get_latest_trading_date()
    if latest_date:
        logger.info(f"当前最新交易日: {latest_date}")
        
        # 检查是否需要更新（如果最新日期不是今天）
        today = datetime.now().strftime('%Y-%m-%d')
        if latest_date < today:
            logger.info(f"需要更新数据: {latest_date} -> {today}")
            # 这里应该调用API获取最新数据
            # 暂时只是占位
            logger.info("数据更新功能待实现")
        else:
            logger.info("数据已是最新")
    else:
        logger.warning("无法获取最新交易日")
    
    logger.info("市场数据更新完成")

def update_stock_data():
    """更新股票数据"""
    logger.info("开始更新股票数据...")
    # 待实现
    logger.info("股票数据更新功能待实现")

def update_indicators():
    """更新指标计算"""
    logger.info("开始更新指标计算...")
    
    try:
        from core.market.indicators import MarketScanner
        
        data = get_data_access()
        scanner = MarketScanner(data)
        
        # 获取最近60天数据
        latest_date = data.get_latest_trading_date()
        if latest_date:
            end_date = latest_date
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            start_dt = end_dt - timedelta(days=60)
            start_date = start_dt.strftime('%Y-%m-%d')
            
            logger.info(f"计算市场指标: {start_date} 到 {end_date}")
            
            # 分析市场
            days = scanner.analyze_index(start_date=start_date, end_date=end_date)
            
            if days:
                stats = scanner.get_summary_statistics(days)
                logger.info(f"指标计算完成: {len(days)} 个交易日")
                logger.info(f"抛盘日: {stats['distribution_days']}, 吸筹日: {stats['accumulation_days']}")
                
                # 这里应该将结果保存到数据库
                # 暂时只是记录
            else:
                logger.warning("市场分析无数据")
        else:
            logger.warning("无最新交易日数据")
            
    except Exception as e:
        logger.error(f"指标计算失败: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("指标计算完成")

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("欧奈尔投资系统 - 数据更新脚本")
    logger.info("=" * 60)
    
    # 更新市场数据
    update_market_data()
    
    # 更新股票数据
    update_stock_data()
    
    # 更新指标计算
    update_indicators()
    
    logger.info("数据更新脚本执行完成")

if __name__ == "__main__":
    main()