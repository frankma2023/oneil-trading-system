# 欧奈尔投资系统

基于威廉·欧奈尔（William O'Neil）投资理念的专业投资分析系统。全新开发，只复用历史数据和API接口。

## 🎯 项目目标

构建一个完整的欧奈尔投资工作流系统，包括7个核心功能：

1. **大盘扫描** - 市场健康度、抛盘日/吸筹日/追盘日识别
2. **行业扫描** - 行业相对强度、轮动分析
3. **个股筛选** - CAN SLIM评分、相对强度分析
4. **形态识别** - 欧奈尔形态（杯柄、双重底等）识别
5. **回测实验室** - 策略验证、参数优化
6. **持仓管理** - 仓位管理、信号监控
7. **总览仪表板** - 系统概览、风险监控

## 🏗️ 系统架构（七层结构）

```
investment/
├── data/           # 数据层 - 所有数据相关
│   ├── database/   # SQLite数据库 (lixinger.db)
│   ├── api/        # 理杏仁API客户端 (复用)
│   └── access.py   # 统一数据访问接口
│
├── core/           # 核心层 - 欧奈尔算法和回测
│   ├── market/     # 大盘扫描引擎 ✅
│   ├── industry/   # 行业扫描引擎 (待开发)
│   ├── stocks/     # 个股筛选引擎 (待开发)
│   ├── patterns/   # 形态识别引擎 (待开发)
│   ├── backtest/   # 回测框架 ✅
│   ├── portfolio/  # 投资组合管理 (待开发)
│   └── utils/      # 工具函数 (待开发)
│
├── api/            # API层 - FastAPI Web服务
│   └── main.py     # 主应用 ✅
│
├── web/            # 前端层 - 7个功能页面
│   ├── static/     # 设计系统 (CSS/JS) ✅
│   ├── templates/  # HTML模板 ✅
│   └── pages/      # 功能页面 ✅
│       ├── market_scan/    # 大盘扫描 ✅
│       ├── industry_scan/  # 行业扫描 (待开发)
│       ├── stock_screen/   # 个股筛选 (待开发)
│       ├── pattern_scan/   # 形态识别 (待开发)
│       ├── backtest_lab/   # 回测实验室 (待开发)
│       ├── portfolio_mgmt/ # 持仓管理 (待开发)
│       └── dashboard/      # 总览仪表板 (待开发)
│
├── config/         # 配置层 - 所有参数配置 ✅
├── scripts/        # 脚本层 - 自动化任务 ✅
├── tests/          # 测试层 - 完整测试套件 ✅
├── docs/           # 文档层 - 详细文档 ✅
└── logs/           # 日志层 - 系统日志 ✅
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd investment

# 创建虚拟环境（推荐）
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库准备

从旧系统复制数据库文件：
```bash
# 将 oldsys/db/lixinger.db 复制到 investment/data/database/
cp oldsys/db/lixinger.db investment/data/database/
```

### 3. 启动系统

```bash
# 方式1: 使用启动脚本
python run.py

# 方式2: 直接启动Web服务器
python api/main.py

# 方式3: 使用uvicorn
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. 访问系统

- Web界面: http://0.0.0.0:8000 (或 http://127.0.0.1:8000)
- API文档: http://0.0.0.0:8000/docs
- 大盘扫描页面: http://0.0.0.0:8000/market_scan.html

## 📊 核心功能

### 大盘扫描 (已完成MVP)
- 抛盘日检测（标准、假阳线、日内反转）
- 吸筹日检测
- 追盘日识别
- 市场健康度评分 (0-100)
- 25日滑动窗口计数
- 实时市场信号生成

### 回测框架 (基础完成)
- 参数化策略回测
- 多维度绩效评估
- 参数扫描和优化
- 结果缓存和比较

### 统一设计系统
- 暗色主题，专业交易员风格
- 中国A股红涨绿跌颜色语义
- 响应式设计，移动友好
- 高信息密度布局

## 🔧 技术栈

### 后端
- **Web框架**: FastAPI (高性能，自动API文档)
- **数据处理**: Pandas, NumPy, Ta-Lib
- **数据库**: SQLAlchemy + SQLite
- **任务调度**: APScheduler (未来)

### 前端
- **核心**: HTML5, CSS3, JavaScript (ES6+)
- **图表**: ECharts (功能强大，中文友好)
- **设计**: 自定义暗色设计系统
- **构建**: 纯静态，无需构建工具

### 开发工具
- **代码质量**: black, flake8
- **测试**: pytest
- **文档**: FastAPI自动文档 + Markdown

## 📈 开发路线图

### 第1阶段：基础架构 (当前)
- ✅ 数据访问层
- ✅ 大盘扫描引擎
- ✅ 回测框架基础
- ✅ 统一设计系统
- ✅ 大盘扫描页面

### 第2阶段：核心功能 (2-3周)
- [ ] 行业扫描引擎
- [ ] 个股CAN SLIM评分
- [ ] 形态识别基础
- [ ] 回测实验室页面
- [ ] 行业扫描页面

### 第3阶段：完整系统 (3-4周)
- [ ] 持仓管理模块
- [ ] 信号监控系统
- [ ] 数据管道自动化
- [ ] 剩余功能页面
- [ ] 系统集成测试

### 第4阶段：高级功能 (未来)
- [ ] 机器学习辅助形态识别
- [ ] 实时信号推送
- [ ] 多用户支持
- [ ] 移动端应用
- [ ] 云部署

## 🔍 API文档

系统提供RESTful API接口，支持前端数据获取：

### 市场数据API
- `GET /api/market/dates` - 获取交易日列表
- `GET /api/market/analysis` - 分析指定时间段市场
- `GET /api/market/summary` - 获取市场摘要
- `GET /api/market/indices` - 获取指数列表

### 个股数据API
- `GET /api/stocks/search` - 搜索股票
- `GET /api/stocks/{code}` - 获取股票数据

### 回测API
- `GET /api/backtest/strategies` - 获取回测策略列表

## 🧪 测试

```bash
# 运行系统测试
python run.py  # 选择测试选项

# 运行单元测试
pytest tests/ -v

# 运行集成测试
pytest tests/integration/ -v
```

## 📁 目录结构详解

### data/ - 数据层
- `access.py` - 统一数据访问接口
- `database/lixinger.db` - SQLite数据库 (10年K线数据)
- `api/lixinger/` - 理杏仁API客户端 (复用)

### core/ - 业务逻辑
- `market/indicators.py` - 市场扫描引擎
- `backtest/framework.py` - 回测框架
- `portfolio/` - 投资组合管理 (待开发)
- `patterns/` - 形态识别 (待开发)

### web/ - 前端
- `static/css/dark_theme.css` - 统一设计系统
- `pages/market_scan/` - 大盘扫描页面
- `templates/` - HTML模板

### api/ - Web服务
- `main.py` - FastAPI主应用
- `endpoints/` - API端点模块

## 🔄 数据约定

### 百分比格式
- 数据库存储小数格式：`0.01` 表示 `1%`
- 配置参数使用小数格式
- 前端显示时转换为百分比

### A股颜色语义
- **红色** (`#ef4444`): 上涨，盈利
- **绿色** (`#10b981`): 下跌，亏损
- **蓝色** (`#60a5fa`): 正面，信息
- **黄色** (`#fbbf24`): 警告

### 前复权价格
- 所有K线分析基于前复权价格
- 数据库中的`daily_kline`表已存储前复权价

## 🤝 贡献指南

### 开发流程
1. 从`main`分支创建特性分支
2. 实现功能，添加测试
3. 提交代码，确保通过测试
4. 创建Pull Request
5. 代码审查后合并

### 代码规范
- 使用black格式化Python代码
- 使用flake8检查代码质量
- 添加类型注解
- 编写文档字符串

### 提交信息
使用约定式提交：
- `feat:` 新功能
- `fix:` Bug修复
- `docs:` 文档更新
- `style:` 代码格式
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具

## 📞 支持与反馈

如有问题或建议，请：

1. 查看项目文档
2. 提交Issue
3. 查看API文档 (`/docs`)
4. 运行系统测试诊断

## 📄 许可证

本项目仅供学习研究使用，不构成投资建议。数据来源：理杏仁API。

---

**开始投资于知识，收获于智慧。**