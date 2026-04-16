#!/usr/bin/env python3
"""
快速启动欧奈尔投资系统Web服务器
"""

import uvicorn
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("=" * 60)
    print("欧奈尔投资系统 Web服务器")
    print("基于威廉·欧奈尔投资理念的专业投资分析系统")
    print("=" * 60)
    print(f"Python路径: {sys.executable}")
    print(f"工作目录: {os.getcwd()}")
    print(f"服务器地址: http://0.0.0.0:8001")
    print(f"本地访问: http://127.0.0.1:8001")
    print("=" * 60)
    print("\n可用页面:")
    print("  - 大盘扫描: http://127.0.0.1:8001/market_scan.html")
    print("  - 抛盘日回测: http://127.0.0.1:8001/backtest.html")
    print("  - 追盘日回测: http://127.0.0.1:8001/followthrough_backtest.html")
    print("  - 行业扫描: http://127.0.0.1:8001/industry_scan.html")
    print("  - 股票筛选: http://127.0.0.1:8001/stock_scan.html")
    print("  - 模式识别: http://127.0.0.1:8001/pattern_scan.html")
    print("  - 回测实验室: http://127.0.0.1:8001/backtest_lab.html")
    print("  - 持仓管理: http://127.0.0.1:8001/portfolio.html")
    print("  - 仪表盘: http://127.0.0.1:8001/dashboard.html")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    try:
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=8001,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"\n启动服务器失败: {e}")
        sys.exit(1)