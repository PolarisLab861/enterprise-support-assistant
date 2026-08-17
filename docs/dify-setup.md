# 真实 Dify Workflow 配置指南

## 1. 创建知识库

1. 在 Dify 创建一个 Knowledge，命名为 `AcmeFlow Support Knowledge`。
2. 上传 `knowledge_base/` 下的 6 个 Markdown 文件。
3. 文本分段建议使用标题作为分段边界，chunk size 约 500～800 tokens，保留标题作为 metadata。
4. 开启引用来源返回，方便后端展示 `title`、`section`、`page` 或 chunk 标识。

## 2. 创建 Workflow

按以下顺序创建节点：

```text
Start
  → LLM: 意图和风险识别
  → Knowledge Retrieval
  → LLM: 依据检索结果生成答案
  → Condition: confidence / need_human
  → End 或人工转接分支
```

## 3. Start 输入变量

```text
message: string, required
user_id: string, required
conversation_id: string, optional
```

## 4. 意图识别提示词

```text
你是 AcmeFlow 客服分流器。只能从以下意图中选择一个：
account_problem, permission_problem, product_usage, api_problem,
billing_problem, technical_problem, feedback, other。

同时判断 priority：low、medium、high、critical。
如果问题涉及退款、删除数据、修改管理员权限、导出客户隐私数据、
修改收款账户或关闭安全验证，need_human 必须为 true。

输出 JSON：
{"intent":"...","priority":"...","need_human":true|false}
```

## 5. 答案生成提示词

```text
你是 AcmeFlow 客服助手。只能依据检索到的知识库内容回答。
如果检索内容不足，必须说明“知识库中没有足够依据”，不要使用常识补全。
回答需要给出可执行步骤，并返回引用来源。
涉及退款、删除、权限提升、数据导出和安全设置时，不得直接执行，必须转人工。

输出 JSON：
{
  "answer":"...",
  "confidence":0.0,
  "sources":[{"title":"...","section":"...","page":1,"score":0.0}],
  "reason":"..."
}
```

## 6. 后端连接配置

将 Dify 中发布后的 Workflow ID 和 API Key 写入 `.env`：

```env
MOCK_AI=false
DIFY_BASE_URL=https://api.dify.ai/v1
DIFY_API_KEY=your-dify-app-api-key
DIFY_WORKFLOW_ID=your-workflow-id
```

重启后端并调用：

```bash
curl -X POST http://localhost:8000/api/v1/questions \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"demo_user","message":"API 返回 401 怎么办？"}'
```

## 7. 验收检查

- “忘记密码”能返回账号文档引用。
- “直接给我退款”必须创建高优先级工单。
- “帮我订机票”不得编造答案，并创建人工工单。
- Dify 输出字段与 `app/dify.py` 的解析逻辑一致。
- Dify 不可用时 API 返回 502，且不会泄露 API Key。
