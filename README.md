# House Agent

> 面向长租场景的智能找房与预约看房系统。项目使用 LangGraph 编排租房意图识别、MySQL 房源检索、预约工单和预约记录管理；`web/` 提供 Vue 3 租客工作台。

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3-42B883?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent%20workflow-1C3C3C)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Async%20Gateway-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## 目录

- [项目能力](#项目能力)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [使用流程](#使用流程)
- [LangGraph 图](#langgraph-图)
- [项目结构](#项目结构)
- [数据与权限边界](#数据与权限边界)
- [测试与质量检查](#测试与质量检查)
- [常见问题](#常见问题)
- [生产部署建议](#生产部署建议)

## 项目能力

### 租客侧找房

- **真实房源目录**：页面初次加载从 MySQL `house` 表读取房源卡片，不维护静态或模拟房源数据。
- **自然语言推荐**：支持城市、区域、预算、户型、朝向和补充需求等自然语言输入；智能体提取条件后生成并校验 SQL，再查询真实房源。
- **结果联动**：智能体推荐的房源会以结构化 `listings` 状态返回，前端立即将目录切换为推荐结果卡片。
- **多维排序**：支持智能匹配、最新发布、价格优先三种当前结果集排序方式。
- **对话式补问**：城市或预算等核心条件缺失时，后端通过 LangGraph `interrupt` 请求补充信息，前端可在同一会话中恢复执行。

### 预约看房

- **完整预约工单流程**：预约弹窗收集看房时间、手机号与证件号码，依次恢复原有 `reserve_agent` 的房源、电话、证件信息节点，生成工单。
- **预约状态突出显示**：工单生成成功后，对应房源卡片会置顶并标记为“预约已确认”。
- **我的预约**：按预约手机号读取已生成工单，展示房源、工单号、看房时间、联系电话与状态。
- **取消预约**：租客可以取消未取消的预约，预约记录保留并更新为已取消状态，便于追踪历史。
- **合同风险分析**：内置租赁条款知识库，检索押金、租金、违约、维修与居住权相关依据，输出结构化风险、原始条款与协商建议。

### 工作台体验

- Vue 3 + Element Plus 构建的响应式租客工作台。
- Three.js 房源雷达场景，桌面与小屏幕均可稳定渲染。
- 流式消费 LangGraph Server 的 SSE `values` / `updates` 事件。
- 助手返回的 Markdown 标题、加粗与表格会被格式化为适合聊天气泡阅读的文本。

## 系统架构

```mermaid
flowchart LR
    U["租客浏览器 / Vue 3"] -->|"SSE / threads/{id}/runs/stream"| LG["LangGraph Server"]
    U -->|"REST /api/*"| API["FastAPI 异步网关"]
    LG --> H["house_agent\n意图识别与主编排"]
    H --> R["recommend_agent\nSQL 推荐子图"]
    H --> V["reserve_agent\n预约子图"]
    LG --> B["browse_agent\n房源目录"]
    LG --> A["appointments_agent\n预约中心"]
    R --> DB[("MySQL\nhouse 表")]
    B --> DB
    V --> S[("LangGraph Store\n预约与偏好")]
    A --> S
    API --> P[("PostgreSQL / SQLite\n用户、会话、预约")]
```

### 房源推荐数据流

1. 前端首次调用 `browse_agent`，读取数据库最新房源并渲染卡片。
2. 用户提交自然语言需求，`house_agent` 判断为推荐、预约、偏好查询或其他问答。
3. 推荐子图提取条件，读取表结构，生成 SQL，检查 SQL，再通过 `SQLDatabaseToolkit` 执行查询。
4. 推荐节点保留 SQL 返回的房源 ID，并回查完整字段映射为统一的 `listings` 卡片数据。
5. 前端收到最终状态后用推荐 `listings` 替换首屏目录；智能体文本仍在聊天区域展示。

### 预约数据流

1. 用户从房源卡片打开预约弹窗。
2. 前端将房源标题、手机号、证件号码按顺序恢复 `reserve_agent` 的中断节点。
3. `generate_orders` 工具生成工单，并把预约记录写入 LangGraph Store。
4. 前端使用 `appointments_agent` 补充看房时间、刷新预约中心，并将房源卡片标记为已预约。
5. 用户可在“我的预约”中查询或取消自己的预约记录。

## 技术栈

| 层级 | 技术 | 用途 |
| --- | --- | --- |
| 前端框架 | Vue 3、Vite | 单页工作台与开发/构建工具链 |
| UI | Element Plus、`@element-plus/icons-vue` | 表单、对话框、空状态、标签与无障碍基础组件 |
| 3D | Three.js | 房源雷达场景 |
| Agent 编排 | LangGraph、LangChain | 状态图、子图、工具调用、中断恢复与持久化 Store |
| 业务网关 | FastAPI、AnyIO | 异步 REST API、会话记录、用户偏好与预约业务数据 |
| 模型接入 | `langchain-openai` | OpenAI 兼容接口；可配置 DeepSeek 或其他兼容服务 |
| 数据库 | MySQL、PostgreSQL、SQLite、SQLAlchemy | MySQL 房源读取；PostgreSQL 业务数据；SQLite 本地开发测试 |
| 工程质量 | Ruff、Pytest | 静态检查和测试 |

## 快速开始

### 前置条件

- Python `3.11+`
- Node.js `20+`
- 可访问的 MySQL 房源库，包含 `house` 表
- 可用的 OpenAI 兼容模型服务密钥

### 1. 克隆并配置后端

```powershell
git clone https://github.com/yanxiao07/house_agent.git
cd house_agent

# Windows PowerShell
Copy-Item .env.example .env
```

在 `.env` 中填写模型与 MySQL 连接信息，示例见 [配置说明](#配置说明)。不要提交 `.env`。

安装依赖并启动 LangGraph Server：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e . "langgraph-cli[inmem]"

langgraph dev --port 2024
```

服务启动后默认监听 `http://127.0.0.1:2024`。

可选启动 FastAPI 业务网关（用户会话、预约业务数据、合同分析 REST API）：

```powershell
uvicorn agent.api:app --reload --port 8000
```

网关文档地址为 `http://127.0.0.1:8000/docs`。

### 2. 配置并启动前端

新开一个终端：

```powershell
cd web
Copy-Item .env.example .env
npm install
npm run dev
```

在 `web/.env` 中设置后端地址：

```dotenv
VITE_LANGGRAPH_API_URL=http://127.0.0.1:2024
VITE_LANGGRAPH_ASSISTANT_ID=house_agent
VITE_RENTAL_API_URL=http://127.0.0.1:8000
```

访问 Vite 输出的地址，默认是 `http://127.0.0.1:5173`。

### 3. 生产构建

```powershell
cd web
npm run build
npm run preview
```

## 配置说明

根目录 `.env.example` 提供完整模板。

### 模型配置

通用 `LLM_*` 变量优先级高于 `DEEPSEEK_*` 变量：

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `LLM_API_KEY` | 是 | OpenAI 兼容模型 API Key |
| `LLM_BASE_URL` | 是 | OpenAI 兼容 API Base URL |
| `LLM_MODEL` | 是 | 模型名称 |
| `LLM_TEMPERATURE` | 否 | 温度，默认 `0` |
| `DEEPSEEK_API_KEY` | 可选 | 兼容旧部署的 DeepSeek 配置 |
| `DEEPSEEK_BASE_URL` | 可选 | DeepSeek / 兼容服务地址 |
| `DEEPSEEK_MODEL` | 可选 | DeepSeek / 兼容模型名 |

### MySQL 配置

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `DB_HOST` | 是 | MySQL 主机地址 |
| `DB_PORT` | 是 | MySQL 端口 |
| `DB_NAME` | 是 | 数据库名称 |
| `DB_USER` | 是 | 只读或最小权限数据库用户 |
| `DB_PASSWORD` | 是 | 数据库密码 |
| `PROPERTY_IMAGE_BASE_URL` | 否 | 数据库相对图片路径的 CDN / 对象存储域名 |

当前房源映射使用 `house` 表中的 `id`、`title`、`rent_type`、`rooms`、`position`、`area`、`price`、`city_name`、`region_name`、`community_name`、`detail_address`、`head_image`、`images` 等字段。

### 业务数据配置

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | 否 | 用户、会话、预约业务库 URL；生产推荐 `postgresql+psycopg://user:password@host:5432/house_agent` |

未设置时，项目使用 `.langgraph_api/rental.db` SQLite 文件，适合本地运行和测试；生产环境应配置 PostgreSQL。

### LangSmith（可选）

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT=house-agent
```

用于查看模型调用、状态图执行和工具调用轨迹。未配置时不影响核心功能。

## 使用流程

### 找房与推荐

1. 页面会先加载数据库房源目录。
2. 使用顶部筛选栏，或在右侧助手中输入自然语言需求，例如：`深圳租房，预算 1000 到 2000 元，一居室`。
3. 智能体返回推荐文本，同时房源区域切换为推荐结果。
4. 如信息不足，按聊天中的追问补充城市、预算等条件。

### 预约看房

1. 在任意房源卡片点击“预约看房”。
2. 填写看房时间、联系电话与证件号码。
3. 提交后等待工单生成成功提示。
4. 已预约房源将置顶并显示预约状态；“我的预约”自动更新。

### 我的预约

1. 点击顶部“我的预约”，或滚动到预约中心。
2. 输入预约时使用的手机号并查询。
3. 查看工单号、房源、看房时间和状态。
4. 对未取消的预约点击“取消预约”并确认。

## LangGraph 图

`langgraph.json` 注册以下图，均可通过 LangGraph Server 调用：

| 图 ID | 模块 | 职责 |
| --- | --- | --- |
| `house_agent` | `agent.graph:graph` | 主编排：读取偏好、识别意图、路由到推荐/预约/查询/普通问答 |
| `recommend_agent` | `agent.recommend:recommend_graph` | 提取租房需求、检查数据库结构、生成/校验/执行 SQL |
| `reserve_agent` | `agent.reserve:reserve_graph` | 通过中断收集预约信息并生成预约工单 |
| `appointments_agent` | `agent.appointments:appointments_graph` | 查询、补全、取消预约记录 |
| `contracts_agent` | `agent.contracts:contracts_graph` | 检索合同知识并输出结构化条款风险 |
| `browse_agent` | `agent.browse:browse_graph` | 读取首屏房源目录 |
| `extend_agent` | `agent.extend:extend_graph` | 处理非核心租房问答 |

### SSE 会话协议

前端通过以下接口执行图：

```text
POST /threads
POST /threads/{thread_id}/runs/stream
```

主要消费：

- `values`：图的完整最新状态，例如 `messages`、`listings`、`appointments`。
- `updates`：节点增量状态，包含预约或补充信息的中断事件。
- `__interrupt__`：需要用户输入时的暂停信息；前端用 `command.resume` 在同一线程恢复。

### FastAPI 业务接口

| 方法 | 路径 | 职责 |
| --- | --- | --- |
| `GET` | `/api/health` | 网关健康检查 |
| `GET` | `/api/listings` | 异步读取只读房源卡片 |
| `GET/PUT` | `/api/users/{user_id}/preferences` | 读取或写入租客偏好 |
| `POST` | `/api/conversations` | 写入一条会话消息 |
| `GET` | `/api/users/{user_id}/conversations/{session_id}` | 恢复会话历史 |
| `GET` | `/api/users/{user_id}/bookings` | 查询业务预约记录 |
| `PUT` | `/api/bookings/{order_id}` | 幂等写入预约业务记录 |
| `POST` | `/api/users/{user_id}/bookings/{order_id}/cancel` | 取消预约 |
| `POST` | `/api/contracts/analyze` | 合同知识检索与风险分析 |

## 项目结构

```text
house-agent/
├── src/agent/
│   ├── graph.py                 # 主状态图与路由
│   ├── recommend.py             # 房源推荐子图
│   ├── reserve.py               # 预约子图
│   ├── appointments.py          # 我的预约查询/取消图
│   ├── contracts.py             # 合同 RAG 检索、风险分析与合同图
│   ├── api.py                   # FastAPI 异步业务网关
│   ├── persistence.py            # PostgreSQL/SQLite 用户、会话、预约仓储
│   ├── browse.py                # 首屏房源目录图
│   ├── catalog.py               # MySQL 房源到前端卡片的只读映射
│   ├── common/
│   │   ├── llm.py               # OpenAI 兼容模型初始化
│   │   ├── store.py             # 偏好与预约数据模型
│   │   └── context.py           # LangGraph 运行时上下文
│   ├── node/                    # 主图、推荐、预约节点
│   └── state/                   # 状态类型定义
├── web/
│   ├── src/App.vue              # 租客工作台与预约中心
│   ├── src/services/agent.js    # LangGraph SSE 客户端
│   ├── src/components/HouseScene.vue # Three.js 场景
│   └── src/styles.css            # 响应式样式
├── tests/
├── langgraph.json
├── .env.example
└── pyproject.toml
```

## 数据与权限边界

### 房源

- 房源来自 MySQL，租客前端只具备浏览、筛选、智能查询与预约能力。
- 项目不提供租客侧新增、编辑或删除房源的接口或 UI。
- 推荐结果按 SQL 返回的房源 ID 回查完整记录，避免前端维护重复数据源。

### 预约

- 预约记录使用 LangGraph Store 保存，按预约手机号查询。
- 前端会在本地浏览器保存最近一次预约手机号，以便自动刷新“我的预约”；不会把手机号提交到代码仓库。
- 当前示例未接入登录/短信验证码。生产环境必须以已认证的用户 ID 替代手机号直接查询，并在服务端验证预约归属。

### 合同审查

- 合同文本仅用于本地检索和规则分析；当前实现不依赖 LLM 才能给出初步风险提示。
- 返回值包含命中条款、风险级别、协商建议和知识依据，便于前端稳定展示与后续接入向量数据库/LLM 总结。
- 本功能不构成法律意见，重要签约请咨询专业人士。

### 数据库与模型调用

- 数据库、模型密钥和 LangSmith 密钥只从环境变量读取。
- `.env`、前端依赖和构建产物已被 `.gitignore` 忽略。
- 推荐提示词限制为查询场景，但生产环境仍应使用最小权限 MySQL 账号、数据库网络隔离和 SQL 审计，不能把提示词当作安全边界。

## 测试与质量检查

### 后端

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m pytest tests/unit_tests -q
```

### 前端

```powershell
cd web
npm run build
```

### 浏览器端到端检查

在 LangGraph Server（默认 `2024`）和前端开发服务（默认 `5173`）均启动后，执行：

```powershell
cd web
npm run test:e2e
```

该检查通过 Edge 驱动真实浏览器，不使用 mock 数据，验证以下流程：

- 首屏从 `browse_agent` 读取 MySQL 房源目录，卡片图片实际完成加载；
- “找房工作台 / 我的预约 / 合同审查”是相互独立的页面视图，而不是向下堆叠的长页面；
- 合同审查会展示结构化风险与 3 条 RAG 检索依据；
- 390px 移动端下的主导航和首张房源卡片可见。

推荐、预约和预约中心的端到端验证需要有效的模型凭据、可访问的 MySQL 与运行中的 LangGraph Server。

FastAPI 接口测试使用临时 SQLite 数据库，不依赖 MySQL、PostgreSQL 或模型 Key。

## 常见问题

### 页面没有房源卡片

1. 确认后端 `http://127.0.0.1:2024` 已启动。
2. 确认 `web/.env` 的 `VITE_LANGGRAPH_API_URL` 指向该地址。
3. 检查 MySQL 连接变量与 `house` 表是否可访问。
4. 查看 LangGraph Server 日志，确认 `browse_agent` 已注册。

### 房源图片无法显示

数据库当前存储的是类似 `bitehouse/<file>.jpg` 的对象键，而不是可由浏览器直接访问的 URL。生产环境需要在后端 `.env` 中配置实际对象存储或 CDN 域名：

```dotenv
PROPERTY_IMAGE_BASE_URL=https://your-cdn.example.com
```

未配置时，服务端会明确返回 `preview_image: true` 并使用预览图，保证卡片不会出现空白区域；预览图不是原房源实拍图。配置后无需改动前端，接口会自动返回真实图片地址。

### 助手返回内容但没有推荐卡片

确认请求被识别为找房/推荐意图，并检查模型生成的 SQL 是否返回 `id`。推荐节点会基于这些 ID 回查并输出 `listings`。

### 模型调用报错或余额不足

检查 `.env` 中的模型 Key、Base URL、模型名称和账户状态。修改环境变量后重启 LangGraph Server，使运行进程重新加载配置。

### 我的预约为空

使用生成预约工单时填写的同一手机号查询。当前没有登录态绑定，手机号是预约记录的查询键。

## 生产部署建议

- 使用 HTTPS 反向代理，并限制 CORS 来源。
- 为 LangGraph API 接入认证、会话隔离、限流和审计日志。
- MySQL 使用只读最小权限账号处理房源查询；预约状态应使用单独的业务数据库表或具备备份策略的持久化 Store。
- 以登录用户 ID、短信验证码或 OAuth 身份替代手机号作为预约记录访问凭证。
- 将模型 Key、数据库密码放入密钥管理服务，不写入镜像、构建日志或仓库。
- 在 CI 中执行 Ruff、Pytest 和 `npm run build`。

## 许可证

本项目采用 [MIT License](LICENSE)。
