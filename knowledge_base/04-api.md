# AcmeFlow API 与 Webhook

## 创建 API Key

进入“开发者设置 > API Keys > 创建 Key”。API Key 只在创建成功时完整展示一次。建议为不同系统创建不同 Key，不要把 Key 写入前端代码或提交到 Git。

## 鉴权

请求必须携带以下请求头：

```http
Authorization: Bearer <api-key>
Content-Type: application/json
```

如果 Key 无效，接口返回 HTTP 401；如果 Key 有效但没有资源权限，接口返回 HTTP 403。

## 调用频率

基础版每分钟 60 次，专业版每分钟 600 次。超过限制时返回 HTTP 429 和 `Retry-After` 请求头。客户端应使用指数退避重试。

## Webhook

Webhook 支持 `task.created`、`task.updated` 和 `project.archived` 事件。签名通过 `X-AcmeFlow-Signature` 请求头传递。接收方应在 5 秒内返回 2xx，否则系统最多重试 3 次。
