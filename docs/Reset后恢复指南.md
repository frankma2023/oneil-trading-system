# RESET后恢复指南

## 🎯 一句话总结
**欧奈尔抛盘日扫描系统已完成开发**，包含核心算法、Web API和前端页面，可立即启动运行。

## 📍 项目位置
```
D:/hanako/investment/
├── data/database/lixinger.db    # 数据库 (已迁移)
├── api/main.py                  # Web服务器
├── web/pages/market_scan/index.html  # 大盘扫描页面
├── web/pages/backtest/index.html    # 抛盘日回测页面
├── api/endpoints/backtest.py        # 参数化回测API
└── core/market/distribution_scanner.py  # 抛盘日算法
```

## 🚀 立即运行
```bash
# 1. 进入项目目录
cd D:/hanako/investment

# 2. 启动Web服务器 (三选一)
python run.py                    # 选择选项3
python api/main.py               # 直接启动
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 3. 浏览器访问
# http://0.0.0.0:8000/market_scan.html
# http://0.0.0.0:8000/backtest.html
```

## 📚 核心文档
1. **算法规则**: `docs/investment/抛盘日定义.md`
2. **系统状态**: `docs/系统状态总结.md`
3. **快速备忘**: `docs/快速恢复备忘.md`
4. **知识索引**: `docs/知识库索引.md`

## 🔧 待修复问题
1. **测试编码**: `test_distribution_scanner.py` Windows GBK问题
2. **平盘日识别**: `is_flat_day` 逻辑需要检查
3. **前端数据**: 连接真实API替代mock数据

## ✅ 已完成新增功能
1. **参数化回测页面**: `backtest.html` - 交互式参数调整界面
2. **回测API**: `/api/backtest/distribution` - 15个参数可调
3. **详细统计**: 包含特殊抛盘日、盘中反转抛盘日统计
4. **实时验证**: 支持参数调整后立即计算市场状态

## 📊 抛盘日规则核心
- **平盘日**: |涨跌幅|<0.05% → 不计算
- **标准日**: 跌幅≤-0.1% + 放量 → 计1个
- **重抛日**: 跌幅≥-1.5% + 放量 → 计2个
- **确认日**: 涨幅≥1.5% + 放量 → 抵消1个
- **窗口**: 25交易日滚动

## 🎨 设计要点
- **颜色**: 红涨(#ef4444) 绿跌(#10b981) - A股语义
- **主题**: 暗色设计系统 (`dark_theme.css`)
- **布局**: 高信息密度，简约清爽
- **URL**: 直接访问 `market_scan.html`

## 🔗 API端点
```
GET /api/distribution/analyze    # 详细分析
GET /api/distribution/summary    # 摘要数据
GET /api/market/summary         # 市场摘要
POST /api/backtest/distribution # 参数化回测 (支持15个参数)
```

## 💡 用户偏好
1. **高密度** - 信息紧凑，减少空白
2. **简约** - 清爽，色彩克制
3. **实用** - 功能直接，无花哨
4. **A股语义** - 红涨绿跌
5. **URL简化** - 直接页面访问

## 📞 遇到问题
1. **数据库连接失败**
   - 检查 `data/database/lixinger.db` 是否存在
   - 运行 `python run.py` 选择选项1检查

2. **依赖缺失**
   - 运行 `pip install -r requirements.txt`

3. **页面无法访问**
   - 确保端口8000未被占用
   - 检查防火墙设置

---

**最后状态**: 抛盘日MVP完成，参数化回测系统已就绪  
**下一步**: 修复测试 + 完善前端数据对接 + 优化回测界面  
**核心价值**: 严格按欧奈尔理论的A股市场分析工具，支持参数验证和优化