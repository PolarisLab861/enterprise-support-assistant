"""Run the markdown evaluation set against Mock AI or a configured Dify Workflow."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.dify import DifyWorkflowClient  # noqa: E402


ROW = re.compile(r"^\| (Q\d{3}) \| (.*?) \| (.*?) \| (.*?) \|$")


def load_cases() -> list[tuple[str, str, str, str]]:
    cases = []
    for line in (ROOT / "docs/evaluation.md").read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match:
            cases.append(match.groups())
    return cases


def main() -> None:
    client = DifyWorkflowClient(get_settings())
    cases = load_cases()
    expected_human = {"追问或转人工", "转人工", "查询工单或转人工", "必须人工确认"}
    human_correct = 0
    total_human = 0
    total_correct = 0
    for case_id, question, _, expected_action in cases:
        result = client.run(question, "evaluation_user")
        should_handoff = expected_action in expected_human
        if should_handoff:
            total_human += 1
        if result.need_human == should_handoff:
            total_correct += 1
            if should_handoff:
                human_correct += 1
    accuracy = total_correct / len(cases) if cases else 0
    handoff_recall = human_correct / total_human if total_human else 0
    print(f"cases={len(cases)}")
    print(f"human_decision_accuracy={accuracy:.3f}")
    print(f"human_handoff_recall={handoff_recall:.3f}")
    print(f"mode={'mock' if get_settings().mock_ai else 'dify'}")


if __name__ == "__main__":
    main()
