#!/usr/bin/env python3
# 市场状态集成器
# 整合抛盘日和追盘日信号，提供综合市场状态判断
# 2026-04-14 开发

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class MarketState(Enum):
    """市场状态枚举"""
    HEALTHY_BULL = "health_bull"        # 健康牛市（可选股）
    PRESSURE_MARKET = "pressure"        # 承压市场（谨慎选股）
    BEAR_MARKET = "bear"                # 熊市（暂停选股）
    UNKNOWN = "unknown"                 # 未知


class MarketRecommendation(Enum):
    """操作建议枚举"""
    BUY_SIGNALS_OK = "buy_signals_ok"           # 可以选股买入
    CAUTION_BUY = "caution_buy"                 # 谨慎选股
    STOP_BUYING = "stop_buying"                 # 暂停选股
    REDUCE_POSITIONS = "reduce_positions"       # 减仓
    FULL_DEFENSE = "full_defense"               # 全面防守


@dataclass
class IntegratedMarketStatus:
    """综合市场状态"""
    # 基本信息
    timestamp: str
    index_code: str
    index_name: str
    
    # 抛盘日数据
    distribution_days_25: int           # 最近25日抛盘日数量（加权）
    distribution_raw_25: int            # 最近25日原始抛盘日数量
    distribution_status: str            # 抛盘日状态（正常/承压/熊市）
    
    # 追盘日数据
    has_active_followthrough: bool      # 是否有有效追盘日
    followthrough_date: Optional[str]   # 追盘日日期
    followthrough_type: Optional[str]   # 追盘日类型
    followthrough_strength: int         # 追盘日强度
    followthrough_status: str           # 追盘日状态（有效/失效/等待）
    
    # 综合状态
    market_state: MarketState           # 市场状态
    recommendation: MarketRecommendation  # 操作建议
    confidence: float                   # 信心度（0-1）
    
    # 详细信息
    distribution_details: Dict[str, Any]
    followthrough_details: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'timestamp': self.timestamp,
            'index_code': self.index_code,
            'index_name': self.index_name,
            
            'distribution_days_25': self.distribution_days_25,
            'distribution_raw_25': self.distribution_raw_25,
            'distribution_status': self.distribution_status,
            
            'has_active_followthrough': self.has_active_followthrough,
            'followthrough_date': self.followthrough_date,
            'followthrough_type': self.followthrough_type,
            'followthrough_strength': self.followthrough_strength,
            'followthrough_status': self.followthrough_status,
            
            'market_state': self.market_state.value,
            'recommendation': self.recommendation.value,
            'confidence': self.confidence,
            
            'distribution_details': self.distribution_details,
            'followthrough_details': self.followthrough_details,
        }


class MarketStateIntegrator:
    """市场状态集成器"""
    
    def __init__(self):
        """初始化集成器"""
        self.distribution_scanner = None
        self.followthrough_scanner = None
        
    def set_scanners(self, distribution_scanner, followthrough_scanner):
        """设置扫描器实例"""
        self.distribution_scanner = distribution_scanner
        self.followthrough_scanner = followthrough_scanner
    
    def get_integrated_status(self, 
                             index_code: str = "000985",
                             index_name: str = "中证全指") -> IntegratedMarketStatus:
        """
        获取综合市场状态
        
        规则：
        1. 抛盘日 ≥ 8 → 熊市，无论追盘日状态
        2. 抛盘日 5-7 → 承压市场
        3. 抛盘日 < 5 且 有有效追盘日 → 健康牛市
        4. 抛盘日 < 5 但 无有效追盘日 → 承压市场（等待信号）
        
        返回:
            IntegratedMarketStatus: 综合市场状态
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取抛盘日数据（模拟，实际应从抛盘日系统获取）
        distribution_data = self._get_distribution_data(index_code)
        
        # 获取追盘日数据（模拟，实际应从追盘日系统获取）
        followthrough_data = self._get_followthrough_data(index_code)
        
        # 计算市场状态
        market_state, recommendation, confidence = self._calculate_market_state(
            distribution_data, followthrough_data
        )
        
        # 创建综合状态对象
        status = IntegratedMarketStatus(
            timestamp=timestamp,
            index_code=index_code,
            index_name=index_name,
            
            distribution_days_25=distribution_data['weighted_total'],
            distribution_raw_25=distribution_data['raw_total'],
            distribution_status=distribution_data['market_status'],
            
            has_active_followthrough=followthrough_data['has_active'],
            followthrough_date=followthrough_data.get('active_date'),
            followthrough_type=followthrough_data.get('type'),
            followthrough_strength=followthrough_data.get('strength', 0),
            followthrough_status=followthrough_data['status'],
            
            market_state=market_state,
            recommendation=recommendation,
            confidence=confidence,
            
            distribution_details=distribution_data,
            followthrough_details=followthrough_data,
        )
        
        return status
    
    def _get_distribution_data(self, index_code: str) -> Dict[str, Any]:
        """
        获取抛盘日数据
        
        实际实现应从抛盘日系统获取数据
        """
        # 这里模拟返回数据，实际应调用抛盘日系统的API
        return {
            'weighted_total': 3,        # 加权抛盘日总数
            'raw_total': 2,             # 原始抛盘日数量
            'market_status': '正常状态', # 抛盘日状态
            'heavy_days': 1,            # 重抛盘日
            'confirmation_days': 2,     # 确认日
            'offset_applications': 2,   # 抵消应用次数
            'details': {
                'standard_days': 1,
                'special_days': 0,
                'intraday_reversal_days': 0,
            }
        }
    
    def _get_followthrough_data(self, index_code: str) -> Dict[str, Any]:
        """
        获取追盘日数据
        
        实际实现应从追盘日系统获取数据
        """
        # 这里模拟返回数据，实际应调用追盘日系统的API
        return {
            'has_active': True,                 # 是否有有效追盘日
            'active_date': '2026-04-10',        # 追盘日日期
            'type': 'standard',                 # 追盘日类型
            'strength': 2,                      # 强度
            'status': 'active',                 # 状态（active/failed/expired）
            'attempt_start': '2026-04-01',      # 反弹尝试起点
            'attempt_days': 10,                 # 尝试天数
            'dynamic_threshold': 0.016,         # 动态阈值
            'details': {
                'change_pct': 0.018,            # 涨幅
                'volume_ratio': 1.15,           # 成交量比率
                'position_in_range': 0.65,      # 区间位置
            }
        }
    
    def _calculate_market_state(self, 
                               distribution_data: Dict, 
                               followthrough_data: Dict) -> Tuple[MarketState, MarketRecommendation, float]:
        """
        计算市场状态和操作建议
        
        返回:
            tuple: (市场状态, 操作建议, 信心度)
        """
        weighted_distribution = distribution_data['weighted_total']
        has_active_followthrough = followthrough_data['has_active']
        followthrough_status = followthrough_data['status']
        
        confidence = 0.7  # 基础信心度
        
        # 规则1：抛盘日 ≥ 8 → 熊市
        if weighted_distribution >= 8:
            market_state = MarketState.BEAR_MARKET
            recommendation = MarketRecommendation.FULL_DEFENSE
            confidence = max(confidence, 0.9)  # 高信心度
            return market_state, recommendation, confidence
        
        # 规则2：抛盘日 5-7 → 承压市场
        if 5 <= weighted_distribution <= 7:
            market_state = MarketState.PRESSURE_MARKET
            
            if has_active_followthrough and followthrough_status == 'active':
                # 有追盘日信号，但仍需谨慎
                recommendation = MarketRecommendation.CAUTION_BUY
                confidence = 0.6
            else:
                # 无有效追盘日，更谨慎
                recommendation = MarketRecommendation.REDUCE_POSITIONS
                confidence = 0.7
            
            return market_state, recommendation, confidence
        
        # 规则3：抛盘日 < 5
        market_state = MarketState.HEALTHY_BULL
        
        if has_active_followthrough and followthrough_status == 'active':
            # 有有效追盘日 → 健康牛市
            recommendation = MarketRecommendation.BUY_SIGNALS_OK
            
            # 根据追盘日强度调整信心度
            strength = followthrough_data.get('strength', 1)
            if strength >= 3:
                confidence = 0.9
            elif strength == 2:
                confidence = 0.8
            else:
                confidence = 0.7
        else:
            # 无有效追盘日 → 转为承压市场（等待信号）
            market_state = MarketState.PRESSURE_MARKET
            recommendation = MarketRecommendation.CAUTION_BUY
            confidence = 0.5
        
        return market_state, recommendation, confidence
    
    def get_recommendation_details(self, status: IntegratedMarketStatus) -> Dict[str, Any]:
        """获取详细建议说明"""
        details = {
            'market_state': {
                'value': status.market_state.value,
                'description': self._get_state_description(status.market_state),
            },
            'recommendation': {
                'value': status.recommendation.value,
                'description': self._get_recommendation_description(status.recommendation),
                'actions': self._get_recommendation_actions(status.recommendation),
            },
            'confidence': {
                'value': status.confidence,
                'level': self._get_confidence_level(status.confidence),
            },
            'key_factors': self._get_key_factors(status),
        }
        
        return details
    
    def _get_state_description(self, state: MarketState) -> str:
        """获取状态描述"""
        descriptions = {
            MarketState.HEALTHY_BULL: "市场处于健康牛市状态，机构资金入场明显",
            MarketState.PRESSURE_MARKET: "市场处于承压状态，买卖力量平衡",
            MarketState.BEAR_MARKET: "市场处于熊市状态，抛压持续",
            MarketState.UNKNOWN: "市场状态未知，需要更多数据",
        }
        return descriptions.get(state, "未知状态")
    
    def _get_recommendation_description(self, recommendation: MarketRecommendation) -> str:
        """获取建议描述"""
        descriptions = {
            MarketRecommendation.BUY_SIGNALS_OK: "可以积极寻找买入信号，符合欧奈尔选股标准",
            MarketRecommendation.CAUTION_BUY: "谨慎选股，控制仓位，关注市场变化",
            MarketRecommendation.STOP_BUYING: "暂停选股，观察市场企稳信号",
            MarketRecommendation.REDUCE_POSITIONS: "减仓防守，降低风险敞口",
            MarketRecommendation.FULL_DEFENSE: "全面防守，清仓或极小仓位运行",
        }
        return descriptions.get(recommendation, "无明确建议")
    
    def _get_recommendation_actions(self, recommendation: MarketRecommendation) -> List[str]:
        """获取具体行动建议"""
        actions = {
            MarketRecommendation.BUY_SIGNALS_OK: [
                "可以使用口袋支点、杯柄形态等买入规则",
                "关注强势行业和个股",
                "设置合理的止损位",
            ],
            MarketRecommendation.CAUTION_BUY: [
                "降低仓位至50%以下",
                "只选择最强势的股票",
                "缩短持股周期",
                "严格止损",
            ],
            MarketRecommendation.STOP_BUYING: [
                "停止开新仓",
                "逐步减持仓位",
                "关注抛盘日数量变化",
                "等待追盘日信号",
            ],
            MarketRecommendation.REDUCE_POSITIONS: [
                "减仓至30%以下",
                "只保留最强的持仓",
                "增加现金比例",
                "等待市场企稳",
            ],
            MarketRecommendation.FULL_DEFENSE: [
                "清仓或仅保留极小仓位",
                "增加现金储备",
                "关注宏观经济变化",
                "等待明确的牛市信号",
            ],
        }
        return actions.get(recommendation, [])
    
    def _get_confidence_level(self, confidence: float) -> str:
        """获取信心等级"""
        if confidence >= 0.8:
            return "高"
        elif confidence >= 0.6:
            return "中"
        else:
            return "低"
    
    def _get_key_factors(self, status: IntegratedMarketStatus) -> List[Dict[str, Any]]:
        """获取关键因素"""
        factors = []
        
        # 抛盘日因素
        if status.distribution_days_25 >= 8:
            factors.append({
                'factor': '抛盘日数量',
                'value': f"{status.distribution_days_25}个（熊市阈值）",
                'impact': 'negative',
                'weight': 0.4,
            })
        elif status.distribution_days_25 >= 5:
            factors.append({
                'factor': '抛盘日数量',
                'value': f"{status.distribution_days_25}个（承压阈值）",
                'impact': 'warning',
                'weight': 0.3,
            })
        else:
            factors.append({
                'factor': '抛盘日数量',
                'value': f"{status.distribution_days_25}个（正常范围）",
                'impact': 'positive',
                'weight': 0.2,
            })
        
        # 追盘日因素
        if status.has_active_followthrough:
            factors.append({
                'factor': '追盘日信号',
                'value': f"有效（强度{status.followthrough_strength}）",
                'impact': 'positive',
                'weight': 0.3,
            })
        else:
            factors.append({
                'factor': '追盘日信号',
                'value': "无有效信号",
                'impact': 'warning',
                'weight': 0.2,
            })
        
        # 市场状态因素
        if status.market_state == MarketState.HEALTHY_BULL:
            factors.append({
                'factor': '市场趋势',
                'value': '健康牛市',
                'impact': 'positive',
                'weight': 0.3,
            })
        elif status.market_state == MarketState.BEAR_MARKET:
            factors.append({
                'factor': '市场趋势',
                'value': '熊市',
                'impact': 'negative',
                'weight': 0.4,
            })
        else:
            factors.append({
                'factor': '市场趋势',
                'value': '承压震荡',
                'impact': 'neutral',
                'weight': 0.2,
            })
        
        # 排序（按权重）
        factors.sort(key=lambda x: x['weight'], reverse=True)
        
        return factors