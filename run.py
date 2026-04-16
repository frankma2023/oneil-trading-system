#!/usr/bin/env python3
# 欧奈尔投资系统启动脚本

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """检查依赖"""
    try:
        import fastapi
        import pandas
        import sqlalchemy
        logger.info("依赖检查通过")
        return True
    except ImportError as e:
        logger.error(f"缺少依赖: {e}")
        logger.info("请运行: pip install -r requirements.txt")
        return False

def check_database():
    """检查数据库"""
    db_path = project_root / "data" / "database" / "lixinger.db"
    if not db_path.exists():
        logger.error(f"数据库文件不存在: {db_path}")
        logger.info("请从旧系统复制数据库文件到该位置")
        return False
    
    # 检查数据库是否可访问
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 5")
        tables = cursor.fetchall()
        conn.close()
        
        if tables:
            logger.info(f"数据库检测正常，找到 {len(tables)} 个表")
            return True
        else:
            logger.error("数据库中没有表")
            return False
    except Exception as e:
        logger.error(f"数据库访问失败: {e}")
        return False

def start_web_server():
    """启动Web服务器"""
    try:
        import uvicorn
        logger.info("启动FastAPI服务器...")
        logger.info("本地访问地址: http://127.0.0.1:8000")
        logger.info("网络访问地址: http://0.0.0.0:8000")
        logger.info("API文档: http://0.0.0.0:8000/docs")
        logger.info("大盘扫描: http://0.0.0.0:8000/market_scan.html")
        
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"启动服务器失败: {e}")
        return False

def run_test():
    """运行系统测试"""
    logger.info("运行系统测试...")
    
    try:
        # 测试数据访问层
        from data.access import get_data_access
        data = get_data_access()
        
        # 获取数据范围
        min_date, max_date = data.get_data_range()
        logger.info(f"数据日期范围: {min_date} 到 {max_date}")
        
        # 获取最新交易日
        latest_date = data.get_latest_trading_date()
        logger.info(f"最新交易日: {latest_date}")
        
        # 测试市场扫描器
        from core.market.indicators import MarketScanner
        scanner = MarketScanner(data)
        
        # 测试最近30天
        if latest_date:
            end_date = latest_date
            from datetime import datetime, timedelta
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            start_dt = end_dt - timedelta(days=30)
            start_date = start_dt.strftime('%Y-%m-%d')
            
            days = scanner.analyze_index(start_date=start_date, end_date=end_date)
            if days:
                stats = scanner.get_summary_statistics(days)
                logger.info(f"市场分析完成: {len(days)} 个交易日")
                logger.info(f"抛盘日: {stats['distribution_days']}, 吸筹日: {stats['accumulation_days']}")
                
                # 测试回测框架
                from core.backtest.framework import BacktestEngine, DistributionDayStrategy
                engine = BacktestEngine()
                strategy = DistributionDayStrategy(distribution_threshold=3)
                
                logger.info("回测框架测试完成")
                return True
            else:
                logger.warning("市场分析无数据")
                return False
        else:
            logger.warning("无最新交易日数据")
            return False
            
    except Exception as e:
        logger.error(f"系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("欧奈尔投资系统")
    print("基于威廉·欧奈尔投资理念的专业投资分析系统")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查数据库
    if not check_database():
        logger.warning("数据库检查失败，部分功能可能不可用")
    
    # 运行测试
    if not run_test():
        logger.warning("系统测试部分失败，但将继续启动")
    
    print("\n选择操作:")
    print("1. 启动Web服务器 (默认)")
    print("2. 运行市场扫描测试")
    print("3. 运行回测试测试")
    print("4. 退出")
    
    import sys
    if sys.stdin.isatty():
        choice = input("\n请选择 (1-4): ").strip()
    else:
        choice = "1"
        print("\n非交互式模式，自动选择: 1 (启动Web服务器)")
    
    if choice == "2":
        # 运行市场扫描测试
        from core.market.indicators import MarketScanner
        from data.access import get_data_access
        
        data = get_data_access()
        scanner = MarketScanner(data)
        
        latest_date = data.get_latest_trading_date()
        if latest_date:
            from datetime import datetime, timedelta
            end_dt = datetime.strptime(latest_date, '%Y-%m-%d')
            start_dt = end_dt - timedelta(days=60)
            start_date = start_dt.strftime('%Y-%m-%d')
            
            print(f"\n分析市场: {start_date} 到 {latest_date}")
            days = scanner.analyze_index(start_date=start_date, end_date=latest_date)
            
            if days:
                stats = scanner.get_summary_statistics(days)
                signals = scanner.generate_signals(days)
                
                print(f"\n市场统计:")
                print(f"  总交易日: {stats['total_days']}")
                print(f"  抛盘日: {stats['distribution_days']}")
                print(f"  吸筹日: {stats['accumulation_days']}")
                print(f"  追盘日: {stats['follow_through_days']}")
                
                if signals:
                    latest_signal = signals[-1]
                    print(f"\n最新信号:")
                    print(f"  日期: {latest_signal['date']}")
                    print(f"  信号: {latest_signal['signal']}")
                    print(f"  抛盘日计数: {latest_signal['distribution_count']}")
                    print(f"  建议: {latest_signal['recommendation']}")
        else:
            print("无交易日数据")
            
    elif choice == "3":
        # 运行回测试测试
        print("\n回测试测试...")
        from core.backtest.framework import BacktestEngine, DistributionDayStrategy
        
        engine = BacktestEngine()
        strategy = DistributionDayStrategy(distribution_threshold=3)
        
        # 使用最近一年数据
        from data.access import get_data_access
        data = get_data_access()
        latest_date = data.get_latest_trading_date()
        
        if latest_date:
            from datetime import datetime, timedelta
            end_dt = datetime.strptime(latest_date, '%Y-%m-%d')
            start_dt = end_dt - timedelta(days=365)
            start_date = start_dt.strftime('%Y-%m-%d')
            
            print(f"回测时间段: {start_date} 到 {latest_date}")
            try:
                result = engine.run(strategy, start_date, latest_date, save_results=False)
                print(result.summary())
            except Exception as e:
                print(f"回测失败: {e}")
        else:
            print("无交易日数据")
            
    elif choice == "4":
        print("退出系统")
        sys.exit(0)
    else:
        # 默认启动Web服务器
        start_web_server()

if __name__ == "__main__":
    main()