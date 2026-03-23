"""Generate offline legal evaluation dataset (Q-A-Context) in JSONL."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Any, List

from langchain_core.messages import HumanMessage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.llm_factory import LLMFactory
from app.core.logger import app_logger


DATASET_PROMPT = """
你是资深中国法律教育与评测专家。请生成 {count} 条用于 RAG/Agent 评估的测试样本。

每条样本必须是 JSON 对象，字段如下：
- id: 字符串，格式 eval_001
- question: 用户问题（真实、具体）
- reference_answer: 标准答案（简洁准确，包含法律逻辑）
- reference_context: 参考文档片段（法条摘要或案例摘要，可被 RAG 检索）
- category: 问题类别（如劳动争议/婚姻家事/合同纠纷/交通事故）
- difficulty: easy|medium|hard

强约束：
1) 只输出 JSON 数组，不要输出任何额外文字。
2) 题目应覆盖多个法律场景，至少 50% 为劳动法相关。
3) reference_answer 必须与 reference_context 一致，不要自相矛盾。
4) 每条 question 长度 20-80 字。
5) 输出必须可被 json.loads 解析。
""".strip()


def _extract_json_array(raw_text: str) -> list[dict[str, Any]]:
    text = raw_text.strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("模型输出中未找到 JSON 数组")
    payload = text[start : end + 1]
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("输出不是 JSON 数组")
    return data


def _fallback_dataset(count: int) -> list[dict[str, Any]]:
    templates = [
        {
            "question": "公司未提前通知就辞退我，工作 2 年 8 个月，月薪 12000，可能拿到多少补偿？",
            "reference_answer": "若构成违法解除，通常按经济补偿标准的二倍支付，即 2N。2 年 8 个月可按 3 个月计，2N 约为 72000 元。",
            "reference_context": "劳动合同法第47条：经济补偿按工作年限计算；第87条：违法解除需按经济补偿标准二倍支付赔偿金。",
            "category": "劳动争议",
            "difficulty": "easy",
        },
        {
            "question": "试用期公司不给我缴社保是否合法？",
            "reference_answer": "不合法。建立劳动关系后，用人单位应依法为劳动者参加社会保险，试用期也不例外。",
            "reference_context": "社会保险法规定，用人单位应自用工之日起 30 日内为职工申请办理社保登记。",
            "category": "劳动争议",
            "difficulty": "easy",
        },
        {
            "question": "房屋租赁合同里约定‘押金一律不退’是否有效？",
            "reference_answer": "该类一刀切条款可能被认定为无效或应调整，需结合违约情况与实际损失判断。",
            "reference_context": "民法典合同编强调公平原则，格式条款不得不合理免除提供方责任或加重对方责任。",
            "category": "合同纠纷",
            "difficulty": "medium",
        },
    ]

    items: list[dict[str, Any]] = []
    for i in range(count):
        t = random.choice(templates).copy()
        t["id"] = f"eval_{i + 1:03d}"
        items.append(t)
    return items


def generate_dataset(count: int, use_fallback: bool = False) -> list[dict[str, Any]]:
    if use_fallback:
        return _fallback_dataset(count)

    llm = LLMFactory.create_llm(temperature=0.3, max_tokens=4096)
    prompt = DATASET_PROMPT.format(count=count)
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content if hasattr(response, "content") else str(response)
    data = _extract_json_array(content)

    normalized = []
    for i, item in enumerate(data[:count], start=1):
        normalized.append(
            {
                "id": item.get("id") or f"eval_{i:03d}",
                "question": str(item.get("question", "")).strip(),
                "reference_answer": str(item.get("reference_answer", "")).strip(),
                "reference_context": str(item.get("reference_context", "")).strip(),
                "category": str(item.get("category", "其他")).strip(),
                "difficulty": str(item.get("difficulty", "medium")).strip(),
            }
        )
    if len(normalized) < count:
        normalized.extend(_fallback_dataset(count - len(normalized)))
    return normalized[:count]


def save_jsonl(items: List[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for row in items:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate legal eval dataset JSONL")
    parser.add_argument("--count", type=int, default=20, help="sample count")
    parser.add_argument(
        "--output",
        type=str,
        default=str(PROJECT_ROOT / "eval" / "eval_dataset.jsonl"),
        help="output jsonl path",
    )
    parser.add_argument("--fallback", action="store_true", help="use fallback synthetic data")
    args = parser.parse_args()

    try:
        data = generate_dataset(count=args.count, use_fallback=args.fallback)
        save_jsonl(data, Path(args.output))
        app_logger.info(f"✅ eval 数据集已生成: {args.output}, count={len(data)}")
        print(f"Generated {len(data)} samples -> {args.output}")
    except Exception as e:
        app_logger.error(f"❌ 生成评估数据失败: {str(e)}")
        raise


if __name__ == "__main__":
    main()
