# API Portal — CLIProxyAPI 用户运营控制台

API Portal 是为 **CLIProxyAPI (CPA)** 与 **CPA Manager Plus (CPAMP)** 打造的多用户商业化运营端，支持用户注册登录、自助管理 API 密钥、用量明细对账、兑换码与在线充值，以及管理员运营管控、模型定价和收支统计。

- **前端**：Vue 3 + Vite，纯静态资源（打包约 130 KB），由本地构建打包上传，服务器免 Node.js。
- **后端**：Python 3.12+ (FastAPI + Uvicorn)，内置单页静态服务与定时对账调度。
- **数据**：本地 SQLite（`backend/data/portal.sqlite`），用量增量只读 CPAMP 的 `usage.sqlite`。

---

## 工作原理

```text
用户浏览器 ──HTTPS──▶ Nginx ──▶ API Portal (127.0.0.1:18400)
                                           │
                     ┌─────────────────────┴──────────────────────┐
                     ▼                                            ▼
     只读 CPAMP usage.sqlite（usage_events）          CPA 管理接口 /v0/management/api-keys
     按 sha256(key) 归属到用户，按模型价格扣费        密钥自动同步（余额耗尽/过期/超额自动停用）

用户的客户端 ──Bearer sk-xxx──▶ CLIProxyAPI (:8317) ──▶ 上游大模型
```

- **密钥同步**：用户创建的密钥自动写入 CPA；余额不足、停用或过期时自动从 CPA 移除，充值后自动恢复。不影响 CPA 原生密钥。
- **增量计费**：后台每 15 秒增量只读 CPAMP `usage_events` 表完成先用后扣，不消费 CPA usage queue，互不冲突。
- **独立持久化**：用户账户、密钥、流水、兑换码及系统设置均保存在本地 `portal.sqlite`。

---

## 项目结构

```text
api-portal/
├── backend/                   # 后端服务（Python 3.12+ / FastAPI）
│   ├── server.py              # 服务与命令行主入口
│   ├── runtime/               # 运行时编排：应用组装、CLI 命令、用量同步调度
│   ├── core/                  # 核心基础：.env 配置加载、SQLite 迁移、常量与安全工具
│   ├── api/                   # HTTP 接口层：认证、API 密钥、充值计费、用量明细等
│   ├── services/              # 业务逻辑层：用户管理、额度扣费、密钥生命周期等
│   ├── integrations/          # 外部集成：CPA 管理接口、CPAMP 数据库、易支付
│   ├── requirements/          # 依赖清单（base.txt 生产依赖 / dev.txt 开发测试）
│   ├── tests/                 # 单元测试与端到端集成测试用例
│   └── tools/devstack.py      # 本地一体化模拟环境（CPA / CPAMP / 易支付）
├── frontend/                  # 前端单页应用（Vue 3 + Vite）
│   ├── src/                   # 源代码：页面（views）、组件（components）、接口（api）等
│   ├── public/                # 静态资源与主题预加载脚本
│   └── vite.config.js         # 前端构建与开发代理配置
└── deploy/                    # 部署脚本与运维配置
    ├── deploy.example.sh      # 本地一键构建与部署脚本模板
    ├── api-portal.service     # Systemd 托管服务配置文件
    └── nginx.conf             # Nginx 反向代理配置参考
```

---

## 快速部署

假设部署在 `/opt/services/api-portal`，与 CPA、CPAMP 同台服务器。

### 1. 本地一键打包与发布

```bash
# 复制并配置服务器地址与 SSH 端口
cp deploy/deploy.example.sh deploy/deploy.sh
nano deploy/deploy.sh

# 自动在本地构建前端、打包并上传至服务器重启
bash deploy/deploy.sh
```

### 2. 服务器配置环境变量

首次部署时在服务器配置 `backend/core/.env`：

```bash
cd /opt/services/api-portal/backend/core
cp .env.example .env
nano .env
```

**关键必填项**：

| 配置项 | 默认值 / 示例 | 说明 |
| :--- | :--- | :--- |
| `PUBLIC_API_BASE` | `https://api.example.com` | 用户调用的 CPA 接口公网地址（控制台接入示例中展示） |
| `CPA_BASE_URL` | `http://127.0.0.1:8317` | 本机 CPA 服务地址 |
| `CPA_MANAGEMENT_KEY`| *(空)* | CPA 管理密钥**明文**（初始化 CPAMP 时的 Management Key） |
| `CPAMP_USAGE_DB` | `/opt/services/cpa-manager-plus/data/usage.sqlite` | CPAMP 用量数据库路径 |
| `CPAMP_PRICE_DISCOUNT` | `1.0` | 官方价折扣初始值（8 折填 `0.8`，`1` 为不打折），之后可在后台「系统设置」修改 |

### 3. 创建管理员与系统服务

```bash
cd /opt/services/api-portal/backend

# 创建初始管理员账号
.venv/bin/python server.py create-admin admin

# 配置开机自启
cp /opt/services/api-portal/deploy/api-portal.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now api-portal
```

### 4. Nginx 反向代理

```bash
cp /opt/services/api-portal/deploy/nginx.conf /etc/nginx/conf.d/api-portal.conf
# 修改 server_name 后重载并申请证书
nginx -t && systemctl reload nginx
certbot --nginx -d 你的域名
```

---

## 常用运维命令

所有命令在 `backend/` 目录下由虚拟环境执行：

```bash
# 创建管理员 / 提权已有用户
.venv/bin/python server.py create-admin <用户名>

# 重置用户密码并强制下线
.venv/bin/python server.py reset-password <用户名>

# 批量生成兑换码（支持充值券与赠送券，赠送券不计入充值统计）
.venv/bin/python server.py gen-codes --amount 50 --count 10 [--type recharge|gift] [--batch 批次名] [--expires-days 30]

# 手动调整用户余额（正数为充值，负数为扣款）
.venv/bin/python server.py credit <用户名> 100 --note "线下收款"
```

---

## 本地开发

项目内置 `tools/devstack.py` 模拟 CPA、CPAMP 与易支付网关：

```bash
# 1. 后端依赖安装
cd backend && python3 -m venv .venv
.venv/bin/python -m pip install -r requirements/dev.txt

# 2. 启动服务（分三个终端执行）
python3 tools/devstack.py run        # 终端 1：本地模拟 CPA/CPAMP (18399)
.venv/bin/python server.py           # 终端 2：后端服务 (18400)
cd frontend && npm run dev           # 终端 3：前端开发服务器 (5173)

# 3. 运行测试与格式检查
pytest backend/tests
ruff check backend && ruff format --check backend
cd frontend && npm run lint
```

---

## 关键注意事项

1. **单进程运行**：内置定时后台任务与 CPA 同步调度器，请保持单进程运行（不要增加 Uvicorn `--workers`）。
2. **CPA 密钥明文**：`CPA_MANAGEMENT_KEY` 必须填明文，认证错误会导致 CPA 安全机制封禁 IP。
3. **数据备份**：仅需定期备份数据库 `backend/data/portal.sqlite` 及配置文件 `backend/core/.env`。
