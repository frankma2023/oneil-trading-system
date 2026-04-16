#!/usr/bin/env python3
"""
欧奈尔抛盘日回测脚本
回测最近25个交易日中证全指和沪深300的抛盘日数量
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主回测函数"""
    print("=" * 70)
    print("欧奈尔抛盘日回测 - 最近25个交易日")
    print("=" * 70)
    
    try:
        # 导入项目模块
        from data.access import get_data_access
        from core.market.distribution_scanner import DistributionScanner, MultiIndexScanner
        
        # 初始化数据访问
        print("1. 初始化数据访问层...")
        data = get_data_access()
        print(f"   数据库: {data.db_path}")
        
        # 获取最新交易日
        latest_date = data.get_latest_trading_date()
        print(f"   最新交易日: {latest_date}")
        
        if not latest_date:
            print("错误: 无法获取最新交易日")
            return
        
        # 获取最近25个交易日
        print("\n2. 获取交易日列表...")
        trading_dates = data.get_trading_dates(end_date=latest_date)
        print(f"   总交易日数: {len(trading_dates):,}")
        
        if len(trading_dates) < 25:
            print(f"警告: 只有 {len(trading_dates)} 个交易日，少于25个")
            analysis_dates = trading_dates
        else:
            # 取最近25个交易日
            analysis_dates = trading_dates[-25:]
        
        start_date = analysis_dates[0]
        end_date = analysis_dates[-1]
        print(f"   分析期间: {start_date} 到 {end_date}")
        print(f"   分析天数: {len(analysis_dates)} 个交易日")
        
        # 定义要分析的指数
        indices = [
            ("000985", "中证全指"),
            ("000300", "沪深300")
        ]
        
        # 方法1: 使用DistributionScanner进行详细分析
        print("\n3. 使用DistributionScanner进行详细分析...")
        scanner = DistributionScanner()
        
        all_results = {}
        
        for index_code, index_name in indices:
            print(f"\n   --- 分析 {index_name} ({index_code}) ---")
            
            # 获取指数数据
            df = data.get_index_data(index_code, start_date, end_date)
            print(f"     获取到 {len(df)} 行数据")
            
            if df.empty:
                print(f"     警告: {index_code} 无数据，跳过")
                continue
            
            # 按日期排序
            df_sorted = df.sort_index().reset_index()
            
            # 分析每个交易日
            results = []
            distribution_days = []
            distribution_types = {
                "standard": 0,
                "special": 0,
                "intraday_reversal": 0,
                "heavy": 0,  # 重抛盘日（计为2个）
                "confirmation": 0,  # 确认日
                "flat": 0,   # 平盘日
            }
            
            weighted_total = 0  # 加权抛盘日总数
            confirmation_count = 0  # 确认日数量
            
            for i in range(1, len(df_sorted)):
                current_row = df_sorted.iloc[i]
                prev_row = df_sorted.iloc[i-1]
                
                # 准备交易日数据
                day = scanner.prepare_trading_day(current_row, prev_row)
                
                # 分析抛盘日
                day = scanner.analyze_distribution_day(day)
                
                # 统计
                if day.is_flat_day:
                    distribution_types["flat"] += 1
                elif day.distribution_type.value != "none":
                    # 记录抛盘日
                    distribution_days.append({
                        'date': day.date,
                        'type': day.distribution_type.value,
                        'weight': day.distribution_weight,
                        'change_pct': day.change_pct,
                        'volume_ratio': day.volume_ratio,
                    })
                    
                    # 统计类型
                    if day.distribution_type.value == "standard":
                        distribution_types["standard"] += 1
                    elif day.distribution_type.value == "special":
                        distribution_types["special"] += 1
                    elif day.distribution_type.value == "intraday_reversal":
                        distribution_types["intraday_reversal"] += 1
                    
                    # 统计重抛盘日
                    if day.distribution_weight == 2:
                        distribution_types["heavy"] += 1
                    
                    # 加权总数
                    weighted_total += day.distribution_weight
                
                # 统计确认日
                if day.is_confirmation_day:
                    distribution_types["confirmation"] += 1
                    confirmation_count += 1
            
            # 计算原始总数（不计权重）
            raw_total = (distribution_types["standard"] + 
                        distribution_types["special"] + 
                        distribution_types["intraday_reversal"])
            
            # 显示结果
            print(f"     平盘日: {distribution_types['flat']}")
            print(f"     标准抛盘日: {distribution_types['standard']}")
            print(f"     特殊抛盘日: {distribution_types['special']}")
            print(f"     盘中反转抛盘日: {distribution_types['intraday_reversal']}")
            print(f"     重抛盘日（计为2个）: {distribution_types['heavy']}")
            print(f"     确认日: {distribution_types['confirmation']}")
            print(f"     原始抛盘日总数: {raw_total}")
            print(f"     加权抛盘日总数: {weighted_total}")
            
            # 市场状态判断
            market_status = "正常状态"
            if weighted_total >= 8:
                market_status = "熊市状态"
            elif weighted_total >= 5:
                market_status = "承压状态"
            
            print(f"     市场状态: {market_status}")
            
            # 保存结果
            all_results[index_code] = {
                'name': index_name,
                'raw_total': raw_total,
                'weighted_total': weighted_total,
                'distribution_types': distribution_types,
                'market_status': market_status,
                'distribution_days': distribution_days,  # 详细抛盘日列表
            }
        
        # 方法2: 使用MultiIndexScanner进行综合分析和确认日抵消
        print("\n4. 使用MultiIndexScanner进行综合分析和确认日抵消...")
        multi_scanner = MultiIndexScanner(data)
        
        for index_code, index_name in indices:
            print(f"\n   --- MultiIndexScanner分析 {index_name} ({index_code}) ---")
            
            try:
                # 分析指数
                analysis_results = multi_scanner.analyze_index(index_code, start_date, end_date)
                print(f"     分析完成，共 {len(analysis_results)} 个交易日")
                
                # 获取综合分析
                combined = multi_scanner.get_combined_analysis()
                index_result = combined.get(index_code, {})
                
                if index_result:
                    stats = index_result.get('stats', {})
                    market_status = index_result.get('market_status', '未知')
                    distribution_total = index_result.get('distribution_total', 0)
                    
                    print(f"     市场状态: {market_status}")
                    print(f"     抛盘日总数: {distribution_total}")
                    
                    # 显示详细统计
                    if stats:
                        print(f"     标准抛盘日: {stats.get('standard', 0)}")
                        print(f"     特殊抛盘日: {stats.get('special', 0)}")
                        print(f"     盘中反转抛盘日: {stats.get('intraday_reversal', 0)}")
                        print(f"     重抛盘日: {stats.get('heavy_distribution', 0)}")
                        print(f"     确认日: {stats.get('confirmation_days', 0)}")
                        print(f"     加权总数: {stats.get('weighted_total', 0)}")
                        print(f"     抵消后总数: {stats.get('total_after_offset', 0)}")
                
            except Exception as e:
                print(f"     MultiIndexScanner分析失败: {e}")
        
        # 显示详细抛盘日列表
        print("\n5. 详细抛盘日列表:")
        for index_code, index_name in indices:
            if index_code in all_results:
                result = all_results[index_code]
                distribution_days = result['distribution_days']
                
                if distribution_days:
                    print(f"\n   {index_name} ({index_code}) 抛盘日:")
                    for day in distribution_days:
                        print(f"     {day['date']}: {day['type']} (权重:{day['weight']}, "
                              f"涨跌幅:{day['change_pct']:.2%}, 成交量比:{day['volume_ratio']:.2f})")
                else:
                    print(f"\n   {index_name} ({index_code}): 无抛盘日")
        
        # 总结
        print("\n" + "=" * 70)
        print("回测总结")
        print("=" * 70)
        
        for index_code, index_name in indices:
            if index_code in all_results:
                result = all_results[index_code]
                print(f"\n{index_name} ({index_code}):")
                print(f"  原始抛盘日总数: {result['raw_total']}")
                print(f"  加权抛盘日总数: {result['weighted_total']}")
                print(f"  市场状态: {result['market_status']}")
                
                # 建议
                if result['weighted_total'] >= 8:
                    print(f"  建议: 🛑 暂停选股，市场处于熊市状态")
                elif result['weighted_total'] >= 5:
                    print(f"  建议: ⚠️ 谨慎选股，市场处于承压状态")
                else:
                    print(f"  建议: ✅ 正常选股，市场状态正常")
        
        print("\n注: 加权总数考虑了重抛盘日（跌幅≥-1.5%且放量计为2个）")
        print("     未考虑确认日抵消机制（涨幅≥1.5%且放量可抵消1个抛盘日）")
        print("=" * 70)
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保在项目根目录运行此脚本")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"回测过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()