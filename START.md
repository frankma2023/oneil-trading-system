# 快速启动指南

## 🚀 一键启动

```bash
# 1. 进入项目目录
cd D:/hanako/investment

# 2. 安装依赖（如果尚未安装）
pip install -r requirements.txt

# 3. 启动系统
python run.py

# 4. 按照提示操作（默认选择1启动Web服务器）
```

## 🌐 访问地址

启动成功后，访问以下地址：

- **Web主界面**: http://0.0.0.0:8000 (或 http://127.0.0.1:8000)
- **API文档**: http://0.0.0.0:8000/docs (自动生成的Swagger UI)
- **大盘扫描页面**: http://0.0.0.0:8000/market_scan.html

## 🔍 系统测试

### 运行基础测试
```bash
python tests/test_basic.py
```

### 测试数据访问层
```bash
python -c "from data.access import get_data_access; d=get_data_access(); print(f'数据范围: {d.get_data_range()}')"
```

### 测试市场扫描器
```bash
python -c "
from data.access import get_data_access
from core.market.indicators import MarketScanner
data = get_data_access()
scanner = MarketScanner(data)
latest = data.get_latest_trading_date()
if latest:
    from datetime import datetime, timedelta
    end = datetime.strptime(latest, '%Y-%m-%d')
    start = (end - timedelta(days=30)).strftime('%Y-%m-%d')
    days = scanner.analyze_index(start_date=start, end_date=latest)
    print(f'分析完成: {len(days)} 个交易日')
    if days:
        stats = scanner.get_summary_statistics(days)
        print(f'抛盘日: {stats[\"distribution_days\"]}, 吸筹日: {stats[\"accumulation_days\"]}')
"
```

## 📁 目录结构验证

检查系统是否按七层架构正确组织：

```bash
# 检查关键目录
ls -la data/ core/ api/ web/ config/ scripts/ tests/ docs/ logs/

# 检查核心文件是否存在
ls -la data/access.py
ls -la core/market/indicators.py
ls -la core/backtest/framework.py
ls -la api/main.py
ls -la web/static/css/dark_theme.css
ls -la web/pages/market_scan/index.html
ls -la config/config.yaml
ls -la scripts/update_data.py
ls -la tests/test_basic.py
```

## ⚠️ 常见问题

### 1. 数据库文件不存在
**错误**: `FileNotFoundError: 数据库文件不存在`
**解决**: 从旧系统复制数据库文件
```bash
cp D:/hanako/oldsys/db/lixinger.db D:/hanako/investment/data/database/
```

### 2. 依赖安装失败
**解决**: 手动安装核心依赖
```bash
pip install fastapi uvicorn pandas numpy sqlalchemy
```

### 3. 端口被占用
**解决**: 修改端口或停止占用端口的进程
```bash
# 修改端口（编辑 api/main.py 或 run.py）
uvicorn api.main:app --reload --host 127.0.0.1 --port 8001

# 或查找占用进程
netstat -ano | findstr :8000
```

### 4. 页面无法访问
**检查**:
1. 服务器是否成功启动
2. 防火墙是否阻止访问
3. 浏览器是否支持现代JavaScript

## 🔧 开发模式

### 热重载开发
```bash
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### 调试模式
```bash
# 设置环境变量
set UVICORN_LOG_LEVEL=debug
uvicorn api.main:app --reload --log-level debug
```

### 仅运行后端测试
```bash
# 不启动Web服务器，直接测试核心功能
python run.py
# 然后选择选项2（运行市场扫描测试）或3（运行回测试测试）
```

## 📊 验证系统功能

### 验证1: 数据访问
```bash
python -c "
from data.access import get_data_access
d = get_data_access()
print('✅ 数据访问层正常')
print(f'  数据库: {d.db_path}')
print(f'  数据范围: {d.get_data_range()}')
print(f'  最新交易日: {d.get_latest_trading_date()}')
"
```

### 验证2: 市场扫描
```bash
python -c "
from data.access import get_data_access
from core.market.indicators import MarketScanner
import sys

data = get_data_access()
scanner = MarketScanner(data)

latest = data.get_latest_trading_date()
if latest:
    from datetime import datetime, timedelta
    end = datetime.strptime(latest, '%Y-%m-%d')
    start = (end - timedelta(days=10)).strftime('%Y-%m-%d')
    
    try:
        days = scanner.analyze_index(start_date=start, end_date=latest)
        print('✅ 市场扫描引擎正常')
        print(f'  分析交易日: {len(days)}')
        if days:
            stats = scanner.get_summary_statistics(days)
            print(f'  抛盘日: {stats[\"distribution_days\"]}')
            print(f'  吸筹日: {stats[\"accumulation_days\"]}')
    except Exception as e:
        print(f'❌ 市场扫描失败: {e}')
        sys.exit(1)
else:
    print('⚠️ 无交易日数据，但架构正常')
"
```

### 验证3: Web服务
```bash
# 在一个终端启动服务器
python api/main.py &

# 在另一个终端测试API
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/market/dates
```

## 🎯 下一步操作

系统启动成功后，您可以：

1. **浏览大盘扫描页面** - 查看市场健康度分析
2. **查看API文档** - 了解可用接口
3. **运行回测试测试** - 验证策略有效性
4. **开始新功能开发** - 基于现有架构

---

**提示**: 所有源代码都在相应目录中，架构清晰，便于扩展。从`core/`目录开始查看业务逻辑，从`web/pages/`目录开始查看前端页面。