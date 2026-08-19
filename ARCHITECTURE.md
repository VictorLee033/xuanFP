# xuanFP 架构契约（Architecture Contract）

> 本文档是 xuanFP 的**架构规范与更新约定**。今后每次改动都必须遵守本文档的分层与设计原则，
> 否则会破坏系统的可维护性与抗故障能力。改动前请先读一遍本文。

---

## 一、分层架构

代码按职责严格分层，**上层只允许依赖直接下层，禁止跨层、禁止反向依赖**：

```
┌─────────────────────────────────────────────────────────────┐
│  api/             HTTP 接口层（薄）                          │
│  职责：参数校验、调用 service、返回 JSON。不含业务逻辑。        │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  services/        应用服务层                                  │
│  职责：编排领域逻辑 + 仓库 + 数据源；扫描生命周期、进度上报。    │
└──────────────┬─────────────────────┬────────────────────────┘
               ▼                     ▼
┌──────────────────────┐  ┌───────────────────────────────────┐
│  domain/scanner/     │  │  repositories/  数据访问层          │
│  核心领域层（纯业务） │  │  职责：封装全部 SQL，唯一允许碰库的层 │
│  因子/评分/剔除/引擎  │  └────────────────┬──────────────────┘
└──────────┬───────────┘                   ▼
           │                    ┌─────────────────────────────┐
           │                    │  SQLite（WAL + 迁移 + 仓库）  │
           │                    └─────────────────────────────┘
           ▼
┌─────────────────────────────────────────────────────────────┐
│  datasources/     外部数据源（东财/腾讯/新浪）                 │
│  职责：只负责「取数 + 解析 + 多主机容灾」，不含业务规则          │
└─────────────────────────────────────────────────────────────┘
```

**依赖方向（只能从上往下，或平级调用下层）**：

- `api` → `services`
- `services` → `domain`（调用扫描引擎/因子）、`repositories`、`datasources`、`llm`
- `domain/scanner` → 只依赖 `errors`、纯函数（factors/scoring/indicators），**不读配置、不碰库、不碰网络**
- `repositories` → 只依赖 `database.py`
- `datasources` → 只依赖 `errors`、`config`（读密钥/URL）

**唯一例外**：`container.py` 是「组合根」，它知道所有具体实现，负责把依赖装配并注入。
业务代码一律通过构造函数接收依赖（依赖注入），**禁止在业务代码里 `import` 具体实现或读全局配置**。

---

## 二、SQLite 设计（核心约定）

1. **WAL 模式 + busy_timeout**：每个连接 `PRAGMA journal_mode=WAL`、`synchronous=NORMAL`、
   `busy_timeout=5000`，避免 "database is locked"。
2. **线程本地连接**：`Database.conn()` 返回当前线程独占连接，杜绝跨线程共享连接导致的
   事务快照/可见性不一致（历史踩坑）。
3. **autocommit**：连接以 `isolation_level=None` 打开，单条语句即提交，读取永远看到最新已提交数据。
4. **版本化迁移**：`database.py` 里的 `MIGRATIONS` 列表 + `schema_migrations` 表。
   - **只允许追加新迁移，禁止修改历史迁移**。
   - 加字段/加表/加索引 → 新增一条 `("000N_xxx", [SQL...])` 迁移。
5. **仓库封装 SQL**：所有 SQL 都写在 `repositories/*.py`，业务层绝不写 SQL。
   - 新表 → 新建 `xxx_repo.py` + 迁移 + 在 `container.py` 注册。

---

## 三、防御式编程约定

1. **类型化异常**（`errors.py`）：数据源失败抛 `DataSourceError`，配置错误抛 `ConfigurationError`，
   数据不存在抛 `NotFoundError`。最外层统一转友好 HTTP 响应（`main.py` 全局 handler）。
2. **结构化日志**：统一 `logging.getLogger(__name__)`；关键路径（扫描开始/结束/失败、数据源失败）
   必须打日志。日志同时写控制台与 `data/xuanfp.log`（滚动 5MB×3）。
3. **优雅降级**：数据源单点失败**不拖垮整个扫描**——单条数据失败置空、对应因子记缺失并触发维度降权；
   只有「行情快照」这类不可替代的核心数据失败才中止并给出明确提示。
4. **健康检查**：`GET /api/health` 返回 DB 状态与扫描运行态；新增关键依赖时同步扩展该端点。
5. **防御性校验**：外部输入（请求参数、外部数据）必须校验/兜底（`Query(..., ge=.., le=..)`、
   数值 `_num()` 容错等），不允许因为脏数据导致 500。

---

## 四、日常更新怎么做（规范）

| 需求 | 改哪里 | 注意 |
|---|---|---|
| 新增一个因子 | `domain/scanner/factors.py` 加函数 + 注册到 `FACTORS` 列表 + 在 `FACTOR_WEIGHTS` 配权重 | 保持纯函数、返回 `(score, value, note)`，score=None 表示该股缺此数据（维度内自动归一） |
| 调整评分权重 | 维度权重在 `config.yaml` 的 `scanner.weights`；因子权重在 `factors.py` 的 `FACTOR_WEIGHTS` | 两层权重：综合分 = Σ(维度分×维度权重)，维度分 = Σ(因子分×因子权重) |
| 新增数据源 | `datasources/` 新建客户端 + 在 `container.py` 注入 | 客户端只取数+容灾，含多主机回退 |
| 新增数据库表/字段 | `repositories/database.py` 追加迁移 + 新建/扩展 repo | 只追加迁移，不改历史 |
| 新增接口 | `api/schemas.py` + `api/router.py` 调 service | 路由只做校验+调用 |
| 新增业务编排 | `services/` 新建 service | 通过构造注入依赖 |

**修 bug 的定位顺序**：`api` 报错 → 查 `services` 编排 → 查 `domain` 逻辑 / `repositories` SQL /
`datasources` 取数；日志里 `name` 字段（模块名）会直接指到出问题的层。

---

## 五、目录结构

```
backend/
├── main.py            # 组合根入口（装配 + 异常兜底 + 静态挂载）
├── container.py       # 依赖容器（唯一知道所有实现的地方）
├── config.py          # 配置加载（config.yaml + config.local.yaml 合并）
├── logging_config.py  # 日志初始化
├── errors.py          # 类型化异常 + 友好信息
├── api/               # 接口层
│   ├── router.py      #   薄路由
│   └── schemas.py     #   Pydantic 模型
├── services/          # 应用服务层
│   ├── scan_service.py
│   ├── market_service.py
│   └── history_service.py
├── domain/scanner/    # 领域层（纯业务）
│   ├── engine.py      #   扫描流水线（依赖注入）
│   ├── filters.py     #   剔除 + 财务门槛
│   ├── factors.py     #   基础因子 + FACTOR_WEIGHTS（维度内因子权重）
│   ├── factors_extra.py # 细化技术指标/筹码/情绪因子（打分包装）
│   ├── technical.py   #   技术指标计算（MACD/KDJ/OBV/ATR/通道等）
│   ├── chip.py        #   筹码分布 CYQ 算法
│   ├── sentiment.py   #   单股情绪因子合成
│   ├── scoring.py     #   两层权重聚合（维度权重×因子权重）
│   └── indicators.py  #   基础技术指标（numpy）
├── repositories/      # 数据访问层
│   ├── database.py    #   SQLite WAL/迁移
│   ├── cache_repo.py
│   ├── scan_repo.py
│   └── report_repo.py
├── datasources/       # 外部数据源
│   ├── eastmoney.py
│   ├── fundamentals.py # 财务/分红/北向/龙虎榜/股东户数/两融
│   ├── news.py        #   个股新闻（舆情）
│   ├── tencent.py
│   └── sina.py
└── llm/               # LLM 报告
    └── reporter.py
```

---

## 六、环境约定

- 依赖（`pylibs/`）与前端 vendor（`frontend/static/vendor/`）由 `scripts/fetch_deps.py`、
  `scripts/fetch_frontend.py` 下载，**不入 git**。
- 密钥放 `config.local.yaml`（已 gitignore），`config.yaml` 只留空占位。
- 数据库默认 `data/xuanfp.db`，可用环境变量 `XUANFP_DB` 覆盖。
