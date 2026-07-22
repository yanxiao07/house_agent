# House Agent

面向长租场景的智能找房与预约看房系统。项目以 LangGraph 编排租房意图识别、房源推荐、预约工单和用户偏好查询；`web/` 提供独立的 Vue 3 租赁工作台。

## 功能

- 根据城市、区域、预算、户型和附加偏好推荐房源
- 保存用户预算偏好并支持查询历史预约
- 引导式收集预约信息，生成预约工单
- Vue 3 + Element Plus 商业化工作台：筛选、房源卡片、预约弹窗和对话助手
- Three.js 房源概览场景，桌面端自适应渲染，小屏平稳降级

## 项目结构

```text
src/agent/          LangGraph 工作流、节点和状态定义
tests/              单元与集成测试
web/                Vue 3 + Vite + Element Plus + Three.js 前端
langgraph.json      LangGraph Server 图配置
```

## 后端启动

前提：Python 3.11+、可访问的 OpenAI 兼容模型服务，以及 MySQL 房源库。

```powershell
Copy-Item .env.example .env
# 在 .env 中填写 LLM_API_KEY、数据库连接等配置
pip install -e . "langgraph-cli[inmem]"
langgraph dev
```

服务默认由 LangGraph CLI 提供。`house_agent` 是前端调用的主图 ID。

## 前端启动

前提：Node.js 20+。

```powershell
cd web
Copy-Item .env.example .env
npm install
npm run dev
```

访问 Vite 输出的地址，默认是 `http://localhost:5173`。前端需要配置 LangGraph Server 地址；未配置时会明确提示服务未连接，不会显示模拟的助手回复。

```dotenv
VITE_LANGGRAPH_API_URL=http://127.0.0.1:2024
VITE_LANGGRAPH_ASSISTANT_ID=house_agent
```

前端通过 LangGraph 的流式 `values` 事件消费主图状态：

- `messages`：助手对话内容
- `matches`：后端目录筛选后的房源卡片
- `booking`：预约工单状态与编号

因此筛选、对话和预约都由同一条后端会话驱动，前端不维护独立的模拟结果。

## 配置说明

不要将真实密钥、数据库密码或 `.env` 提交到仓库。后端优先使用通用配置：

| 变量 | 用途 |
| --- | --- |
| `LLM_API_KEY` | OpenAI 兼容模型的 API 密钥 |
| `LLM_BASE_URL` | 模型服务地址 |
| `LLM_MODEL` | 模型名称 |
| `DB_USER` / `DB_PASSWORD` | MySQL 凭据 |
| `DB_HOST` / `DB_PORT` / `DB_NAME` | MySQL 连接信息 |

为兼容已有部署，也支持 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`。

## 校验

```powershell
cd web
npm run build

cd ..
python -m compileall -q src
pytest tests/unit_tests
```

Python 测试和实际推荐流程需要可用的模型与 MySQL 配置。前端构建不依赖任何密钥。

## 安全

- 密钥仅从环境变量读取，代码库不保存服务端凭据。
- `.env`、`web/node_modules` 和前端构建产物已加入忽略规则。
- 面向生产时，请在网关层为 LangGraph API 加上认证、限流与 CORS 白名单。
