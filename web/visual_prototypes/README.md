# 统一暗夜热力图主题系统

基于用户反馈创建的完整暗色主题设计系统，解决了以下问题：

## 解决的问题

1. **中国A股红涨绿跌颜色语义** - 修正了颜色系统，红色表示上涨，绿色表示下跌
2. **统一导航栏** - 添加了完整的导航系统，便于在页面间切换
3. **样式分离** - CSS和JavaScript已分离到统一文件中，便于维护和复用
4. **字体统一** - 建立了完整的字体层次系统
5. **日历日期控件** - 添加了统一的日期选择器，支持历史数据回看

## 文件结构

```
web/
├── static/
│   ├── dark_theme.css      # 统一暗色主题基础样式
│   ├── dark_nav.css        # 导航栏和日历控件样式
│   └── dark_nav.js         # 导航和日历交互逻辑
├── templates/
│   ├── base_dark.html      # 基础HTML模板
│   └── dark_nav.html       # 导航栏组件
└── visual_prototypes/
    ├── portfolio_dark_glass.html      # 投资组合暗色版
    ├── sell_signal_dark_glass.html    # 持仓哨兵暗色版
    ├── stock_screening_dark_glass.html # 个股扫描暗色版
    ├── sector_scan_dark_glass.html    # 行业扫描暗色版
    ├── finviz_dark_glass_dashboard.html # 大盘扫描暗色版
    └── index.html                     # 原型索引页
```

## 颜色语义系统（中国A股）

```css
--data-up: #ef4444;          /* 上涨：红色 */
--data-up-strong: #dc2626;   /* 强势上涨：深红色 */
--data-down: #10b981;        /* 下跌：绿色 */
--data-down-strong: #059669; /* 大幅下跌：深绿色 */
```

## 字体层次系统

- **显示字体**: `Space Grotesk` - 用于标题和重要显示
- **正文字体**: `Inter` - 用于正文和界面文本
- **等宽字体**: `IBM Plex Mono` - 用于代码、数字和表格数据

### 字号层级
- `--text-xs`: 0.7rem (10px) - 辅助文本、标签
- `--text-sm`: 0.8rem (11px) - 小号正文、表格文本
- `--text-base`: 0.9rem (13px) - 基础正文
- `--text-lg`: 1.0rem (14px) - 大号正文
- `--text-xl`: 1.1rem (16px) - 小标题
- `--text-2xl`: 1.3rem (18px) - 中标题
- `--text-3xl`: 1.5rem (21px) - 大标题
- `--text-4xl`: 2.0rem (28px) - 超大数字

## 如何使用

### 1. 创建新页面

使用基础模板创建新页面：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>页面标题 · 暗夜热力图</title>
    
    <!-- 引入统一CSS -->
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="../static/dark_theme.css">
    <link rel="stylesheet" href="../static/dark_nav.css">
    
    <!-- 页面特定CSS -->
    <style>
        /* 页面特定样式 */
    </style>
</head>
<body>
    <!-- 导航栏 -->
    <!-- 复制dark_nav.html内容或使用模板引擎引入 -->
    
    <!-- 页面内容 -->
    <div class="page-header">
        <h1 class="page-title">页面标题</h1>
        <div class="page-subtitle">页面副标题</div>
    </div>
    
    <div class="page-content">
        <!-- 页面内容 -->
    </div>
    
    <!-- 统一JavaScript -->
    <script src="../static/dark_nav.js"></script>
    
    <!-- 页面特定JavaScript -->
    <script>
        // 页面初始化逻辑
    </script>
</body>
</html>
```

### 2. 使用CSS变量

系统提供了一系列CSS变量，便于保持一致性：

```css
/* 使用颜色变量 */
.up { color: var(--data-up); }
.down { color: var(--data-down); }

/* 使用字体变量 */
.title { 
    font-family: var(--font-display);
    font-size: var(--text-2xl);
    font-weight: var(--font-weight-bold);
}

/* 使用间距变量 */
.card { 
    padding: var(--space-lg);
    margin-bottom: var(--space-md);
}

/* 使用圆角变量 */
.button { border-radius: var(--radius-md); }
```

### 3. 使用组件类

系统预定义了一些组件类：

```html
<!-- 卡片 -->
<div class="card">
    <div class="card-title">卡片标题</div>
    <div class="card-body">卡片内容</div>
</div>

<!-- 统计卡片 -->
<div class="stat-card">
    <div class="stat-title">统计标题</div>
    <div class="stat-value">123.45</div>
    <div class="stat-subtitle">统计说明</div>
</div>

<!-- 按钮 -->
<button class="btn">普通按钮</button>
<button class="btn btn-primary">主要按钮</button>
<button class="btn btn-sm">小按钮</button>

<!-- 输入框 -->
<input type="text" class="input" placeholder="输入文本">
<input type="text" class="input input-sm" placeholder="小输入框">

<!-- 标签页 -->
<div class="tab-bar">
    <div class="tab active">标签1</div>
    <div class="tab">标签2</div>
    <div class="tab">标签3</div>
</div>

<!-- 徽章 -->
<span class="badge badge-danger">危险</span>
<span class="badge badge-warning">警告</span>
<span class="badge badge-safe">安全</span>

<!-- 表格容器 -->
<div class="table-container">
    <table class="table">
        <!-- 表格内容 -->
    </table>
</div>
```

### 4. 日历日期选择器

系统内置了完整的日历日期选择器：

```javascript
// 监听日期变化
document.addEventListener('datechange', function(e) {
    const selectedDate = e.detail.date;
    console.log('选择的日期:', selectedDate);
    // 加载该日期的数据
});

// 编程方式设置日期
window.darkNav.setDate(new Date('2025-04-01'));

// 获取当前选中日期
const currentDate = window.darkNav.selectedDate;
```

## 响应式设计

系统已内置响应式设计：

- **≥1200px**: 完整桌面布局
- **992px-1199px**: 中等屏幕适配
- **768px-991px**: 平板适配
- **<768px**: 手机适配

## 浏览器兼容性

- Chrome 60+
- Firefox 55+
- Safari 11+
- Edge 79+

## 后续开发建议

1. **组件化开发** - 将常用组件进一步封装
2. **主题切换** - 添加亮色主题支持
3. **数据绑定** - 集成数据绑定框架
4. **性能优化** - 优化CSS和JS文件大小
5. **无障碍访问** - 改善无障碍访问支持

## 创建者说明

此系统基于用户反馈创建，重点解决了中国A股市场的特殊需求（红涨绿跌），同时保持了欧奈尔(CAN SLIM)投资体系的专业性要求。所有页面都遵循高信息密度、视觉舒适、操作便捷的设计原则。