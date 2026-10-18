# API Portal — CLIProxyAPI 用户控制台

给 CLIProxyAPI（CPA）+ CPA Manager Plus（CPAMP）配套的用户端：用户注册登录、自助创建 API 密钥、查看每一笔调用花销、兑换码 / 在线充值；管理员发兑换码、调余额、定价、看收支。

- **前端**：Vue 3 + Vite，构建产物是纯静态文件（约 300 KB，gzip 后约 80 KB），已构建好放在 `frontend/dist/`，服务器上不需要 Node.js。
- **后端**：Python 3.8+ 标准库（零第三方依赖），自带静态文件服务，常驻内存约 **25–30 MB**。
- **数据**：自己的 `backend/data/portal.sqlite`；用量 **只读** CPAMP 的 `usage.sqlite`。

## 工作原理

```
用户浏览器 ──HTTPS──▶ Nginx ──▶ API Portal (127.0.0.1:18400)
                                           │
                     ┌─────────────────────┴──────────────────────┐
                     ▼                                            ▼
     只读 CPAMP usage.sqlite（usage_events）          CPA 管理接口 /v0/management/api-keys
     按 api_key_hash = sha256(密钥) 归属到用户，       用户的密钥自动写入 / 移除 CPA 的 api-keys 列表
     按模型价格逐条扣费                               （余额不足、禁用、过期、超额度 → 自动移除）

用户的客户端 ──Bearer sk-xxx──▶ CLIProxyAPI (:8317) ──▶ 上游模型
```

- 新版 CPA 不再自己持久化用量统计，用量事件由 CPAMP 从 CPA 的 usage queue 取出并写入 SQLite。**门户不会去消费 usage queue**（队列是"取出即删除"，会和 CPAMP 抢数据），而是每 15 秒增量读取 CPAMP 的 `usage_events` 表。
- 门户只管理自己创建的密钥。CPA `api-keys` 里原有的密钥（比如你自己用的）**不会被改动**。
- 计费是"先用后扣"：请求完成 → CPAMP 落库 → 门户下一轮同步扣费，所以余额可能出现少量负数，充值后自动抵扣。

## 功能

| 用户端 | 管理端 |
| --- | --- |
| 注册 / 登录（可关闭注册、注册赠送） | 运营概况：用户数、今日/本月充值与消费、14 天收支图、同步状态告警 |
| 概览：余额、今日/本月消费、30 天消费趋势、模型消费排行、接入示例（cURL / Python / Claude Code） | 用户管理：搜索、调整余额（线下收款手动充值）、禁用账号、设为管理员 |
| API 密钥：创建（完整密钥只展示一次）、复制、单独额度上限、过期时间、启用/禁用、删除 | 兑换码：批量生成（面额/数量/批次/有效期）、复制全部、下载 TXT、停用 |
| 用量明细：按时间/密钥/模型/状态筛选，输入/缓存/输出/推理 tokens、费用、耗时，导出 CSV | 模型定价：自定义售价，或用 CPAMP 同步的官方价 × 倍率；控制前台是否展示；未定价模型告警 |
| 充值中心：兑换码充值、在线充值（易支付，可选）、余额流水、支付订单 | 系统设置：站点名称、API 地址、公告、开放注册、注册赠送、价格倍率、默认价格 |
| 模型价格：每百万 / 每千 tokens 两种单位 | 命令行：创建管理员、重置密码、生成兑换码、调整余额 |
| 个人设置：修改邮箱、修改密码（其他设备登录失效） | |

界面支持深色 / 浅色主题和手机端。

## 目录

```
api-portal/
├── backend/
│   ├── server.py              # 入口 + 命令行
│   ├── config.example.json    # 配置模板（复制为 config.json）
│   ├── portal/                # 认证、计费、CPA 同步、接口
│   └── tools/devstack.py      # 本地开发用的模拟 CPA / CPAMP / 易支付
├── frontend/
│   ├── src/                   # Vue 源码
│   └── dist/                  # 已构建的静态文件（部署用）
└── deploy/                    # systemd、Nginx 配置与服务器更新脚本
```

## 部署

以下假设部署到 `/opt/services/api-portal`，与 CPA、CPAMP 在同一台服务器。

### 1. 前置检查

- 服务器有 Python 3.8+：`python3 --version`
- 准备好 CPA 管理密钥的**明文**，也就是初始化 CPA Manager Plus 时填的 CPA Management Key。CPA 启动时会把 `config.yaml` 里明文的 `remote-management.secret-key` 改写成 `$2a$` 开头的 bcrypt 哈希，所以在 `config.yaml` 里看到哈希是正常的，门户需要的是哈希前的明文。忘了的话，把 `secret-key` 改成新的明文、重启 CPA，再到 CPA Manager Plus 里同步更新这个密钥。
- 门户与 CPA 在同一台机器，通过 `127.0.0.1` 访问，不需要打开 `allow-remote`。
- CPAMP 正常运行，并且在它的面板里能看到请求记录（说明 usage queue 采集正常）。

### 2. 获取代码

仓库里包含构建好的 `frontend/dist/`，服务器直接克隆即可，不需要 Node.js：

```bash
git clone <仓库地址> /opt/services/api-portal
```

`config.json` 和 `data/` 在 `.gitignore` 中，之后 `git pull` 不会覆盖它们。

### 3. 配置

```bash
cd /opt/services/api-portal/backend
cp config.example.json config.json
chmod 600 config.json
```

需要改的字段：

| 字段 | 说明 |
| --- | --- |
| `public_api_base` | 用户调用接口的地址（CPA 对外地址），显示在概览页的接入示例里 |
| `trust_proxy` | 放在 Nginx 后面时保持 `true` |
| `cpa.base_url` | CPA 地址，默认 `http://127.0.0.1:8317` |
| `cpa.management_key` | CPA 管理密钥的**明文**（见第 1 步）。也可以不写进文件，改用环境变量 `PORTAL_CPA_MANAGEMENT_KEY`。留空则不同步密钥，管理后台会提示。填错时门户只尝试一次就暂停重试，因为 CPA 对同一 IP 连续认证失败 5 次会封禁 30 分钟，而 CPA Manager Plus 也是从 127.0.0.1 调用 |
| `cpamp.usage_db` | CPAMP 数据库路径，默认 `/opt/services/cpa-manager-plus/data/usage.sqlite` |
| `pricing.cpamp_price_multiplier` | 官方美元价 × 倍率 = 售价（美元）。1 为原价，加价 20% 填 1.2 |
| `pricing.default_input_price` / `default_output_price` | 找不到任何价格的模型用的兜底价（$/百万 tokens）。都为 0 时这类模型**不扣费** |
| `signup_bonus` / `allow_register` | 注册赠送金额、是否开放注册（也可在管理后台改） |
| `payment.epay` | 在线支付，见下文；不用就保持 `enabled: false` |

余额、价格、兑换码面额统一以 `currency_symbol` 为单位，默认美元（$）。

### 4. 创建管理员

```bash
cd /opt/services/api-portal/backend
python3 server.py -c config.json create-admin admin
```

按提示输入密码。对已存在的用户执行这条命令会把他设为管理员。

### 5. 开机自启

```bash
cp /opt/services/api-portal/deploy/api-portal.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now api-portal
journalctl -u api-portal -f      # 看到 "listening on http://127.0.0.1:18400" 即启动成功
```

### 6. 域名与 HTTPS

`cp deploy/nginx.conf /etc/nginx/conf.d/api-portal.conf`，改域名后 `nginx -t && systemctl reload nginx`，再 `certbot --nginx -d 你的域名`。

门户默认只监听 `127.0.0.1:18400`，不要把这个端口直接暴露到公网。

### 7. 验证

1. 打开域名，用管理员登录，进入 **管理后台 → 运营概况**，"同步状态"两项都应显示 **正常**。
2. 注册一个普通账号，在 **充值中心** 用管理员生成的兑换码充值，创建一个密钥。
3. 用这个密钥调用一次 CPA，十几秒后（CPAMP 落库 + 门户同步）**用量明细** 出现记录、余额减少。
4. 管理员把该用户余额扣到 0 以下，几秒后该密钥调用 CPA 会返回 401；充值后自动恢复。

### 8. 更新版本

本机修改后，前端有改动先执行 `npm run build`（`frontend/dist/` 要一起提交），然后提交并推送：

```bash
cd frontend && npm run build && cd ..
git add -A && git commit -m "说明" && git push
```

服务器上拉取并重启（已是最新版本时不会重启）：

```bash
bash /opt/services/api-portal/deploy/update.sh
```

原来用压缩包部署的目录可以原地改成 git 管理，`config.json` 和 `data/` 不受影响：

```bash
cd /opt/services/api-portal
git init -b main
git remote add origin <仓库地址>
git fetch origin
git reset --hard origin/main
git branch --set-upstream-to=origin/main main
```

## 计费规则

单价按以下顺序确定（单位：$ / 百万 tokens）：

1. **管理后台 → 模型定价** 中为该模型设置的价格；
2. CPAMP 同步的官方价（models.dev 等，美元）× `cpamp_price_multiplier`；
3. `default_input_price` / `default_output_price`；
4. 都没有 → 不扣费，运营概况会提示"未定价模型"。

单次费用 = 未缓存输入 × 输入价 + 缓存读取 × 缓存读价 + 缓存写入 × 缓存写价 + 输出 × 输出价。缓存价未单独设置时，读取按输入价 × 0.1、写入按输入价 × 1.25。推理 tokens 已包含在输出中，失败的请求不收费（`pricing.bill_failed_requests` 可改）。tokens 的拆分使用 CPAMP 归一化后的字段（未缓存输入 / 缓存读取 / 缓存写入）；CPAMP 估算成本时用到的长上下文分档价、Priority 服务等级倍率，门户不会套用，需要的话请在"模型定价"里直接设置售价。

改价只影响之后的请求，已扣费的记录不会重算。

## 充值方式

**兑换码（默认可用）**：管理后台 → 兑换码 → 生成，复制或下载后通过发卡平台 / 微信等渠道出售。命令行也可以生成：

```bash
python3 server.py -c config.json gen-codes --amount 50 --count 20 --batch 2026-10
```

**线下收款**：管理后台 → 用户管理 → 调整余额，会记入该用户的余额流水。

**在线支付（易支付 / 彩虹易支付协议）**：在 `config.json` 中设置：

```json
"epay": {
  "enabled": true,
  "gateway": "https://你的易支付网关域名",
  "pid": "商户 ID",
  "key": "商户密钥",
  "channels": ["alipay", "wxpay"],
  "site_url": "https://你的控制台域名"
}
```

异步通知地址为 `https://你的控制台域名/api/pay/epay/notify`，同步跳转为 `/api/pay/epay/return`。门户会校验 MD5 签名、商户号与金额，订单只会入账一次。易支付属于第三方聚合支付，请自行确认服务商的资质与合规性。

## 常用命令

```bash
python3 server.py -c config.json                          # 启动（systemd 已代劳）
python3 server.py -c config.json create-admin <用户名>     # 创建/提升管理员
python3 server.py -c config.json reset-password <用户名>   # 重置密码并注销其所有登录
python3 server.py -c config.json gen-codes --amount 50 --count 10 [--batch 名称] [--expires-days 30]
python3 server.py -c config.json credit <用户名> 100 --note "线下转账"   # 负数为扣款
```

## 备份

只需要备份 `backend/data/portal.sqlite`（用户、密钥、余额、流水、兑换码）和 `backend/config.json`。在线备份可用：

```bash
sqlite3 /opt/services/api-portal/backend/data/portal.sqlite ".backup /root/portal-$(date +%F).sqlite"
```

## 本地开发

`backend/tools/devstack.py` 会在本机模拟 CPA 管理接口、CPAMP 数据库和易支付网关，并为已同步到"CPA"的密钥持续生成假请求，可以完整跑通"建密钥 → 产生用量 → 扣费 → 余额耗尽自动停用 → 充值恢复"。

```bash
# 终端 1：模拟服务（端口 18399）
cd backend && python3 tools/devstack.py run
# 终端 2：门户后端（读 config.dev.json，数据在 backend/data-dev/）
cd backend && python3 server.py -c config.dev.json
python3 server.py -c config.dev.json create-admin admin
python3 tools/devstack.py seed-demo        # 可选：demo / demo12345，带 30 天历史数据
# 终端 3：前端热更新（访问 http://127.0.0.1:5173，/api 代理到 18400）
cd frontend && npm install && npm run dev
```

修改前端后执行 `npm run build` 重新生成 `frontend/dist/`，和源码一起提交，再按"更新版本"同步到服务器。

## 安全说明

- CPA 管理密钥只保存在服务器的 `config.json`（或环境变量）中，前端拿不到。认证失败一次后门户就暂停自动重试，避免触发 CPA 的 IP 封禁。
- 密码使用 PBKDF2-SHA256（60 万轮）加盐存储；会话 Cookie 为 HttpOnly + SameSite=Lax，HTTPS 下自动加 Secure。
- 写操作要求自定义请求头并校验 Origin，防跨站请求伪造；登录、注册、兑换、下单都有频率限制。
- 用户密钥以明文保存在 `portal.sqlite`（CPA 的 `config.yaml` 本身也是明文存储），请控制好服务器与备份文件的访问权限。

## 注意事项

- 不要在 CPA 面板里手动删除门户创建的密钥：下一轮同步会把应当可用的密钥加回去。要停用请在门户里操作。
- 如果运营概况显示"用量同步失败"，这段时间的请求不会扣费，修复后会从中断处继续补扣（只要 CPAMP 的数据还在）。
- 首次启动时，门户从 CPAMP 当前最新的一条记录开始读取，不会对历史用量扣费。
