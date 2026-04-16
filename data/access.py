#!/usr/bin/env python3
# 统一数据访问层
# 封装所有对lixinger.db的访问，提供干净的接口

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class DataAccess:
    """统一数据访问接口"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 默认数据库路径
            self.db_path = Path(__file__).parent / "database" / "lixinger.db"
        else:
            self.db_path = Path(db_path)
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")
        
        logger.info(f"初始化数据访问层，数据库: {self.db_path}")
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(str(self.db_path))
    
    # === 市场数据 ===
    
    def get_market_indices(self) -> List[Dict]:
        """获取所有指数列表"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT stock_code as index_code, stock_code as name 
                FROM index_daily_kline 
                ORDER BY stock_code
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_index_data(self, index_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取指数日K线数据"""
        query = """
            SELECT date, open, high, low, close, volume, change as change_pct,
                   stock_code as index_code
            FROM index_daily_kline 
            WHERE stock_code = ? AND kline_type = 'normal'
        """
        params = [index_code]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date"
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            return df
    
    # === 个股数据 ===
    
    def get_stock_list(self) -> List[Dict]:
        """获取股票列表（基础信息）"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT stock_code, name, list_date, delist_date, exchange_location
                FROM stock_basic
                ORDER BY stock_code
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stock_data(self, stock_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取个股日K线数据（前复权价）"""
        query = """
            SELECT date, open, high, low, close, volume, turnover, change_pct
            FROM daily_kline 
            WHERE stock_code = ?
        """
        params = [stock_code]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date"
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            return df
    
    def get_stock_weekly_data(self, stock_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取个股周K线数据"""
        query = """
            SELECT week_start_date as date, open, high, low, close, volume
            FROM weekly_kline 
            WHERE stock_code = ?
        """
        params = [stock_code]
        
        if start_date:
            query += " AND week_start_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND week_end_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY week_start_date"
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            return df
    
    # === 行业数据 ===
    
    def get_industry_list(self) -> List[Dict]:
        """获取行业列表"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT sw_industry_code, sw_industry_name
                FROM stock_sw_industry
                WHERE sw_industry_code IS NOT NULL
                ORDER BY sw_industry_code
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_industry_stocks(self, industry_code: str) -> List[str]:
        """获取行业成分股"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT stock_code
                FROM stock_sw_industry
                WHERE sw_industry_code = ?
            """, (industry_code,))
            return [row[0] for row in cursor.fetchall()]
    
    # === 相对强度数据 ===
    
    def get_rs_data(self, stock_code: str = None, date: str = None) -> pd.DataFrame:
        """获取相对强度数据"""
        query = "SELECT * FROM rs_daily WHERE 1=1"
        params = []
        
        if stock_code:
            query += " AND stock_code = ?"
            params.append(stock_code)
        if date:
            query += " AND date = ?"
            params.append(date)
        
        query += " ORDER BY date, stock_code"
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty and 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            return df
    
    # === 基本面数据 ===
    
    def get_fundamental_data(self, stock_code: str, date: str = None) -> pd.DataFrame:
        """获取基本面数据"""
        query = """
            SELECT date, pe_ttm, pb, ps_ttm, dividend_yield, roe, net_profit_yoy
            FROM fundamental_indicator
            WHERE stock_code = ?
        """
        params = [stock_code]
        
        if date:
            query += " AND date = ?"
            params.append(date)
        
        query += " ORDER BY date"
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty and 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            return df
    
    # === 工具函数 ===
    
    def get_trading_dates(self, start_date: str = None, end_date: str = None) -> List[str]:
        """获取交易日列表"""
        query = "SELECT DISTINCT date FROM daily_kline"
        params = []
        
        if start_date:
            query += " WHERE date >= ?"
            params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
        elif end_date:
            query += " WHERE date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [row[0] for row in cursor.fetchall()]
    
    def get_latest_trading_date(self) -> str:
        """获取最新交易日"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM daily_kline")
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
    
    def get_data_range(self) -> Tuple[str, str]:
        """获取数据日期范围"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MIN(date), MAX(date) FROM daily_kline")
            min_date, max_date = cursor.fetchone()
            return min_date, max_date
    
    # === 批量数据获取 ===
    
    def batch_get_stock_data(self, stock_codes: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """批量获取多只股票数据"""
        results = {}
        for code in stock_codes:
            try:
                df = self.get_stock_data(code, start_date, end_date)
                if not df.empty:
                    results[code] = df
            except Exception as e:
                logger.warning(f"获取股票 {code} 数据失败: {e}")
        return results


# 全局数据访问实例
_data_access = None

def get_data_access() -> DataAccess:
    """获取全局数据访问实例（单例模式）"""
    global _data_access
    if _data_access is None:
        _data_access = DataAccess()
    return _data_access


if __name__ == "__main__":
    # 测试数据访问层
    import logging
    logging.basicConfig(level=logging.INFO)
    
    data = get_data_access()
    
    # 测试基本功能
    print("测试数据访问层...")
    
    # 1. 获取数据范围
    min_date, max_date = data.get_data_range()
    print(f"数据日期范围: {min_date} 到 {max_date}")
    
    # 2. 获取最新交易日
    latest_date = data.get_latest_trading_date()
    print(f"最新交易日: {latest_date}")
    
    # 3. 获取指数列表
    indices = data.get_market_indices()
    print(f"指数数量: {len(indices)}")
    for idx in indices[:3]:
        print(f"  指数: {idx['index_code']} - {idx.get('name', '')}")
    
    # 4. 获取股票列表
    stocks = data.get_stock_list()
    print(f"股票数量: {len(stocks)}")
    for stock in stocks[:3]:
        print(f"  股票: {stock['stock_code']} - {stock['name']}")
    
    # 5. 获取中证全指数据示例
    if indices:
        index_code = indices[0]['index_code']
        df = data.get_index_data(index_code, "2024-01-01", "2024-01-31")
        print(f"指数 {index_code} 数据形状: {df.shape}")
        if not df.empty:
            print(f"  样本数据: {df.index[0]} - {df.index[-1]}")
    
    print("数据访问层测试完成！")