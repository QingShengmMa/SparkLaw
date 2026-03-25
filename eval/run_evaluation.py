"""Run offline evaluation with LLM-as-a-Judge and produce detailed reports."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests
from langchain_core.messages import HumanMessage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.llm_factory import LLMFactory
from app.core.logger import app_logger


JUDGE_PROMPT_TEMPLATE = """
你是严谨的法律问答评审官（LLM-as-a-Judge）。
请根据给定问题、参考答案、上下文、系统答案进行打分。

【评分维度】每项 1-5 分：
1) faithfulness: 回答是否基于上下文，是否有幻觉。
2) answer_relevance: 回答是否直接解决用户诉求。
3) legal_accuracy: 法律条文引用与法律逻辑是否准确。
4) completeness: 是否覆盖关键结论、依据、建议。
5) format_adherence: 是否保持律师专业语气、结构清晰。

【输入】
Question:
{question}

Reference Answer:
{reference_answer}

Context (reference + retrieved):
{context}

System Answer:
{system_answer}

请严格输出 JSON：
{{
  "faithfulness": {{"score": 1-5, "reason": "..."}},
  "answer_relevance": {{"score": 1-5, "reason": "..."}},
  "legal_accuracy": {{"score": 1-5, "reason": "..."}},
  "completeness": {{"score": 1-5, "reason": "..."}},
  "format_adherence": {{"score": 1-5, "reason": "..."}},
  "overall": {{"score": 1-5, "reason": "..."}}
}}
""".strip()

SCORE_KEYS = [
    "faithfulness",
    "answer_relevance",
    "legal_accuracy",
    "completeness",
    "format_adherence",
    "overall",
]


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def call_legal_chat(api_base: str, question: str, session_id: str = "eval_session") -> str:
    url = f"{api_base.rstrip('/')}/api/legal/chat"
    payload = {"question": question, "session_id": session_id, "personality": "machine"}
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return str(resp.json().get("answer", "")).strip()


def call_retrieve_context(api_base: str, question: str, top_k: int = 3) -> str:
    url = f"{api_base.rstrip('/')}/api/document/retrieve"
    payload = {"query": question, "top_k": top_k}
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        lines = []
        for idx, item in enumerate(results, 1):
            text = str(item.get("text", "")).strip()
            if text:
                lines.append(f"[{idx}] {text[:300]}")
        return "\n".join(lines)
    except Exception:
        return ""


def parse_judge_json(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("judge 输出不是 JSON")
    return json.loads(text[start : end + 1])


def judge_answer(judge_llm, question: str, reference_answer: str, context: str, system_answer: str) -> Dict[str, Any]:
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        reference_answer=reference_answer,
        context=context,
        system_answer=system_answer,
    )
    response = judge_llm.invoke([HumanMessage(content=prompt)])
    content = response.content if hasattr(response, "content") else str(response)
    return parse_judge_json(content)


def to_score(judge_item: Dict[str, Any], key: str) -> float:
    try:
        return max(0.0, min(5.0, float(judge_item.get(key, {}).get("score", 0))))
    except Exception:
        return 0.0


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {"sample_size": 0, "avg": {k: 0 for k in SCORE_KEYS}, "by_category": {}, "by_difficulty": {}}

    avg = {k: statistics.mean(r["scores"][k] for r in rows) for k in SCORE_KEYS}

    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_difficulty: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_category[r["category"]].append(r)
        by_difficulty[r["difficulty"]].append(r)

    return {
        "sample_size": len(rows),
        "avg": avg,
        "pass_rate_overall_ge4": sum(1 for r in rows if r["scores"]["overall"] >= 4.0) / len(rows),
        "pass_rate_faithfulness_ge4": sum(1 for r in rows if r["scores"]["faithfulness"] >= 4.0) / len(rows),
        "by_category": {
            c: {
                "count": len(v),
                "overall": statistics.mean(x["scores"]["overall"] for x in v),
                "faithfulness": statistics.mean(x["scores"]["faithfulness"] for x in v),
                "legal_accuracy": statistics.mean(x["scores"]["legal_accuracy"] for x in v),
            }
            for c, v in sorted(by_category.items(), key=lambda x: x[0])
        },
        "by_difficulty": {
            d: {
                "count": len(v),
                "overall": statistics.mean(x["scores"]["overall"] for x in v),
                "faithfulness": statistics.mean(x["scores"]["faithfulness"] for x in v),
                "completeness": statistics.mean(x["scores"]["completeness"] for x in v),
            }
            for d, v in sorted(by_difficulty.items(), key=lambda x: x[0])
        },
    }


def render_markdown(rows: List[Dict[str, Any]], summary: Dict[str, Any], output: Path) -> None:
    lines = [
        "# SparkLaw Offline Evaluation Report",
        "",
        f"- Generated at: {datetime.now().isoformat()}",
        f"- Sample size: {summary['sample_size']}",
        "",
        "## Overall Metrics (1-5)",
        "",
    ]
    for k in SCORE_KEYS:
        lines.append(f"- {k}: **{summary['avg'][k]:.2f}**")

    lines.extend([
        "",
        f"- Pass@Overall>=4: **{summary['pass_rate_overall_ge4'] * 100:.1f}%**",
        f"- Pass@Faithfulness>=4: **{summary['pass_rate_faithfulness_ge4'] * 100:.1f}%**",
        "",
        "## Category Breakdown",
        "",
        "| Category | Count | Overall | Faithfulness | Legal Accuracy |",
        "|---|---:|---:|---:|---:|",
    ])
    for cat, v in summary["by_category"].items():
        lines.append(f"| {cat} | {v['count']} | {v['overall']:.2f} | {v['faithfulness']:.2f} | {v['legal_accuracy']:.2f} |")

    lines.extend([
        "",
        "## Difficulty Breakdown",
        "",
        "| Difficulty | Count | Overall | Faithfulness | Completeness |",
        "|---|---:|---:|---:|---:|",
    ])
    for diff, v in summary["by_difficulty"].items():
        lines.append(f"| {diff} | {v['count']} | {v['overall']:.2f} | {v['faithfulness']:.2f} | {v['completeness']:.2f} |")

    bad = [r for r in rows if r["scores"]["overall"] <= 2.5 or r["scores"]["faithfulness"] <= 2.5 or r["scores"]["legal_accuracy"] <= 2.5]
    lines.extend(["", "## Bad Cases", ""])
    if not bad:
        lines.append("无明显低分案例。")
    else:
        for item in bad:
            lines.extend([
                f"### {item['id']} ({item['category']} / {item['difficulty']})",
                f"- Question: {item['question']}",
                f"- Scores: {item['scores']}",
                f"- Judge Overall Reason: {item['judge_raw'].get('overall', {}).get('reason', '')}",
                "",
            ])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SparkLaw offline evaluation")
    parser.add_argument("--dataset", type=str, default=str(PROJECT_ROOT / "eval" / "eval_dataset.jsonl"))
    parser.add_argument("--api-base", type=str, default="http://127.0.0.1:8000")
    parser.add_argument("--judge-model", type=str, default="gpt-4o")
    parser.add_argument("--output", type=str, default=str(PROJECT_ROOT / "eval" / "reports" / "evaluation_report.md"))
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    dataset = load_jsonl(Path(args.dataset))
    judge_llm = LLMFactory.create_llm(model=args.judge_model, temperature=0.0, max_tokens=1500)

    rows: List[Dict[str, Any]] = []
    for i, item in enumerate(dataset, 1):
        sample_id = str(item.get("id", f"eval_{i:03d}"))
        question = str(item.get("question", "")).strip()
        reference_answer = str(item.get("reference_answer", "")).strip()
        reference_context = str(item.get("reference_context", "")).strip()
        category = str(item.get("category", "其他")).strip()
        difficulty = str(item.get("difficulty", "medium")).strip()

        app_logger.info(f"[{i}/{len(dataset)}] evaluating: {sample_id}")
        try:
            system_answer = call_legal_chat(args.api_base, question, session_id="eval_session")
            retrieved_context = call_retrieve_context(args.api_base, question, top_k=args.top_k)
            full_context = (reference_context + "\n" + retrieved_context).strip()
            judge_raw = judge_answer(judge_llm, question, reference_answer, full_context, system_answer)
            scores = {k: to_score(judge_raw, k) for k in SCORE_KEYS}
        except Exception as e:
            app_logger.error(f"样本评估失败 id={sample_id}: {e}")
            system_answer = ""
            retrieved_context = ""
            judge_raw = {"overall": {"score": 0, "reason": str(e)}}
            scores = {k: 0.0 for k in SCORE_KEYS}

        rows.append({
            "id": sample_id,
            "category": category,
            "difficulty": difficulty,
            "question": question,
            "reference_answer": reference_answer,
            "reference_context": reference_context,
            "retrieved_context": retrieved_context,
            "system_answer": system_answer,
            "scores": scores,
            "judge_raw": judge_raw,
        })

    summary = summarize(rows)
    report_path = Path(args.output)
    render_markdown(rows, summary, report_path)

    report_path.with_suffix(".summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.with_suffix(".details.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "Evaluation completed.\n"
        f"Report: {report_path}\n"
        f"Summary: {report_path.with_suffix('.summary.json')}\n"
        f"Details: {report_path.with_suffix('.details.json')}"
    )


if __name__ == "__main__":
    main()
