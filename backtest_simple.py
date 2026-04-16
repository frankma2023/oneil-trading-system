#!/usr/bin/env python3
"""
欧奈尔抛盘日回测 - 简化版
回测最近25个交易日中证全指和沪深300的抛盘日数量
"""

import sys
import os
from pathlib import Path
import pandas as pd

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    print("=" * 70)
    print("欧奈尔抛盘日回测 - 最近25个交易日")
    print("=" * 70)
    
    try:
        from data.access import get_data_access
        from core.market.distribution_scanner import DistributionScanner
        
        # 初始化
        data = get_data_access()
        scanner = DistributionScanner()
        
        # 获取最新交易日
        latest_date = data.get_latest_trading_date()
        print(f"最新交易日: {latest_date}")
        
        # 获取最近25个交易日
        trading_dates = data.get_trading_dates(end_date=latest_date)
        if len(trading_dates) < 25:
            analysis_dates = trading_dates
        else:
            analysis_dates = trading_dates[-25:]
        
        start_date = analysis_dates[0]
        end_date = analysis_dates[-1]
        print(f"分析期间: {start_date} 到 {end_date}")
        print(f"分析天数: {len(analysis_dates)} 个交易日")
        print()
        
        # 分析指数
        indices = [("000985", "中证全指"), ("000300", "沪深300")]
        
        results = {}
        
        for index_code, index_name in indices:
            print(f"分析 {index_name} ({index_code}):")
            
            # 获取数据
            df = data.get_index_data(index_code, start_date, end_date)
            if df.empty:
                print("  无数据，跳过")
                continue
            
            # 按日期排序
            df_sorted = df.sort_index().reset_index()
            
            # 分析每个交易日
            distribution_days = []
            distribution_counts = {
                "standard": 0,
                "special": 0, 
                "intraday_reversal": 0,
                "heavy": 0,
                "confirmation": 0,
                "flat": 0,
            }
            weighted_total = 0
            
            for i in range(1, len(df_sorted)):
                current = df_sorted.iloc[i]
                prev = df_sorted.iloc[i-1]
                
                # 准备交易日数据
                day = scanner.prepare_trading_day(current, prev)
                
                # 分析抛盘日
                day = scanner.analyze_distribution_day(day)
                
                # 统计
                if day.is_flat_day:
                    distribution_counts["flat"] += 1
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
                        distribution_counts["standard"] += 1
                    elif day.distribution_type.value == "special":
                        distribution_counts["special"] += 1
                    elif day.distribution_type.value == "intraday_reversal":
                        distribution_counts["intraday_reversal"] += 1
                    
                    if day.distribution_weight == 2:
                        distribution_counts["heavy"] += 1
                    
                    weighted_total += day.distribution_weight
                
                if day.is_confirmation_day:
                    distribution_counts["confirmation"] += 1
            
            raw_total = distribution_counts["standard"] + distribution_counts["special"] + distribution_counts["intraday_reversal"]
            
            # 市场状态
            if weighted_total >= 8:
                market_status = "熊市状态"
            elif weighted_total >= 5:
                market_status = "承压状态"
            else:
                market_status = "正常状态"
            
            # 显示结果
            print(f"  平盘日: {distribution_counts['flat']}")
            print(f"  标准抛盘日: {distribution_counts['standard']}")
            print(f"  特殊抛盘日: {distribution_counts['special']}")
            print(f"  盘中反转抛盘日: {distribution_counts['intraday_reversal']}")
            print(f"  重抛盘日(计为2个): {distribution_counts['heavy']}")
            print(f"  确认日: {distribution_counts['confirmation']}")
            print(f"  原始抛盘日总数: {raw_total}")
            print(f"  加权抛盘日总数: {weighted_total}")
            print(f"  市场状态: {market_status}")
            
            # 详细抛盘日列表
            if distribution_days:
                print(f"  抛盘日详细列表:")
                for d in distribution_days:
                    print(f"    {d['date']}: {d['type']} (权重:{d['weight']}, 涨跌幅:{d['change_pct']:.2%}, 成交量比:{d['volume_ratio']:.2f})")
            else:
                print(f"  无抛盘日")
            
            print()
            
            # 保存结果
            results[index_code] = {
                'name': index_name,
                'raw_total': raw_total,
                'weighted_total': weighted_total,
                'market_status': market_status,
                'distribution_days': distribution_days,
            }
        
        # 总结
        print("=" * 70)
        print("回测总结")
        print("=" * 70)
        
        for index_code, index_name in indices:
            if index_code in results:
                r = results[index_code]
                print(f"\n{index_name} ({index_code}):")
                print(f"  原始抛盘日总数: {r['raw_total']}")
                print(f"  加权抛盘日总数: {r['weighted_total']}")
                print(f"  市场状态: {r['market_status']}")
                
                if r['weighted_total'] >= 8:
                    print(f"  建议: 暂停选股，市场处于熊市状态")
                elif r['weighted_total'] >= 5:
                    print(f"  建议: 谨慎选股，市场处于承压状态")
                else:
                    print(f"  建议: 正常选股，市场状态正常")
        
        print("\n注: 加权总数考虑了重抛盘日（跌幅≥-1.5%且放量计为2个）")
        print("     未考虑确认日抵消机制（涨幅≥1.5%且放量可抵消1个抛盘日）")
        print("=" * 70)
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()