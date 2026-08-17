from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import httpx

from .config import Settings


@dataclass
class WorkflowResult:
    answer: str
    intent: str
    priority: str
    confidence: float
    sources: list[dict]
    need_human: bool
    reason: Optional[str] = None
    total_tokens: int = 0


class DifyWorkflowClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def run(self, message: str, user_id: str, conversation_id: Optional[str] = None) -> WorkflowResult:
        if self.settings.mock_ai or not self.settings.dify_api_key or not self.settings.dify_workflow_id:
            return self._mock(message)

        payload = {
            "inputs": {"message": message, "user_id": user_id},
            "response_mode": "blocking",
            "user": user_id,
        }
        if conversation_id:
            payload["inputs"]["conversation_id"] = conversation_id
        url = f"{self.settings.dify_base_url.rstrip('/')}/workflows/{self.settings.dify_workflow_id}/run"
        with httpx.Client(timeout=self.settings.dify_timeout_seconds) as client:
            response = client.post(url, headers={"Authorization": f"Bearer {self.settings.dify_api_key}"}, json=payload)
            response.raise_for_status()
        data = response.json()
        outputs = data.get("data", {}).get("outputs", data.get("outputs", {}))
        return WorkflowResult(
            answer=str(outputs.get("answer", outputs.get("text", "暂时无法生成回复。"))),
            intent=str(outputs.get("intent", "other")),
            priority=str(outputs.get("priority", "medium")),
            confidence=float(outputs.get("confidence", 0.5)),
            sources=list(outputs.get("sources", [])),
            need_human=bool(outputs.get("need_human", False)),
            reason=outputs.get("reason"),
            total_tokens=int(data.get("data", {}).get("total_tokens", 0)),
        )

    def _mock(self, message: str) -> WorkflowResult:
        text = message.lower()
        high_risk = any(word in message for word in ("退款", "删除", "管理员权限", "收款账户", "导出所有客户"))
        if any(word in text for word in ("登录", "密码", "验证码", "账号")):
            intent, answer, title = "account_problem", "请确认登录邮箱和验证码是否正确；如果仍然无法登录，请使用“忘记密码”功能重置密码。", "账号登录说明"
        elif any(word in text for word in ("api", "接口", "webhook")):
            intent, answer, title = "api_problem", "请检查 API Key、请求地址和调用频率限制；如果返回 401，请重新生成并配置 API Key。", "API 接入说明"
        elif any(word in text for word in ("价格", "套餐", "发票", "退款")):
            intent, answer, title = "billing_problem", "价格、套餐和退款政策需要以企业后台配置为准；我可以先为你创建工单，由客服确认具体方案。", "套餐与售后政策"
        elif any(word in text for word in ("创建", "导入", "导出", "项目", "功能")):
            intent, answer, title = "product_usage", "请参考产品使用手册中的项目管理和数据导入章节；如果你提供具体报错，我可以进一步定位。", "产品使用手册"
        else:
            intent, answer, title = "other", "我暂时没有在知识库中找到足够依据。请补充产品名称、操作步骤和报错信息，我会为你转人工处理。", "客服处理规范"
        need_human = high_risk or intent == "other" or "人工" in message
        confidence = 0.96 if not need_human else 0.38
        return WorkflowResult(
            answer=answer,
            intent=intent,
            priority="high" if high_risk else "medium",
            confidence=confidence,
            sources=[{"title": title, "section": "常见问题", "page": 1, "score": confidence}],
            need_human=need_human,
            reason="涉及高风险操作或知识库依据不足" if need_human else None,
            total_tokens=0,
        )
