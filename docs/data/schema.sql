-- ============================================================
-- 理杏仁数据库表结构
-- 数据库: lixinger.db
-- 随接口开发逐步添加新表，不提前建空表
-- ============================================================

-- 1. 股票基础信息（API #1 股票信息）
CREATE TABLE IF NOT EXISTS stock_basic (
    stock_code     TEXT PRIMARY KEY,
    name           TEXT,
    market         TEXT,              -- a: A股
    exchange       TEXT,              -- sh/sz/bj
    area_code      TEXT,
    listing_status TEXT,              -- normally_listed / delisted / ...
    ipo_date       TEXT,              -- 上市日期
    delisted_date  TEXT,              -- 退市日期（可为空）
    fs_table_type  TEXT,              -- non_financial / bank / insurance / ...
    mutual_market_flag INTEGER DEFAULT 0,  -- 是否陆股通标的
    updated_at     TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 2. 日K线数据（API #4 K线数据）
CREATE TABLE IF NOT EXISTS daily_kline (
    stock_code     TEXT NOT NULL,
    date           TEXT NOT NULL,
    open           REAL,
    close          REAL,
    high           REAL,
    low            REAL,
    volume         INTEGER,
    amount         REAL,
    change_pct     REAL,              -- 涨跌幅
    turnover_rate  REAL,              -- 换手率
    complex_factor REAL,              -- 复权因子
    PRIMARY KEY (stock_code, date)
);

-- 2.5 周K线数据（由日K线聚合生成）
CREATE TABLE IF NOT EXISTS weekly_kline (
    stock_code     TEXT NOT NULL,
    week_start_date TEXT NOT NULL,   -- 该周第一个交易日 (YYYY-MM-DD)
    week_end_date   TEXT NOT NULL,     -- 该周最后一个交易日 (YYYY-MM-DD)
    year_week       TEXT NOT NULL,     -- 年周标识 (YYYY-WW)
    open            REAL,
    close           REAL,
    high            REAL,
    low             REAL,
    volume          INTEGER,           -- 周成交量 = 日成交量求和
    amount          REAL,              -- 周成交额 = 日成交额求和
    change_pct      REAL,              -- 周涨跌幅
    turnover_rate   REAL,              -- 周换手率 = 日换手率求和
    trade_days      INTEGER DEFAULT 1, -- 该周交易日数量
    PRIMARY KEY (stock_code, week_start_date)
);
CREATE INDEX IF NOT EXISTS idx_weekly_kline_date ON weekly_kline(week_end_date);
CREATE INDEX IF NOT EXISTS idx_weekly_kline_stock ON weekly_kline(stock_code);

-- 3. 所属行业（API #14 所属行业）
CREATE TABLE IF NOT EXISTS stock_industry (
    stock_code     TEXT NOT NULL,
    industry_code  TEXT NOT NULL,
    industry_name  TEXT,
    source         TEXT,              -- sw / cni / sw_2021
    updated_at     TEXT DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (stock_code, industry_code, source)
);

-- 4. 所属指数（API #13 所属指数）
CREATE TABLE IF NOT EXISTS stock_index (
    stock_code     TEXT NOT NULL,
    index_code     TEXT NOT NULL,
    index_name     TEXT,
    source         TEXT,              -- csi / cni / hsi / usi / lxri
    updated_at     TEXT DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (stock_code, index_code)
);

-- 5. 基本面指标（API #26 基本面数据：PE/PB/市值等）
--    采用 key-value 结构，字段由 metricsList 动态决定
CREATE TABLE IF NOT EXISTS fundamental_indicator (
    stock_code     TEXT NOT NULL,
    date           TEXT NOT NULL,
    metric_code    TEXT NOT NULL,      -- pe_ttm / pb / mc / pe_ttm.y3.cvpos 等
    value          REAL,
    PRIMARY KEY (stock_code, date, metric_code)
);

-- 6. 财报数据（API #27 财报数据：EPS/营收/ROE/现金流等）
--    采用 key-value 结构，指标格式如 q.ps.toi.t / q.m.roe.t 等
CREATE TABLE IF NOT EXISTS financial_statement (
    stock_code     TEXT NOT NULL,
    report_date    TEXT NOT NULL,      -- 财报日期 (date)
    announce_date  TEXT,              -- 公告日期 (reportDate)
    metric_code    TEXT NOT NULL,      -- q.ps.toi.t / q.bs.ta.t 等
    value          REAL,
    PRIMARY KEY (stock_code, report_date, metric_code)
);

-- 7. 股东人数（API #5 股东人数）
CREATE TABLE IF NOT EXISTS shareholders_num (
    stock_code     TEXT NOT NULL,
    date           TEXT NOT NULL,
    total          INTEGER,            -- 股东人数
    change_rate    REAL,               -- 变化比例
    price_change   REAL,               -- 股价涨跌幅
    PRIMARY KEY (stock_code, date)
);

-- 8. 申万一级行业（API #14 所属行业 sw 第一层）
CREATE TABLE IF NOT EXISTS stock_sw_industry (
    stock_code     TEXT PRIMARY KEY,
    industry_name  TEXT,              -- 申万一级行业名称
    industry_code  TEXT,              -- 申万一级行业指数代码（用于查询行业走势）
    updated_at     TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 9. 指数日K线（指数K线API）
CREATE TABLE IF NOT EXISTS index_daily_kline (
    stock_code     TEXT NOT NULL,     -- 指数代码
    date           TEXT NOT NULL,     -- 交易日期
    kline_type     TEXT NOT NULL,     -- normal / total_return
    open           REAL,
    close          REAL,
    high           REAL,
    low            REAL,
    volume         INTEGER,
    amount         REAL,
    change         REAL,              -- 涨跌幅
    PRIMARY KEY (stock_code, date, kline_type)
);

-- 10. RS强度每日计算结果
CREATE TABLE IF NOT EXISTS rs_daily (
    stock_code         TEXT NOT NULL,
    date               TEXT NOT NULL,
    industry_code      TEXT,
    industry_name      TEXT,

    -- 相对市场（中证全指 000985）
    rs_mkt_long        REAL,
    rs_mkt_mid         REAL,
    rs_mkt_short       REAL,

    -- 相对行业
    rs_ind_long        REAL,
    rs_ind_mid         REAL,
    rs_ind_short       REAL,

    -- 双强标记
    pattern            TEXT,

    -- 计算参数快照
    long_days          INTEGER,
    short_days         INTEGER,
    updated_at         TEXT DEFAULT (datetime('now', 'localtime')),

    PRIMARY KEY (stock_code, date)
);

-- ============================================================
-- 索引：加速常用查询
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_daily_kline_date ON daily_kline(date);
CREATE INDEX IF NOT EXISTS idx_daily_kline_stock ON daily_kline(stock_code);
CREATE INDEX IF NOT EXISTS idx_fundamental_stock_date ON fundamental_indicator(stock_code, date);
CREATE INDEX IF NOT EXISTS idx_fundamental_metric ON fundamental_indicator(metric_code);
CREATE INDEX IF NOT EXISTS idx_financial_stock_date ON financial_statement(stock_code, report_date);
CREATE INDEX IF NOT EXISTS idx_financial_metric ON financial_statement(metric_code);

-- 11. 指数成分股（指数成分股API）
--    记录某个指数在某个日期包含哪些股票
CREATE TABLE IF NOT EXISTS index_constituents (
    index_code     TEXT NOT NULL,     -- 指数代码，如 000300
    stock_code     TEXT NOT NULL,     -- 成分股代码
    date           TEXT NOT NULL,     -- 成分股日期
    updated_at     TEXT DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (index_code, stock_code, date)
);

CREATE INDEX IF NOT EXISTS idx_idx_const_idx ON index_constituents(index_code);
CREATE INDEX IF NOT EXISTS idx_idx_const_stock ON index_constituents(stock_code);
CREATE INDEX IF NOT EXISTS idx_idx_const_date ON index_constituents(date);

-- 12. 指数成分股权重（成分股权重API）
CREATE TABLE IF NOT EXISTS index_constituent_weightings (
    index_code     TEXT NOT NULL,
    stock_code     TEXT NOT NULL,
    date           TEXT NOT NULL,
    weighting      REAL,
    updated_at     TEXT DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (index_code, stock_code, date)
);

CREATE INDEX IF NOT EXISTS idx_icw_index ON index_constituent_weightings(index_code);
CREATE INDEX IF NOT EXISTS idx_icw_stock ON index_constituent_weightings(stock_code);

-- 13. 行业板块RS每日计算结果
CREATE TABLE IF NOT EXISTS sector_rs_daily (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    sector_code     TEXT NOT NULL,
    sector_name     TEXT,
    rs_ratio        REAL,
    score_20        REAL,
    score_120       REAL,
    score_250       REAL,
    rps_20          INTEGER,
    rps_120         INTEGER,
    rps_250         INTEGER,
    price_vs_ma200  REAL,
    ma200_trend     TEXT,
    daily_change_pct REAL,
    vol_ratio_20    REAL,
    vol_ratio_5     REAL,
    rs20_trend_up   INTEGER,
    is_leading      INTEGER DEFAULT 0,
    is_momentum     INTEGER DEFAULT 0,
    is_setup        INTEGER DEFAULT 0,
    is_compact      INTEGER DEFAULT 0,
    internal_status TEXT,
    internal_count  INTEGER,
    internal_weighted REAL,
    top_stocks      TEXT,
    created_at      TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(date, sector_code)
);

CREATE INDEX IF NOT EXISTS idx_srs_date ON sector_rs_daily(date);
CREATE INDEX IF NOT EXISTS idx_srs_leading ON sector_rs_daily(date, is_leading);
CREATE INDEX IF NOT EXISTS idx_srs_momentum ON sector_rs_daily(date, is_momentum);

-- ============================================================
-- 14. 大盘扫描：每日市场方向主表
-- ============================================================
CREATE TABLE IF NOT EXISTS market_direction_daily (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    date                    TEXT NOT NULL UNIQUE,

    -- 市场阶段
    market_phase            TEXT NOT NULL,          -- 上升趋势/震荡盘整/下降趋势/尝试反弹
    market_phase_confidence TEXT,                    -- 高/中/低
    risk_level              TEXT NOT NULL,           -- 正常/警戒/危险
    suggested_position_size REAL,                    -- 建议仓位比例 0-1

    -- 抛盘日分析
    distribution_days_25d   INTEGER,                 -- 最近25日抛盘日数量
    distribution_days_10d   INTEGER,                 -- 最近10日抛盘日数量
    distribution_trend      TEXT,                     -- 增加/减少/稳定
    distribution_warning    INTEGER DEFAULT 0,        -- 是否达到警戒线

    -- 追盘日分析
    ftd_exists              INTEGER DEFAULT 0,        -- 是否有有效追盘日
    ftd_date                TEXT,                      -- 追盘日发生日期
    ftd_day_count           INTEGER,                   -- 发生在第几天(4-7)
    ftd_index_code          TEXT,                      -- 触发追盘日的指数代码
    ftd_index_name          TEXT,                      -- 触发追盘日的指数名称
    ftd_gain_pct            REAL,                      -- 追盘日涨幅(%)
    ftd_volume_ratio        REAL,                      -- 追盘日成交量/前一日

    -- 吸筹日分析
    accumulation_days_10d       INTEGER,               -- 最近10日吸筹日总数
    standard_accumulation       INTEGER,               -- 标准吸筹日数量
    special_accumulation        INTEGER,               -- 特殊吸筹日数量
    breakout_accumulation       INTEGER,               -- 突破吸筹日数量
    accumulation_vs_distribution REAL,                 -- 吸筹/抛盘比率

    -- 指数间背离分析
    divergence_pattern      TEXT,                      -- 大盘强小盘弱/小盘强大盘弱/一致上涨/一致下跌
    style_divergence        TEXT,                      -- 成长强于价值/价值强于成长/均衡
    sector_rotation_summary TEXT,                      -- 行业轮动方向(JSON)

    -- 最强指数
    leading_index_code      TEXT,                      -- 最强指数代码
    leading_index_name      TEXT,                      -- 最强指数名称
    leading_index_rs        INTEGER,                   -- 最强指数RS评级
    top_indices             TEXT,                      -- Top N指数列表(JSON)

    -- 市场健康度评分
    market_health_score     INTEGER,                   -- 0-100综合评分
    health_score_components TEXT,                      -- 各维度评分(JSON)

    -- 市场宽度指标
    advance_decline_ratio   REAL,                      -- 上涨家数/下跌家数
    new_high_new_low_ratio  REAL,                      -- 新高家数/新低家数
    above_ma50_ratio        REAL,                      -- 站上50日线个股比例

    -- 综合判断
    summary                 TEXT,                      -- 市场综述
    action_suggestion       TEXT,                      -- 操作建议
    focus                   TEXT,                      -- 关注方向
    avoid                   TEXT,                      -- 回避方向
    stop_loss               TEXT,                      -- 止损条件
    strengths               TEXT,                      -- 优势信号(JSON)
    weaknesses              TEXT,                      -- 劣势信号(JSON)
    opportunities          TEXT,                      -- 机会方向(JSON)
    risks                   TEXT,                      -- 风险提示(JSON)
    warnings                TEXT,                      -- 风险警告(JSON)

    created_at              TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_mdd_date ON market_direction_daily(date);
CREATE INDEX IF NOT EXISTS idx_mdd_phase ON market_direction_daily(market_phase);
CREATE INDEX IF NOT EXISTS idx_mdd_score ON market_direction_daily(market_health_score);

-- ============================================================
-- 15. 大盘扫描：抛盘日明细
-- ============================================================
CREATE TABLE IF NOT EXISTS distribution_days_detail (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    date                    TEXT NOT NULL,
    index_code              TEXT NOT NULL,
    index_name              TEXT,

    -- 当日数据
    close                   REAL,
    change_pct              REAL,                     -- 涨跌幅(%)
    volume                  INTEGER,
    prev_volume             INTEGER,
    volume_ratio            REAL,                     -- 成交量/前一日

    -- 判断结果
    is_distribution         INTEGER DEFAULT 0,          -- 是否为抛盘日
    distribution_type       TEXT,                      -- 标准抛盘日/高位抛盘日/连续抛盘日
    decline_threshold_used  REAL,                      -- 使用的跌幅阈值

    -- 市场背景
    market_phase_at_date    TEXT,                      -- 当日市场阶段
    is_high_position        INTEGER DEFAULT 0,          -- 是否处于高位

    created_at              TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(date, index_code)
);

CREATE INDEX IF NOT EXISTS idx_ddd_date ON distribution_days_detail(date);
CREATE INDEX IF NOT EXISTS idx_ddd_index ON distribution_days_detail(index_code);
CREATE INDEX IF NOT EXISTS idx_ddd_dist ON distribution_days_detail(is_distribution);

-- ============================================================
-- 16. 大盘扫描：追盘日历史
-- ============================================================
CREATE TABLE IF NOT EXISTS follow_through_days (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    ftd_date                TEXT NOT NULL UNIQUE,

    -- 触发条件
    low_point_date          TEXT NOT NULL,              -- 阶段低点日期
    low_point_value         REAL,                       -- 阶段低点数值
    day_count               INTEGER,                    -- 发生在第几天(4-7)

    -- 触发指数
    index_code              TEXT NOT NULL,
    index_name              TEXT,

    -- 当日数据
    close                   REAL,
    gain_pct                REAL,                       -- 涨幅(%)
    volume                  INTEGER,
    prev_volume             INTEGER,
    volume_ratio            REAL,

    -- 验证状态
    is_valid                INTEGER DEFAULT 1,           -- 是否仍然有效
    invalidated_date        TEXT,                        -- 失效日期
    invalidated_reason      TEXT,                        -- 失效原因

    -- 后续表现
    follow_up_5d_return     REAL,                        -- 5日后涨跌幅
    follow_up_20d_return    REAL,                        -- 20日后涨跌幅

    created_at              TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_ftd_date ON follow_through_days(ftd_date);
CREATE INDEX IF NOT EXISTS idx_ftd_valid ON follow_through_days(is_valid);
CREATE INDEX IF NOT EXISTS idx_ftd_low ON follow_through_days(low_point_date);

-- ============================================================
-- 17. 大盘扫描：吸筹日明细
-- ============================================================
CREATE TABLE IF NOT EXISTS accumulation_days_detail (
    date                    TEXT NOT NULL,
    index_code              TEXT NOT NULL,
    index_name              TEXT,
    close                   REAL,
    change_pct              REAL,                       -- 涨跌幅(%)
    volume                  INTEGER,
    prev_volume             INTEGER,
    volume_ratio            REAL,                       -- 成交量/前一日
    amplitude               REAL,                       -- 振幅(high-low)
    close_position          REAL,                       -- 收盘位置(0-1, close在振幅中的位置)
    
    -- 吸筹日类型
    is_accumulation         INTEGER DEFAULT 0,          -- 是否为吸筹日
    is_standard_acc         INTEGER DEFAULT 0,          -- 标准吸筹日
    is_special_acc          INTEGER DEFAULT 0,          -- 特殊吸筹日
    is_breakout_acc         INTEGER DEFAULT 0,          -- 突破吸筹日
    accumulation_type       TEXT,                       -- 标准/特殊/突破
    
    created_at              TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(date, index_code)
);

CREATE INDEX IF NOT EXISTS idx_add_date ON accumulation_days_detail(date);
CREATE INDEX IF NOT EXISTS idx_add_index ON accumulation_days_detail(index_code);
CREATE INDEX IF NOT EXISTS idx_add_acc ON accumulation_days_detail(is_accumulation);
CREATE INDEX IF NOT EXISTS idx_add_std ON accumulation_days_detail(is_standard_acc);
CREATE INDEX IF NOT EXISTS idx_add_spec ON accumulation_days_detail(is_special_acc);
CREATE INDEX IF NOT EXISTS idx_add_bo ON accumulation_days_detail(is_breakout_acc);

-- ============================================================
-- 18. 融资融券数据
-- ============================================================
CREATE TABLE IF NOT EXISTS stock_margin (
    stock_code     TEXT NOT NULL,
    date           TEXT NOT NULL,
    mtaslb         REAL,              -- 融资融券余额
    mtaslb_fb      REAL,              -- 融资余额
    mtaslb_sb      REAL,              -- 融券余额
    mtaslb_mc_r    REAL,              -- 融资买入额
    npa_o_f_d1     REAL,              -- 1日净买入额
    npa_o_f_d5     REAL,
    npa_o_f_d10    REAL,
    npa_o_f_d20    REAL,
    npa_o_f_d60    REAL,
    npa_o_f_d120   REAL,
    npa_o_f_d240   REAL,
    fb_mc_rc_d1    REAL,              -- 1日融资偿还率
    fb_mc_rc_d5    REAL,
    fb_mc_rc_d10   REAL,
    fb_mc_rc_d20   REAL,
    fb_mc_rc_d60   REAL,
    fb_mc_rc_d120  REAL,
    fb_mc_rc_d240  REAL,
    PRIMARY KEY (stock_code, date)
);

CREATE INDEX IF NOT EXISTS idx_margin_date ON stock_margin(date);
CREATE INDEX IF NOT EXISTS idx_margin_stock ON stock_margin(stock_code);

-- ============================================================
-- 19. 股东人数V2
-- ============================================================
CREATE TABLE IF NOT EXISTS shareholders_num_v2 (
    stock_code     TEXT NOT NULL,
    date           TEXT NOT NULL,
    shnc_rln       INTEGER,           -- 最新股东人数
    shnc_d10       REAL,              -- 10日变化率
    shnc_d20       REAL,
    shnc_d30       REAL,
    shnc_d60       REAL,
    shnc_d90       REAL,
    shnc_qln       REAL,              -- 上期股东人数
    shnc_q1        REAL,              -- 1季度变化
    shnc_q2        REAL,
    shnc_q3        REAL,
    shnc_y1        REAL,              -- 1年变化
    shnc_y2        REAL,
    PRIMARY KEY (stock_code, date)
);

CREATE INDEX IF NOT EXISTS idx_shv2_date ON shareholders_num_v2(date);
CREATE INDEX IF NOT EXISTS idx_shv2_stock ON shareholders_num_v2(stock_code);

-- ============================================================
-- 20. 个股扫描候选日结果
-- ============================================================
CREATE TABLE IF NOT EXISTS stock_candidates_daily (
    stock_code         TEXT NOT NULL,
    date               TEXT NOT NULL,
    stock_name         TEXT,
    industry_name      TEXT,
    -- RS维度
    rs_score           REAL,
    rs_mkt_long        REAL,
    -- 基本面维度
    fundamental_score  REAL,
    eps_ttm            REAL,
    eps_yoy            REAL,
    revenue_yoy        REAL,
    roe                REAL,
    debt_ratio         REAL,
    -- 量价维度
    vol_price_score    REAL,
    price_vs_ma50      REAL,
    price_vs_ma200     REAL,
    dist_from_high     REAL,
    avg_volume_20d     REAL,
    volume_trend      TEXT,
    ma_trend          TEXT,
    -- 形态维度
    pattern_score      REAL,
    pattern_health     TEXT,
    pattern_type       TEXT,
    -- 综合
    composite_score    REAL,
    grade              TEXT,
    -- 标记
    is_watchlist       INTEGER DEFAULT 0,
    created_at         TEXT DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (stock_code, date)
);

CREATE INDEX IF NOT EXISTS idx_candidates_date ON stock_candidates_daily(date);
CREATE INDEX IF NOT EXISTS idx_candidates_grade ON stock_candidates_daily(date, grade);
CREATE INDEX IF NOT EXISTS idx_candidates_score ON stock_candidates_daily(date, composite_score DESC);

-- ============================================================
-- 21. 自选股
-- ============================================================
CREATE TABLE IF NOT EXISTS watchlist (
    stock_code     TEXT PRIMARY KEY,
    stock_name     TEXT,
    added_at       TEXT DEFAULT (datetime('now', 'localtime')),
    removed_at     TEXT,
    note           TEXT
);
