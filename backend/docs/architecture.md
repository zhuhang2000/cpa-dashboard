# 后端结构与维护规则

后端采用 FastAPI 和 Uvicorn，业务按账户、密钥、账务、定价、用量、设置六个领域组织。找代码时先确定业务，再区分 HTTP 接口与业务操作。管理员和普通用户的同类功能放在同一个业务模块。

## 从请求找到业务代码

一次创建密钥请求的路径是：

```text
POST /api/keys
  → api/api_keys.py:create_key          读取参数、确认登录、组装响应
  → services/api_keys.py:create        校验密钥规则、写入数据库
  → core/db.py:transaction             提交或回滚
  → runtime/sync.py:SyncWorker.trigger  唤醒同步
  → integrations/cpa.py:CPAClient      把允许调用的密钥同步到 CPA
```

`api/router.py` 汇总各业务路由。URL、HTTP 方法和权限声明就在对应处理函数旁边，不再另维护一份 URL 对照表。管理员登录后可访问 `/api/docs` 查看这些接口。

## 接口命名与排列

同一功能的用户版和管理员版，从路径和函数名就能看出对应关系：

| 资源 | 用户接口 | 管理员接口 |
| --- | --- | --- |
| 全站共用 | `GET /api/prices` → `list_prices` | `GET /api/admin/prices` → `admin_list_prices` |
| 属于某个用户 | `GET /api/keys` → `list_keys` | `GET /api/admin/users/{user_id}/keys` → `admin_list_keys` |

- 管理员处理函数一律以 `admin_` 开头；有对应的用户接口时，前缀后面的部分与用户接口完全相同。
- 管理员路径：全站共用的资源在 `/api/` 后加 `admin/`；属于某个用户的资源把 `/api/`（或 `/api/user/`）换成 `/api/admin/users/{user_id}/`。
- 前端 `frontend/src/api/` 的方法名跟处理函数一致：`list_keys` → `listKeys`，`admin_list_keys` → `adminListKeys`。
- 每个 `api/*.py` 先放共用辅助函数，再放用户接口，最后放管理员接口，两组分别以 `# ---- User endpoints ----`、`# ---- Administrator endpoints ----` 开头。前端各模块同样先列用户方法，空一行后列管理员方法。
- 每个 `services/*.py` 按调用方分组，依次为 `# ---- Shared ----`（用户和管理员都用，或后台也用）、`# ---- User operations ----`、`# ---- Administrator operations ----`、`# ---- Sync worker and CLI ----`（只给同步任务或命令行用）。新增函数放进它的调用方所在的组；调用方变了就挪到对应的组。只有一种调用方的文件（如 `settings.py`）不分组。

## 各目录负责什么

`backend/` 根目录保留 `server.py` 启动入口和 `pyproject.toml` 工具配置，其他源码与配套文件按用途归入目录：

```text
backend/
├── server.py
├── pyproject.toml
├── runtime/          # app.py、cli.py、sync.py：应用组装与运行编排
├── core/             # config.py、db.py、security.py、errors.py、constants.py
├── api/              # HTTP 适配
├── services/         # 六个业务域的规则和数据库操作
├── integrations/     # 外部系统适配
├── config/           # 唯一 config.json，首次生成，不入库
├── requirements/     # base.txt、dev.txt
├── docs/             # architecture.md
├── tests/
└── tools/
```

本机生成的 `.venv/`、`data/`、`data-dev/` 仍可放在 `backend/` 下，不属于源码。

| 位置 | 职责 | 不放在这里的内容 |
| --- | --- | --- |
| `server.py` | 稳定启动入口 | 业务规则、SQL、命令实现 |
| `runtime/app.py` | 创建 Runtime、组装 FastAPI、应用启动与关闭 | 各个业务流程 |
| `runtime/cli.py` | 参数解析、交互输入、调用服务、打印结果 | SQL、重复实现管理员或兑换码业务 |
| `api/` | HTTP 参数、权限、Cookie、响应字段、CSV 输出 | 数据库查询和写入 |
| `services/` | 业务规则、数据库查询、写入和事务 | Request、Response、FastAPI、App/Runtime 对象 |
| `integrations/` | 外部协议、字段适配、外部数据库读取 | 门户权限、余额决策、HTTP 接口响应 |
| `runtime/sync.py` | 线程生命周期、同步状态、重试和外部操作编排 | SQL、直接修改余额或用量表 |
| `core/db.py` | SQLite 连接、事务、建表迁移、通用 settings 存取 | 账户、订单、模型等具体业务流程 |
| `core/config.py` | 首次生成配置、读取固定文件、解析路径 | 管理后台可编辑设置的缓存和更新 |
| `core/security.py` | 密码哈希、随机令牌、进程内限流 | 数据库会话操作 |
| `core/errors.py` | 预期业务错误及现有公开错误信息 | 依赖 HTTP 框架的异常类型 |
| `core/constants.py` | 稳定角色、状态、版本、时间常量 | 会随请求变化的数据 |
| `config/config.json` | 唯一可编辑的部署配置 | Python 配置加载代码、数据库数据 |
| `requirements/` | 生产与开发依赖的版本清单 | 应用设置 |
| `docs/` | 架构和维护说明 | 可执行代码 |
| `tests/` | 可重复运行的自动化测试 | 真实配置、服务器密钥和真实数据 |
| `tools/` | 本地模拟环境与造数据工具 | 生产请求处理 |

`api/dependencies.py` 集中管理请求数据库连接、当前用户、管理员权限、CSRF、Cookie 和通用参数解析；`api/middleware.py` 负责请求大小、安全响应头及 HEAD；`api/static.py` 负责 Vue 静态文件和页面路由回退。这些是 HTTP 层的组成部分。

## 六个业务模块的边界

`api/` 与 `services/` 使用相同的六个文件名，方便从接口直接找到对应操作。

| 模块 | 负责内容和数据 | 常见修改 |
| --- | --- | --- |
| `accounts.py` | 用户资料、密码、角色与封禁、登录会话；`users` 身份字段和 `sessions` | 邮箱修改、注册规则、登录方式、用户封禁 |
| `api_keys.py` | 密钥创建、状态、额度、过期、调用计数；`api_keys` | 密钥标签、额度规则、可调用状态 |
| `billing.py` | 金额转换、余额增减、流水、兑换码、支付订单；`users` 金额字段、`transactions`、`redeem_codes`、`orders` | 新充值渠道、兑换规则、调账 |
| `pricing.py` | 模型价格、价格选择、费用计算、模型目录和隐藏；`model_prices`、`seen_models`、隐藏模型设置 | 定价规则、展示模型、价格覆盖 |
| `usage.py` | 用量入库与去重、同步游标、明细、用户统计和运营报表；`usage_logs`、游标设置 | 新统计维度、导出字段、用量事件处理 |
| `settings.py` | 管理后台允许修改的设置及缓存；运行时设置记录 | 站点公告、注册开关、价格倍率 |

表不是拆分文件的单位。例如余额和用户身份同在 `users` 表，但余额写入统一由 `billing` 处理。报表需要跨表读取时由 `usage` 聚合；跨业务写入要调用所属服务的函数。

## 依赖与事务

`runtime/app.py` 负责组装各部分。请求与业务的通常依赖方向为 `api / runtime.cli / runtime.sync → services → core`。外部调用通过 `integrations`；集成适配器可以依赖标准库和独立的错误定义，不反过来调用服务、接口或运行编排。`core` 不导入 `runtime`、`api`、`services` 或 `integrations`。服务函数接收明确的连接、参数、配置或必要回调，不传入整个应用对象。

服务之间的当前关系为：

```text
accounts → billing
api_keys → billing（金额转换）
usage → accounts、api_keys、billing、pricing
billing、pricing、settings → core / integrations（按需）
```

每个请求通过 `get_connection` 获得一个连接，鉴权和处理函数共享它，请求结束或失败时关闭。后台任务和 CLI 自己打开并关闭连接。同步 SQLite 操作使用普通 `def`，由 FastAPI 在线程池执行；`async def` 中的同步数据库或网络操作需用 `run_in_threadpool`。

一个完整写操作只能有一个事务入口。批量用量入账由 `usage.apply_batch` 持有事务，依次完成事件去重写入、`billing.charge_usage` 扣费、`api_keys.record_usage` 计数、`pricing.touch_model` 更新模型、保存游标。任一步失败，整批回滚。参与该事务的辅助函数复用传入的连接，不再开启嵌套事务。

`billing.apply_credit` 和 `charge_usage` 要在调用方事务内执行；`billing.create_codes` 自己持有整批生成事务。增加或修改写操作时，应在函数说明里明确事务由谁负责。

## 新需求应该改哪里

| 需求 | 主要修改位置 | 一起检查 |
| --- | --- | --- |
| 用户增加一个资料字段 | `core/db.py` 增加迁移；`services/accounts.py` 读写；`api/accounts.py` 输出 | 注册、资料更新、管理员用户列表、旧数据库升级 |
| 增加一种支付平台 | `integrations/` 新适配器；`services/billing.py` 订单与到账；`api/billing.py` 下单/回调 | 签名、金额、重复回调、事务回滚 |
| 密钥增加新限制 | `services/api_keys.py` 生命周期和统一 `state`；`api/api_keys.py` 参数/输出 | 列表显示与 CPA 同步是否采用同一状态规则 |
| 增加一个统计图 | `services/usage.py` 查询；`api/usage.py` 返回字段 | 时间边界、空日期、分页或数据范围 |
| 管理后台增加设置 | `services/settings.py` 可编辑项；必要时补充首次配置生成字段 | 旧配置处理、数据库持久化、缓存刷新 |
| CPAMP 新增一种事件字段 | `integrations/cpamp.py` 读取/兼容；`services/usage.py` 处理；必要时 `core/db.py` 迁移 | 旧版 CPAMP 缺字段时的行为、重复导入 |
| 增加命令行操作 | `runtime/cli.py` 新子命令并调用对应服务 | 和 HTTP 操作共享核心规则、退出码与输出 |

新增业务如果属于这六类，先加入现有模块。出现独立规则和明确的修改原因后再建新模块；不要因为增加一张表就自动增加一层 `repository`、`manager` 或 `utils`。

## 代码风格与兼容性

- 文件用 `snake_case.py`，目录名描述用途；包的 `__init__.py` 保持轻量。
- 公开函数名描述动作，私有辅助函数加 `_`；金额单位用 `_micro`，毫秒时间用 `_ms` 或既有的 `_at` 字段名。
- SQL 使用参数绑定，放在对应服务旁边；`tools/devstack.py` 为历史造数据直接写 SQL 是开发工具例外。
- 统一使用 Ruff 格式与导入检查。服务的参数、返回值、事务要求和有意义的边界需要说明，不给逐行可读代码重复加注释。
- 当前迁移保留了原字段转换、错误消息和状态码。现有接口通过 `json_body` 在权限检查后解析；新接口可用 Pydantic 模型，但需明确校验失败的公开行为并测试。
- 数据库变更追加到 `core.db.MIGRATIONS`，不要修改已经在服务器执行过的历史迁移。
- 不在导入模块时初始化数据库、连接外部系统或启动线程。

`backend` 是唯一 Python 导入根目录，例如 `from services import accounts`、`from core.db import transaction`、`from runtime.app import Runtime, create_app`。使用 `python backend/server.py` 或在 `backend/` 下执行 `python server.py`，不要混用 `portal.*`、`backend.*` 或旧的 `from db import ...` 等路径。ASGI 工具可在 `backend/` 下使用 `.venv/bin/uvicorn runtime.app:create_app --factory`，日常启动使用 `.venv/bin/python server.py`。

## 配置与路径

唯一部署配置是 `backend/config/config.json`，由 `core.config.load_config()` 读取。首次执行 `python server.py init-config` 或普通启动时，若文件不存在，就用 `core/config.py` 中的 `DEFAULTS` 生成完整文件；文件存在后直接读取，修改文件并重启服务生效。

`DEFAULTS` 用于首次生成和字段完整性校验，已有配置不会在加载时与它合并。新增部署字段时，需要明确已有配置如何补充该字段。CLI 和 ASGI 使用同一个固定文件。

`data_dir`、`frontend_dir` 和相对的 `cpamp.usage_db` 都以 `backend/config/` 为基准。首次生成的 `../data` 与 `../../frontend/dist` 分别指向 `backend/data/` 与前端构建目录。本地模拟服务使用同一文件中的 `../data-dev` 和 `../data-dev/cpamp/usage.sqlite`。

网站名称、公告、注册开关、价格倍率等管理后台功能仍由 `services/settings.py` 保存到数据库；JSON 中的对应字段提供初始值，后台保存的业务设置继续生效。部署连接、密钥和路径等参数在 JSON 文件中维护。

旧版升级时，部署脚本负责一次迁移配置并调整相对路径，运行时不再承担旧位置查找。配置文件不纳入版本管理，也不随发布包覆盖。

## 运行与验证

应用使用一个 Uvicorn 进程，FastAPI lifespan 启动一个同步线程，退出时等待线程结束。增加 Web 进程前，先将同步任务独立部署，并处理进程内限流、缓存和同步状态的共享问题。

生产安装使用 `pip install -r requirements/base.txt`，开发安装使用 `pip install -r requirements/dev.txt`；`dev.txt` 通过 `-r base.txt` 包含生产依赖。具体测试、依赖和检查命令在 [README](../../README.md) 中。全部后端测试统一放在 `tests/`，与代码一起纳入版本管理。

数据库仍是配置中 `data_dir` 下的 `portal.sqlite`，HTTP URL 和原有业务子命令保持不变。`init-config` 只生成配置，不初始化数据库或启动服务。静态文件的 ETag、Range 等 HTTP 能力由 Starlette 提供。FastAPI 的生命周期和模块路由用法可参考 [官方生命周期文档](https://fastapi.tiangolo.com/advanced/events/) 与 [多模块应用文档](https://fastapi.tiangolo.com/tutorial/bigger-applications/)。
