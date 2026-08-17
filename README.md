# 企业智能工单与知识库助手

> 面向企业 SaaS 客服场景的 AI 工单分流与知识库问答项目。

## 项目简介

客服人员经常需要重复回答产品使用、账号权限、退款政策和技术故障等问题。这个项目将企业文档接入知识库，由 Dify 编排问答与工单流程，由 FastAPI 提供业务 API，并使用 PostgreSQL 保存工单、反馈和运行记录。

系统的核心目标不是“让模型自由聊天”，而是让每一次回答都尽量有依据；当知识库没有足够信息、问题涉及高风险操作或用户要求人工服务时，系统会创建工单并转人工处理。

## 核心流程

```mermaid
flowchart LR
    A[用户提交问题] --> B[FastAPI 接收请求]
    B --> C[Dify 意图分类]
    C --> D[知识库检索与重排序]
    D --> E{是否有可靠依据}
    E -->|是| F[生成带引用的回复]
    E -->|否| G[创建工单并转人工]
    F --> H[保存问答记录]
    G --> I[通知负责人]
    I --> J[PostgreSQL 保存工单]
```

## 功能清单

- 知识库问答：支持产品手册、FAQ、售后政策和故障排查文档。
- 意图识别：账号问题、产品使用、技术故障、退款问题、功能建议和其他问题。
- 引用来源：回复展示命中的文档标题、章节或页码。
- 拒答与转人工：知识库没有依据、置信度过低或涉及高风险操作时，不编造答案。
- 工单管理：创建工单、设置优先级、分配负责人、更新状态和保存处理记录。
- 反馈闭环：用户可以评价回复，低评分问题进入知识库优化列表。
- 运行统计：记录响应时间、Token 消耗、失败原因、人工转接率和满意度。

## 技术栈

| 模块 | 技术 | 责任 |
|---|---|---|
| AI 工作流 | Dify | 意图分类、RAG 检索、答案生成、人工审核节点 |
| 业务后端 | FastAPI | 鉴权、参数校验、工单 API、Dify 适配 |
| 数据库 | PostgreSQL | 工单、反馈、运行记录和用户数据 |
| 前端 | React/Vue | 用户问答页、工单管理页、统计页 |
| 部署 | Docker Compose | 本地和测试环境一键启动 |
| 评测 | Python | 测试集、指标统计、回归测试 |

演示知识库位于 [`knowledge_base/`](knowledge_base/)，真实 Dify 配置步骤见 [`docs/dify-setup.md`](docs/dify-setup.md)。

## 一次完整请求

### 请求

```http
POST /api/v1/questions
Content-Type: application/json
Authorization: Bearer <access-token>
```

```json
{
  "user_id": "user_001",
  "message": "为什么我的账号无法登录？",
  "conversation_id": "conversation_001"
}
```

### 返回

```json
{
  "request_id": "req_20260817_0001",
  "answer": "请先确认登录邮箱是否正确；如果仍无法登录，可以使用‘忘记密码’功能重置密码。",
  "intent": "account_problem",
  "confidence": 0.91,
  "sources": [
    {
      "title": "账号登录说明",
      "section": "密码重置",
      "page": 3
    }
  ],
  "need_human": false,
  "ticket_id": null
}
```

## 本地运行

项目当前已包含 FastAPI 后端、Mock AI、工单管理页面、PostgreSQL Compose 配置和自动化测试。没有 Dify Key 时默认使用 Mock AI，可以直接演示完整流程。

```bash
git clone <your-repository-url>
cd enterprise-support-assistant
cp .env.example .env
docker compose up -d
```

启动后访问：

```text
前端：http://localhost:8000
后端：http://localhost:8000
Swagger：http://localhost:8000/docs
```

至少需要配置：

```env
DIFY_BASE_URL=http://localhost/v1
DIFY_API_KEY=replace-with-dify-api-key
DATABASE_URL=postgresql+psycopg://app:app@postgres:5432/support_assistant
MOCK_AI=true
```

切换到真实 Dify Workflow 时，将 `MOCK_AI` 改为 `false`，并填写 `DIFY_API_KEY` 和 `DIFY_WORKFLOW_ID`。Dify Workflow 需要输出 `docs/architecture.md` 中约定的 JSON 字段。

不使用 Docker 时，也可以使用 SQLite 快速启动：

```bash
python -m venv .venv
source .venv/bin/activate
pip install '.[dev]'
uvicorn app.main:app --reload
```

运行测试：

```bash
pytest
```

运行评测脚本：

```bash
PYTHONPATH=. python scripts/evaluate.py
```

脚本会读取 60 条评测问题，并根据当前 `MOCK_AI` 配置运行 Mock AI 或真实 Dify Workflow。

## 数据模型

### tickets

| 字段 | 说明 |
|---|---|
| id | 工单编号 |
| user_message | 用户原始问题 |
| intent | 问题类型 |
| priority | low/medium/high/critical |
| status | open/in_progress/resolved/closed |
| ai_reply | AI 初步回复 |
| sources | 引用来源 JSON |
| assigned_to | 负责人 |
| created_at | 创建时间 |

### feedbacks

| 字段 | 说明 |
|---|---|
| id | 反馈编号 |
| ticket_id | 关联工单 |
| score | 1～5 分 |
| comment | 用户评价 |
| created_at | 评价时间 |

## 评测方案

使用 `docs/evaluation.md` 中的 60 条测试问题，覆盖知识库内、模糊、知识库外和高风险问题。

重点指标：

- 意图分类准确率
- 检索命中率
- 答案准确率
- 引用正确率
- 拒答准确率
- 转人工准确率
- 平均响应时间
- 单次 Token 消耗

评测时比较三个版本：

1. V1：直接向量检索后生成答案。
2. V2：意图分类后再检索。
3. V3：问题改写、混合检索、重排序和置信度判断。

实际测试结果应填写到 `docs/evaluation.md`，不要用预估数据冒充实测结果。

## 项目亮点

- 不是单纯聊天机器人，而是完整的“问答—判断—工单—人工处理”闭环。
- 通过引用来源和拒答策略降低幻觉风险。
- 使用 Dify 编排 AI 流程，使用 FastAPI 和 PostgreSQL 完成工程化封装。
- 有明确的测试集、评测指标和优化前后对比。
- 支持后续接入飞书、钉钉、Zendesk 或企业自有客服系统。

## 项目截图与演示

后续补充真实部署截图和演示视频：

- 用户问答页面截图
- Dify Workflow 截图
- 工单管理页面截图
- 评测结果截图
- 3 分钟演示视频链接

## 文档导航

- [项目开发计划](PROJECT_PLAN.md)
- [系统架构](docs/architecture.md)
- [真实 Dify 配置指南](docs/dify-setup.md)
- [演示知识库](knowledge_base/README.md)
- [评测方案与测试问题](docs/evaluation.md)

## 当前进度

- [x] 完成 FastAPI 问答和工单 API
- [x] 支持 Mock AI 演示模式
- [x] 接入 PostgreSQL 配置
- [x] 开发基础工单管理页面
- [x] 补充 60 条测试问题和评测方案
- [x] 提供 Docker Compose 部署配置
- [ ] 配置真实 Dify Workflow
- [ ] 补充真实评测结果
- [ ] 接入飞书或钉钉通知

## 作者

个人学习与求职作品集项目。
